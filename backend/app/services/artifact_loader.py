"""
app/services/artifact_loader.py — Artifact discovery, parsing, caching, and
cluster_id-keyed merging.

Design rules (per spec section 2 and 5):
  * Search the configured output directory; if it contains run subdirectories
    (ISO-ish timestamped folders), use the newest one unless PARKSIGHT_RUN_ID
    is set.
  * Recognize a few common filename variants per artifact.
  * Required artifacts missing → raise ArtifactError; optional ones missing →
    treated as unavailable, never fabricated.
  * Parsed artifacts are cached in memory and only re-parsed when the
    underlying file's mtime changes.
  * cluster_id is normalized to int before any merge. Duplicate cluster_ids
    and unmatched keys are logged and exposed via diagnostics.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import yaml

from ..config import AppConfig, app_config

log = logging.getLogger("parksight.artifact_loader")

# Canonical artifact name -> accepted filename patterns (case-insensitive,
# versioned suffixes like "_v2" or "_2026-06-20" are tolerated).
ARTIFACT_PATTERNS: Dict[str, List[str]] = {
    "temporal_audit": [r"temporal_audit.*\.json"],
    "bias_audit": [r"bias_audit.*\.json"],
    "hotspot_clusters": [r"hotspot_clusters.*\.csv"],
    "nonjunction_hotspots": [r"nonjunction_hotspots.*\.csv", r"non_junction_hotspots.*\.csv"],
    "risk_scores": [r"risk_scores.*\.csv"],
    "spatial_stability": [r"spatial_stability.*\.json"],
    "traffic_enrichment": [r"traffic_enrichment.*\.csv"],
    "capacity_impact": [r"capacity_impact.*\.csv"],
    "patrol_plan": [r"patrol_plan.*\.(csv|json)"],
    "evidence_ledger": [r"evidence_ledger.*\.csv"],
    "executive_report": [r"executive_report.*\.md"],
    # Not in the spec's core 11 outputs, but hotspot_detection.run_dbscan()
    # returns silhouette / bootstrap-CI metadata that the pipeline may persist
    # as a small sidecar file. Treated as fully optional — None when absent,
    # never fabricated.
    "dbscan_meta": [r"dbscan_meta.*\.json", r"hotspot_(detection_)?meta.*\.json"],
    # Optional per-cluster monthly panel (output of temporal_audit.build_monthly_panel).
    # Without this, per-cluster forecast falls back to a structured "insufficient
    # data" response rather than fabricating a series.
    "monthly_panel": [r"monthly_panel.*\.csv", r"cluster_monthly.*\.csv"],
}

# Required for the dashboard to be usable at all. Everything else is optional.
REQUIRED_ARTIFACTS = {"hotspot_clusters"}

_RUN_DIR_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}([T_]\d{2}-?\d{2}(-?\d{2})?)?$")


class ArtifactError(Exception):
    def __init__(self, code: str, message: str, artifact: Optional[str] = None, required: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.artifact = artifact
        self.required = required

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "artifact": self.artifact,
            "required": self.required,
        }


@dataclass
class _CacheEntry:
    mtime: float
    value: Any


@dataclass
class MergeDiagnostic:
    matched: int = 0
    unmatched: int = 0
    duplicate_keys: int = 0
    present: bool = False
    path: Optional[str] = None
    last_modified: Optional[str] = None
    row_count: Optional[int] = None
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "matched": self.matched,
            "unmatched": self.unmatched,
            "duplicate_keys": self.duplicate_keys,
            "present": self.present,
            "path": self.path,
            "last_modified": self.last_modified,
            "row_count": self.row_count,
            "error": self.error,
        }


def _resolve_run_dir(output_dir: Path, explicit_run_id: Optional[str]) -> Path:
    if not output_dir.exists():
        return output_dir  # caller surfaces a clear "not found" status

    if explicit_run_id:
        candidate = output_dir / explicit_run_id
        return candidate if candidate.exists() else output_dir

    # If any of the canonical artifacts live directly in output_dir, that
    # *is* the active run — don't go hunting for subdirectories.
    direct_hit = any(_find_file(output_dir, patterns) for patterns in ARTIFACT_PATTERNS.values())
    if direct_hit:
        return output_dir

    run_dirs = [
        d for d in output_dir.iterdir()
        if d.is_dir() and (_RUN_DIR_PATTERN.match(d.name) or True)
    ]
    if not run_dirs:
        return output_dir

    run_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return run_dirs[0]


def _find_file(directory: Path, patterns: List[str]) -> Optional[Path]:
    if not directory.exists():
        return None
    candidates = []
    for f in directory.iterdir():
        if not f.is_file():
            continue
        for pat in patterns:
            if re.match(pat, f.name, re.IGNORECASE):
                candidates.append(f)
                break
    if not candidates:
        return None
    # Prefer the most recently modified match if multiple versions exist.
    candidates.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return candidates[0]


# Some artifacts use column names that collide in meaning but not in name
# across files (e.g. every enrichment file has its own "validation_status").
# These explicit renames happen BEFORE the merge so the resulting hotspot
# record carries clear, disambiguated field names matching the actual
# pipeline module outputs (see traffic_enrichment.py / capacity_impact.py).
ARTIFACT_COLUMN_RENAMES: Dict[str, Dict[str, str]] = {
    "traffic_enrichment": {
        "mean_congestion_index": "congestion_index",
        "mean_avg_speed_kmh": "avg_speed_kmh",
        "mean_delay_minutes": "delay_minutes",
        "validation_status": "traffic_validation_status",
    },
    "capacity_impact": {
        "validation_status": "geometry_validation_status",
    },
    "risk_scores": {
        "validation_status": "risk_validation_status",
    },
}


def _normalize_cluster_id(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")


class ArtifactLoader:
    """Discovers, parses, caches, and merges ParkSight pipeline outputs."""

    def __init__(self, config: AppConfig):
        self._config = config
        self._cache: Dict[str, _CacheEntry] = {}
        self._yaml_cache: Optional[_CacheEntry] = None

    # ── Run / path resolution ────────────────────────────────────────

    @property
    def output_dir(self) -> Path:
        return self._config.output_dir

    def active_run_dir(self) -> Path:
        return _resolve_run_dir(self._config.output_dir, self._config.run_id)

    def active_run_label(self) -> Optional[str]:
        run_dir = self.active_run_dir()
        if run_dir == self._config.output_dir:
            return None
        return run_dir.name

    def list_runs(self) -> List[Dict[str, Any]]:
        out_dir = self._config.output_dir
        if not out_dir.exists():
            return []
        active = self.active_run_dir()
        runs = []
        for d in sorted([p for p in out_dir.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True):
            runs.append({
                "run_id": d.name,
                "path": str(d),
                "last_modified": pd.Timestamp(d.stat().st_mtime, unit="s").isoformat(),
                "is_active": d == active,
            })
        return runs

    def artifact_path(self, name: str) -> Optional[Path]:
        patterns = ARTIFACT_PATTERNS.get(name)
        if not patterns:
            raise ValueError(f"Unknown artifact name: {name}")
        return _find_file(self.active_run_dir(), patterns)

    def artifact_status(self) -> Tuple[List[str], List[str]]:
        available, missing = [], []
        for name in ARTIFACT_PATTERNS:
            (available if self.artifact_path(name) else missing).append(name)
        return available, missing

    # ── Settings.yaml ────────────────────────────────────────────────

    def settings_dict(self) -> Dict[str, Any]:
        path = self._config.settings_path
        if not path.exists():
            log.warning("settings.yaml not found at %s", path)
            return {}
        mtime = path.stat().st_mtime
        if self._yaml_cache and self._yaml_cache.mtime == mtime and self._config.cache_enabled:
            return self._yaml_cache.value
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        self._yaml_cache = _CacheEntry(mtime=mtime, value=data)
        return data

    # ── Generic cached read ──────────────────────────────────────────

    def _read_cached(self, path: Path, parser) -> Any:
        key = str(path)
        mtime = path.stat().st_mtime
        cached = self._cache.get(key)
        if cached and cached.mtime == mtime and self._config.cache_enabled:
            return cached.value
        value = parser(path)
        self._cache[key] = _CacheEntry(mtime=mtime, value=value)
        return value

    def read_csv(self, name: str, required: bool = False) -> Optional[pd.DataFrame]:
        path = self.artifact_path(name)
        if path is None:
            if required:
                raise ArtifactError(
                    "MISSING_ARTIFACT", f"{name} was not found in {self.active_run_dir()}.",
                    artifact=name, required=True,
                )
            return None
        try:
            df = self._read_cached(path, lambda p: pd.read_csv(p))
        except (pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
            raise ArtifactError("MALFORMED_ARTIFACT", f"{name} could not be parsed as CSV: {exc}",
                                 artifact=name, required=required)
        if df is None or df.empty:
            if required:
                raise ArtifactError("EMPTY_ARTIFACT", f"{name} is present but empty.", artifact=name, required=True)
            return df
        return df

    def read_json(self, name: str, required: bool = False) -> Optional[Dict[str, Any]]:
        path = self.artifact_path(name)
        if path is None:
            if required:
                raise ArtifactError(
                    "MISSING_ARTIFACT", f"{name} was not found in {self.active_run_dir()}.",
                    artifact=name, required=True,
                )
            return None
        try:
            data = self._read_cached(path, lambda p: json.loads(p.read_text()))
        except json.JSONDecodeError as exc:
            raise ArtifactError("MALFORMED_ARTIFACT", f"{name} could not be parsed as JSON: {exc}",
                                 artifact=name, required=required)
        return data

    # ── Hotspot merge ────────────────────────────────────────────────

    def merged_hotspots(self) -> Tuple[pd.DataFrame, Dict[str, MergeDiagnostic]]:
        """Left-merge risk_scores / capacity_impact / traffic_enrichment onto
        hotspot_clusters using cluster_id as the key. Optional artifacts that
        are absent never reduce the row count — they just leave their columns
        null for every row.
        """
        diagnostics: Dict[str, MergeDiagnostic] = {}

        base = self.read_csv("hotspot_clusters", required=True)
        base = base.copy()
        base["cluster_id"] = _normalize_cluster_id(base["cluster_id"])
        self._record_diag(diagnostics, "hotspot_clusters", base)

        dup_base = base["cluster_id"].duplicated().sum()
        if dup_base:
            log.warning("hotspot_clusters has %d duplicate cluster_id rows — keeping first occurrence", dup_base)
            diagnostics["hotspot_clusters"].duplicate_keys = int(dup_base)
            base = base.drop_duplicates(subset="cluster_id", keep="first")

        merged = base
        for name, prefix_cols in [
            ("risk_scores", None),
            ("capacity_impact", None),
            ("traffic_enrichment", None),
        ]:
            other = self.read_csv(name, required=False)
            if other is None or other.empty:
                diagnostics[name] = MergeDiagnostic(present=False)
                continue
            other = other.copy()
            other["cluster_id"] = _normalize_cluster_id(other["cluster_id"])
            dup = int(other["cluster_id"].duplicated().sum())
            if dup:
                log.warning("%s has %d duplicate cluster_id rows — keeping first occurrence", name, dup)
                other = other.drop_duplicates(subset="cluster_id", keep="first")

            rename_map = ARTIFACT_COLUMN_RENAMES.get(name, {})
            other = other.rename(columns=rename_map)

            overlap_cols = [c for c in other.columns if c in merged.columns and c != "cluster_id"]
            other_renamed = other.rename(columns={c: f"{name}__{c}" for c in overlap_cols})

            matched = int(merged["cluster_id"].isin(other_renamed["cluster_id"]).sum())
            unmatched = int(len(merged) - matched)

            merged = merged.merge(other_renamed, on="cluster_id", how="left")

            # Prefer the dedicated artifact's value where the base was null,
            # without ever silently discarding a real base value.
            for c in overlap_cols:
                renamed = f"{name}__{c}"
                if renamed in merged.columns:
                    merged[c] = merged[c].where(merged[c].notna(), merged[renamed])
                    merged = merged.drop(columns=[renamed])

            d = MergeDiagnostic(
                present=True, matched=matched, unmatched=unmatched, duplicate_keys=dup,
            )
            path = self.artifact_path(name)
            if path:
                d.path = str(path)
                d.last_modified = pd.Timestamp(path.stat().st_mtime, unit="s").isoformat()
                d.row_count = int(len(other))
            diagnostics[name] = d

        merged["cluster_id"] = merged["cluster_id"].astype(int)
        return merged, diagnostics

    def _record_diag(self, diagnostics: Dict[str, MergeDiagnostic], name: str, df: pd.DataFrame) -> None:
        path = self.artifact_path(name)
        d = MergeDiagnostic(present=True, matched=len(df), unmatched=0, duplicate_keys=0)
        if path:
            d.path = str(path)
            d.last_modified = pd.Timestamp(path.stat().st_mtime, unit="s").isoformat()
            d.row_count = int(len(df))
        diagnostics[name] = d


_loader_singleton: Optional[ArtifactLoader] = None


def get_artifact_loader() -> ArtifactLoader:
    global _loader_singleton
    if _loader_singleton is None:
        _loader_singleton = ArtifactLoader(app_config)
    return _loader_singleton
