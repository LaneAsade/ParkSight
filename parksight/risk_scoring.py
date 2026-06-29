"""
risk_scoring.py — Transparent percentile-rank risk scoring and tier assignment.

This is a pure formula on real violation counts and junction/vehicle/hour
attributes — there is no trained classifier involved.

The honest validation check is how many clusters change tier compared to a
count-only ranking, NOT the Spearman correlation with violation count (which
is circular by construction since count drives 55% of the score).
"""

import logging
from collections import Counter
from typing import Dict, List, Tuple

import numpy as np
from scipy.stats import spearmanr

from .config import Settings
from .hotspot_detection import HotspotCluster
from .utils import REAL_DATA, SPEC_ONLY

log = logging.getLogger(__name__)


def score_and_tier(
    clusters: List[HotspotCluster], settings: Settings
) -> Tuple[List[HotspotCluster], Dict]:
    """Assign risk scores and tiers to all clusters.

    Score = weighted percentile rank of:
        violations (55%) + at_junction% (25%) + vehicle_severity (10%) + peak_hour% (10%)

    Tiers are assigned at the 85th / 60th / 25th percentile breakpoints.
    """
    n = len(clusters)
    if n == 0:
        return clusters, {
            "validation_status": SPEC_ONLY,
            "skipped": True,
            "reason": "No hotspot clusters to score.",
            "tier_counts": {},
        }

    weights = settings.risk_weights
    thresholds = settings.tier_thresholds
    vehicle_weights = settings.vehicle_weights

    def pct_rank(arr: np.ndarray) -> np.ndarray:
        return arr.argsort().argsort().astype(float) / max(n - 1, 1)

    counts = np.array([c.violations for c in clusters], dtype=float)
    junc = np.array([c.pct_at_junction for c in clusters], dtype=float)
    veh = np.array([vehicle_weights.get(c.top_vehicle, 0.40) for c in clusters], dtype=float)
    peak = np.array([c.pct_peak_hour for c in clusters], dtype=float)

    raw = (
        weights["violation_count"] * pct_rank(counts)
        + weights["at_junction_pct"] * pct_rank(junc)
        + weights["vehicle_severity"] * pct_rank(veh)
        + weights["peak_hour_pct"] * pct_rank(peak)
    ) * 100

    for i, c in enumerate(clusters):
        c.risk_score = round(float(raw[i]), 1)

    p85 = np.percentile(raw, thresholds["critical"])
    p60 = np.percentile(raw, thresholds["high"])
    p25 = np.percentile(raw, thresholds["medium"])

    tier_cnt: Counter = Counter()
    for c in clusters:
        c.risk_tier = (
            "CRITICAL" if c.risk_score >= p85
            else "HIGH" if c.risk_score >= p60
            else "MEDIUM" if c.risk_score >= p25
            else "LOW"
        )
        tier_cnt[c.risk_tier] += 1

    # Honest validation: compare with count-only ranking
    count_only_raw = pct_rank(counts) * 100
    cp85 = np.percentile(count_only_raw, thresholds["critical"])
    cp60 = np.percentile(count_only_raw, thresholds["high"])
    cp25 = np.percentile(count_only_raw, thresholds["medium"])
    count_only_tiers = [
        "CRITICAL" if v >= cp85 else "HIGH" if v >= cp60 else "MEDIUM" if v >= cp25 else "LOW"
        for v in count_only_raw
    ]
    full_tiers = [c.risk_tier for c in clusters]
    n_tier_changes = sum(1 for a, b in zip(full_tiers, count_only_tiers) if a != b)
    changed = [
        {
            "cluster_id": clusters[i].cluster_id,
            "police_station": clusters[i].police_station,
            "count_only_tier": count_only_tiers[i],
            "full_formula_tier": full_tiers[i],
        }
        for i in range(n) if full_tiers[i] != count_only_tiers[i]
    ]

    rho, pval = spearmanr(raw, counts)
    log.info(
        "Risk tiers: %s | Non-count features changed tier for %d/%d clusters",
        dict(tier_cnt), n_tier_changes, n,
    )

    return clusters, {
        "validation_status": REAL_DATA,
        "method": (
            f"Weighted percentile rank: violations({weights['violation_count']}) "
            f"+ at_junction%({weights['at_junction_pct']}) "
            f"+ vehicle_severity({weights['vehicle_severity']}) "
            f"+ peak_hour%({weights['peak_hour_pct']}). Pure formula, not a trained model."
        ),
        "weights": weights,
        "tier_thresholds_percentile": thresholds,
        "tier_counts": dict(tier_cnt),
        "spearman_score_vs_violations": round(float(rho), 4),
        "spearman_caveat": (
            "Expected by construction (violations = 55% of score) — "
            "NOT independent validation of the formula."
        ),
        "n_clusters_with_tier_changed_by_non_count_features": n_tier_changes,
        "tier_changes_vs_count_only": changed,
        "non_count_interpretation": (
            f"{n_tier_changes} of {n} clusters land in a DIFFERENT tier than a "
            "violations-only ranking — this is the honest measure of whether "
            "junction/vehicle/peak features are doing anything."
        ),
    }
