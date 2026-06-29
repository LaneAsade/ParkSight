"""
spatial_validation.py — Leave-one-district-out spatial stability validation.

Re-scores clusters excluding each synthetic district in turn and measures
Jaccard overlap of the CRITICAL set with the full-city result.
"""

import logging
import math
from typing import Dict, List

import numpy as np
from scipy.stats import spearmanr

from .config import Settings
from .hotspot_detection import HotspotCluster
from .utils import REAL_DATA, SPEC_ONLY

log = logging.getLogger(__name__)


def validate_spatial_stability(clusters: List[HotspotCluster], settings: Settings) -> Dict:
    """Leave-one-district-out Jaccard test on the CRITICAL tier."""
    if not clusters:
        return {"validation_status": SPEC_ONLY, "skipped": True, "reason": "No clusters to validate."}

    vehicle_weights = settings.vehicle_weights
    thresholds = settings.tier_thresholds
    weights = settings.risk_weights

    districts = sorted(set(c.district for c in clusters))
    global_critical = {c.cluster_id for c in clusters if c.risk_tier == "CRITICAL"}
    n_critical = len(global_critical)

    jaccards = []
    for held_out in districts:
        subset = [c for c in clusters if c.district != held_out]
        if len(subset) < 5:
            continue
        raw = _compute_raw_scores(subset, vehicle_weights, weights)
        p85 = np.percentile(raw, thresholds["critical"])
        local_crit = {subset[i].cluster_id for i in range(len(subset)) if raw[i] >= p85}
        universe = global_critical & {c.cluster_id for c in subset}
        if not (local_crit | universe):
            continue
        jac = len(local_crit & universe) / max(len(local_crit | universe), 1)
        jaccards.append(jac)

    mean_jac = float(np.mean(jaccards)) if jaccards else float("nan")

    rank_corrs = []
    for d in districts:
        sub = [c for c in clusters if c.district == d]
        if len(sub) < 5:
            continue
        global_ranks = [c.risk_score for c in sub]
        local_counts = np.array([c.violations for c in sub], dtype=float)
        rho, _ = spearmanr(global_ranks, local_counts)
        if not math.isnan(rho):
            rank_corrs.append(rho)
    mean_rank_corr = float(np.mean(rank_corrs)) if rank_corrs else float("nan")

    if jaccards:
        stable = mean_jac >= 0.6
        interpretation = (
            "STABLE: CRITICAL-tier membership is robust across district holdouts."
            if stable else
            "UNSTABLE: CRITICAL-tier membership is sensitive to district composition — "
            "prefer raw counts over tier labels for single-district analysis."
        )
    else:
        interpretation = "Insufficient districts with ≥5 clusters to test."

    small_n_caveat = (
        f"Only {n_critical} cluster(s) are CRITICAL citywide. "
        f"A single change shifts Jaccard by ~{100 / max(n_critical, 1):.0f}pp. "
        "Read stability verdict as 'nothing flipped in these folds,' not a strong guarantee."
    ) if jaccards else None

    log.info("Spatial stability: mean Jaccard=%.3f (%s)", mean_jac, interpretation)
    return {
        "validation_status": REAL_DATA if jaccards else SPEC_ONLY,
        "method": "Leave-one-district-out: recompute the same percentile-rank formula excluding each district.",
        "district_note": "Districts are synthetic rectangular grid cells — not real administrative boundaries.",
        "n_districts_tested": len(jaccards),
        "n_critical_clusters_global": n_critical,
        "mean_critical_set_jaccard": round(mean_jac, 3) if jaccards else None,
        "interpretation": interpretation,
        "mean_within_district_rank_correlation": round(mean_rank_corr, 3) if rank_corrs else None,
        "small_n_caveat": small_n_caveat,
        "honest_caveat": (
            "Validates the scoring rule's stability, not a model's ability to predict "
            "an unseen label. No learned generalization claim is being made."
        ),
    }


def _compute_raw_scores(
    subset: List[HotspotCluster],
    vehicle_weights: Dict,
    weights: Dict,
) -> np.ndarray:
    n = len(subset)

    def pr(a: np.ndarray) -> np.ndarray:
        return a.argsort().argsort().astype(float) / max(n - 1, 1)

    counts = np.array([c.violations for c in subset], dtype=float)
    junc = np.array([c.pct_at_junction for c in subset], dtype=float)
    veh = np.array([vehicle_weights.get(c.top_vehicle, 0.40) for c in subset], dtype=float)
    peak = np.array([c.pct_peak_hour for c in subset], dtype=float)

    return (
        weights["violation_count"] * pr(counts)
        + weights["at_junction_pct"] * pr(junc)
        + weights["vehicle_severity"] * pr(veh)
        + weights["peak_hour_pct"] * pr(peak)
    ) * 100
