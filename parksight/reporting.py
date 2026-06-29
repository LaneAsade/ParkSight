"""
reporting.py — Generates the human-readable executive_report.md summary.

Every figure quoted here is read back from a stage's own output dict/df —
this module performs no new computation, only formatting.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

log = logging.getLogger(__name__)


def _fmt(value: Any, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.2f}{suffix}"
    return f"{value}{suffix}"


def generate_executive_report(
    audit: Dict[str, Any],
    bias: Dict[str, Any],
    dbscan_meta: Dict[str, Any],
    risk_meta: Dict[str, Any],
    spatial: Dict[str, Any],
    clusters: List[Any],
    patrol: Dict[str, Any],
    evidence_df: Optional[pd.DataFrame],
    failures: Dict[str, str],
) -> str:
    """Build a Markdown executive summary of one pipeline run."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    n_critical = sum(1 for c in clusters if getattr(c, "risk_tier", None) == "CRITICAL")
    n_high = sum(1 for c in clusters if getattr(c, "risk_tier", None) == "HIGH")

    lines: List[str] = []
    lines.append("# ParkSight AI \u2014 Executive Report")
    lines.append("")
    lines.append(f"_Generated {now}_")
    lines.append("")
    lines.append(
        "This report summarizes one pipeline run. Every figure below carries an "
        "evidence label (`REAL_DATA`, `MODELED`, or `SPEC_ONLY`) in the underlying "
        "artifact files \u2014 see `evidence_ledger.csv` for the full chain."
    )
    lines.append("")

    lines.append("## 1. Data Volume")
    lines.append("")
    lines.append(f"- Total rows in source CSV: **{_fmt(audit.get('n_total_rows'))}**")
    lines.append(f"- Approved violations: **{_fmt(audit.get('n_approved'))}** ({_fmt(audit.get('approved_pct'), '%')})")
    lines.append(f"- Distinct police stations: **{_fmt(audit.get('n_distinct_police_stations'))}**")
    lines.append(f"- Distinct junctions: **{_fmt(audit.get('n_distinct_junctions'))}**")
    if audit.get("validation_backlog_warning"):
        lines.append(f"- \u26a0\ufe0f {audit['validation_backlog_warning']}")
    if audit.get("filename_date_mismatch_warning"):
        lines.append(f"- \u26a0\ufe0f {audit['filename_date_mismatch_warning']}")
    lines.append("")

    lines.append("## 2. Hotspot Detection")
    lines.append("")
    lines.append(f"- Hotspot clusters detected: **{len(clusters)}** "
                  f"(silhouette {_fmt(dbscan_meta.get('silhouette'))})")
    lines.append(f"- CRITICAL: **{n_critical}**  |  HIGH: **{n_high}**")
    if risk_meta and not risk_meta.get("skipped"):
        lines.append(
            f"- {risk_meta.get('n_clusters_with_tier_changed_by_non_count_features')} of "
            f"{len(clusters)} clusters land in a different tier than a violations-only ranking "
            "(the honest measure of whether non-count features matter)."
        )
    if spatial and not spatial.get("skipped"):
        lines.append(
            f"- Spatial stability (leave-one-district-out Jaccard on CRITICAL tier): "
            f"**{_fmt(spatial.get('mean_critical_set_jaccard'))}** \u2014 {spatial.get('interpretation')}"
        )
    lines.append("")

    lines.append("## 3. Selection-Bias Audit")
    lines.append("")
    if bias and not bias.get("skipped"):
        lines.append(f"- McFadden pseudo-R\u00b2: **{_fmt(bias.get('mcfadden_pseudo_r2'))}** \u2014 {bias.get('interpretation')}")
    else:
        lines.append(f"- Skipped: {(bias or {}).get('reason', 'insufficient adjudicated data.')}")
    lines.append("")

    lines.append("## 4. Patrol Optimization")
    lines.append("")
    if patrol:
        lines.append(
            f"- {patrol.get('n_teams_requested')} team(s) requested \u2192 "
            f"**{patrol.get('critical_covered')}/{patrol.get('critical_total')}** CRITICAL hotspots covered, "
            f"**{patrol.get('distinct_hotspots_covered')}/{patrol.get('distinct_hotspots_total')}** hotspots overall."
        )
        lines.append(f"- {patrol.get('critical_coverage_note')}")
    lines.append("")

    lines.append("## 5. Stage Failures")
    lines.append("")
    if failures:
        for stage, msg in failures.items():
            lines.append(f"- **{stage}**: {msg}")
    else:
        lines.append("- None \u2014 every stage completed.")
    lines.append("")

    lines.append("## 6. Evidence Summary")
    lines.append("")
    if evidence_df is not None and not evidence_df.empty:
        counts = evidence_df["status"].value_counts().to_dict()
        for status in ("REAL_DATA", "MODELED", "SPEC_ONLY", "PARTIAL"):
            if status in counts:
                lines.append(f"- {status}: **{counts[status]}** claim(s)")
    lines.append("")
    lines.append(
        "## Known Limitations\n\n"
        "1. Parking violations indicate where enforcement occurred, not a controlled "
        "measurement of congestion without parking \u2014 all congestion/capacity relationships "
        "are observational.\n"
        "2. District labels are synthetic rectangular grid cells, not real administrative boundaries.\n"
        "3. Economic figures are modeled from fixed-rate assumptions; `closed_datetime` is null "
        "in the source data, so there is no measured enforcement outcome to calibrate against.\n"
        "4. External APIs (Google, Mappls, OSM) may be unavailable in restricted environments; "
        "the pipeline runs fully offline with `SPEC_ONLY` labels when keys/connectivity are absent."
    )

    return "\n".join(lines) + "\n"
