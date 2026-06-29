"""
dashboard_service.py — builds the /api/overview response from all artifacts.
"""
from __future__ import annotations
from typing import Any, Dict, Optional
import pandas as pd
from .artifact_loader import ArtifactLoader


def build_overview(loader: ArtifactLoader, default_teams: int) -> Dict[str, Any]:
    temporal = loader.read_json("temporal_audit", required=False) or {}
    bias = loader.read_json("bias_audit", required=False) or {}
    dbscan = loader.read_json("dbscan_meta", required=False) or {}
    spatial = loader.read_json("spatial_stability", required=False) or {}
    evidence = loader.read_csv("evidence_ledger", required=False)
    available, missing = loader.artifact_status()

    try:
        merged, diag = loader.merged_hotspots()
        n_clusters = int(len(merged))
        n_critical = int((merged["risk_tier"] == "CRITICAL").sum())
        n_districts = int(merged["district"].nunique()) if "district" in merged.columns else 0
        mean_cong = None
        cong_status = "SPEC_ONLY"
        if "congestion_index" in merged.columns:
            vals = merged["congestion_index"].dropna()
            if not vals.empty:
                mean_cong = round(float(vals.mean()), 3)
                cong_status = "PARTIAL"
    except Exception:
        merged = pd.DataFrame()
        n_clusters = None
        n_critical = None
        n_districts = None
        mean_cong = None
        cong_status = "SPEC_ONLY"
        diag = {}

    nj = loader.read_csv("nonjunction_hotspots", required=False)
    n_nonjunction = int(len(nj)) if nj is not None else 0

    patrol_coverage = None
    patrol_teams = default_teams
    if n_clusters and not merged.empty:
        try:
            from .patrol_service import simulate_patrol
            sim = simulate_patrol(loader, merged, default_teams)
            patrol_coverage = sim.get("overall_coverage_pct")
        except Exception:
            patrol_coverage = None

    evidence_counts: Dict[str, int] = {}
    if evidence is not None and not evidence.empty and "status" in evidence.columns:
        evidence_counts = {str(k): int(v) for k, v in evidence["status"].value_counts().items()}

    last_update = None
    for name in ("hotspot_clusters", "evidence_ledger", "executive_report"):
        path = loader.artifact_path(name)
        if path:
            last_update = pd.Timestamp(path.stat().st_mtime, unit="s").isoformat()
            break

    return {
        "total_approved_violations": temporal.get("n_approved"),
        "approval_pct": temporal.get("approved_pct"),
        "n_hotspot_clusters": n_clusters,
        "n_critical_hotspots": n_critical,
        "n_nonjunction_hotspots": n_nonjunction,
        "active_districts": n_districts,
        "mean_congestion_index": mean_cong,
        "mean_congestion_validation_status": cong_status,
        "patrol_coverage_pct": patrol_coverage,
        "patrol_teams_used": patrol_teams,
        "date_range_start": (temporal.get("date_range_actual_ist") or [None])[0],
        "date_range_end": (temporal.get("date_range_actual_ist") or [None, None])[-1],
        "distinct_police_stations": temporal.get("n_distinct_police_stations"),
        "distinct_junctions": temporal.get("n_distinct_junctions"),
        "dbscan_silhouette": dbscan.get("silhouette"),
        "cluster_count_ci": dbscan.get("n_clusters_ci_90pct"),
        "spatial_stability_score": spatial.get("mean_critical_set_jaccard"),
        "spatial_stability_interpretation": spatial.get("interpretation"),
        "bias_pseudo_r2": bias.get("mcfadden_pseudo_r2"),
        "bias_interpretation": bias.get("interpretation"),
        "backlog_warning": temporal.get("validation_backlog_warning"),
        "filename_date_mismatch_warning": temporal.get("filename_date_mismatch_warning"),
        "evidence_status_counts": evidence_counts,
        "available_artifacts": available,
        "missing_artifacts": missing,
        "active_run": loader.active_run_label(),
        "last_pipeline_update": last_update,
    }