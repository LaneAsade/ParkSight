"""
evidence.py — Builds the evidence ledger from every pipeline stage's output.

This module never invents a claim or upgrades a stage's reported
validation_status. It only restates, in one flat table, what each stage
already returned — so evidence_ledger.csv is a derived view, not a second
source of truth.
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

log = logging.getLogger(__name__)

_DASH = "\u2014"


def _row(claim: str, value: Any, status: str, source: str, confidence: Optional[str] = None) -> Dict[str, Any]:
    return {
        "claim": claim,
        "value": value,
        "status": status,
        "source": source,
        "confidence": confidence if confidence is not None else _DASH,
    }


def build_evidence_ledger(
    audit: Dict[str, Any],
    bias: Dict[str, Any],
    dbscan_meta: Dict[str, Any],
    risk_meta: Dict[str, Any],
    spatial: Dict[str, Any],
    traffic_df: Optional[pd.DataFrame],
    capacity_df: Optional[pd.DataFrame],
    patrol: Dict[str, Any],
) -> pd.DataFrame:
    """Aggregate every stage's metadata into a flat evidence_ledger table."""
    rows: List[Dict[str, Any]] = []

    if audit:
        rows.append(_row(
            "Total approved violations in source CSV", audit.get("n_approved"),
            "REAL_DATA", "violations.csv",
        ))
        rows.append(_row(
            "Approval rate", f"{audit.get('approved_pct')}%",
            "REAL_DATA", "violations.csv",
        ))
        if audit.get("validation_backlog_warning"):
            rows.append(_row(
                "Adjudication backlog detected", list(audit.get("review_backlog_months", {}).keys()),
                "REAL_DATA", "data_loader.py", "review-backlog heuristic",
            ))
        if audit.get("filename_date_mismatch_warning"):
            rows.append(_row(
                "Filename / actual date-range mismatch", audit.get("date_range_actual_ist"),
                "REAL_DATA", "data_loader.py", "filename vs timestamp check",
            ))

    if bias and not bias.get("skipped"):
        rows.append(_row(
            "Selection-bias pseudo-R\u00b2 (approval ~ vehicle+station+hour)",
            bias.get("mcfadden_pseudo_r2"), bias.get("validation_status", "REAL_DATA"),
            "bias_audit.py", bias.get("interpretation"),
        ))
    elif bias and bias.get("skipped"):
        rows.append(_row(
            "Selection-bias audit", "skipped", "SPEC_ONLY", "bias_audit.py", bias.get("reason"),
        ))

    if dbscan_meta:
        rows.append(_row(
            "DBSCAN hotspot cluster count", f"{dbscan_meta.get('n_clusters')} clusters",
            dbscan_meta.get("validation_status", "REAL_DATA"), "hotspot_detection.py",
            "90% CI bootstrap" if dbscan_meta.get("n_clusters_ci_90pct") else None,
        ))

    if risk_meta and not risk_meta.get("skipped"):
        rows.append(_row(
            "Clusters whose tier changed vs a count-only ranking",
            risk_meta.get("n_clusters_with_tier_changed_by_non_count_features"),
            "REAL_DATA", "risk_scoring.py", "honest non-count validation",
        ))

    if spatial and not spatial.get("skipped"):
        rows.append(_row(
            "Spatial stability (leave-one-district-out Jaccard, CRITICAL tier)",
            spatial.get("mean_critical_set_jaccard"), spatial.get("validation_status", "REAL_DATA"),
            "spatial_validation.py", spatial.get("interpretation"),
        ))

    if traffic_df is not None and not traffic_df.empty and "validation_status" in traffic_df.columns:
        real = int((traffic_df["validation_status"] == "REAL_DATA").sum())
        spec = int((traffic_df["validation_status"] == "SPEC_ONLY").sum())
        total = len(traffic_df)
        mean_cong = traffic_df["mean_congestion_index"].dropna()
        if not mean_cong.empty:
            rows.append(_row(
                "Mean congestion index from Distance Matrix probing",
                round(float(mean_cong.mean()), 2), "REAL_DATA", "Google Distance Matrix API",
                f"{real} of {total} hotspots",
            ))
        if spec:
            rows.append(_row(
                "Hotspots where traffic probe failed entirely", f"{spec} of {total}",
                "SPEC_ONLY", "traffic_enrichment.py", "no key / API failure",
            ))

    if capacity_df is not None and not capacity_df.empty:
        real = int((capacity_df["validation_status"] == "REAL_DATA").sum())
        total = len(capacity_df)
        rows.append(_row(
            "Hotspots with real road geometry (Mappls/OSM, not engineering fallback)",
            f"{real} of {total}", "REAL_DATA" if real else "SPEC_ONLY", "capacity_impact.py",
        ))

    if patrol:
        rows.append(_row(
            "Patrol CRITICAL-hotspot coverage", f"{patrol.get('critical_covered')}/{patrol.get('critical_total')}",
            patrol.get("validation_status", "MODELED"), "patrol_optimization.py",
            patrol.get("critical_coverage_mode"),
        ))

    rows.append(_row(
        "Annual economic impact (fuel/time/CO2)", "MODELED placeholder",
        "MODELED", "economic model (backend)", "fixed-rate assumptions",
    ))

    df = pd.DataFrame(rows, columns=["claim", "value", "status", "source", "confidence"])
    log.info("Evidence ledger: %d claims (%s)", len(df), dict(df["status"].value_counts()) if not df.empty else {})
    return df
