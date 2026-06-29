"""
patrol_optimization.py — MILP-based patrol team assignment.

Assigns patrol teams to shifts and hotspots using scipy.optimize.milp.
Guarantees every CRITICAL hotspot gets at least one shift when n_teams ≥
n_critical; auto-relaxes to a soft preference when n_critical > n_teams
(rather than returning zero assignments citywide).
"""

import logging
from typing import Dict, List

import numpy as np

from .config import Settings
from .hotspot_detection import HotspotCluster
from .utils import REAL_DATA, SPEC_ONLY

log = logging.getLogger(__name__)


def milp_assignment(clusters: List[HotspotCluster], n_teams: int, settings: Settings) -> Dict:
    """Assign n_teams patrol teams to shifts across hotspot clusters.

    Returns a metadata dict (including the 'assignments' list) written to patrol_plan.csv.
    """
    shifts = settings.patrol_shifts
    S = len(shifts)
    base_cap = n_teams // S
    remainder = n_teams % S
    shift_caps = [base_cap + (1 if s < remainder else 0) for s in range(S)]
    assert sum(shift_caps) == n_teams
    shift_capacities = dict(zip(shifts, shift_caps))

    if not clusters:
        return {
            "validation_status": SPEC_ONLY,
            "solved_to_optimality": False,
            "n_teams_requested": n_teams,
            "n_assignments": 0,
            "critical_covered": 0,
            "critical_total": 0,
            "skipped_reason": "No hotspot clusters to assign patrols to.",
            "assignments": [],
            "shifts": shifts,
            "shift_capacities": shift_capacities,
        }

    H = len(clusters)
    n_vars = H * S
    soft_bonus = settings.get("patrol", "critical_soft_bonus", default=10.0)
    time_limit = settings.get("patrol", "solver_time_limit_s", default=20.0)

    def shift_for_hour(h: int) -> int:
        if 2 <= h < 7: return 0
        if 7 <= h < 12: return 1
        if 12 <= h < 19: return 2
        return 3

    max_viol = max(c.violations for c in clusters)
    impact = np.array([max(c.violations / max_viol, 0.01) if max_viol else 0.01 for c in clusters])

    n_critical = sum(1 for c in clusters if c.risk_tier == "CRITICAL")
    require_hard_coverage = n_critical <= n_teams

    try:
        from scipy.optimize import milp, LinearConstraint, Bounds

        c_obj = np.zeros(n_vars)
        for h in range(H):
            is_crit = clusters[h].risk_tier == "CRITICAL"
            bonus = soft_bonus if (is_crit and not require_hard_coverage) else 0.0
            pref = 0.05 if shift_for_hour(clusters[h].peak_hour) < S else 0.0
            for s in range(S):
                c_obj[h * S + s] = -(impact[h] + pref + bonus)

        a_rows, b_lo, b_hi = [], [], []
        for h in range(H):
            row = np.zeros(n_vars)
            for s in range(S):
                row[h * S + s] = 1.0
            a_rows.append(row)
            b_lo.append(1.0 if (clusters[h].risk_tier == "CRITICAL" and require_hard_coverage) else 0.0)
            b_hi.append(1.0)
        for s in range(S):
            row = np.zeros(n_vars)
            for h in range(H):
                row[h * S + s] = 1.0
            a_rows.append(row)
            b_lo.append(0.0)
            b_hi.append(float(shift_caps[s]))

        lc = LinearConstraint(np.array(a_rows), b_lo, b_hi)
        bnd = Bounds(lb=0.0, ub=1.0)
        res = milp(c_obj, constraints=lc, integrality=np.ones(n_vars, dtype=int),
                   bounds=bnd, options={"time_limit": time_limit})
        solved = res.success and res.x is not None
    except Exception as exc:
        log.warning("MILP solver error: %s — using greedy fallback", exc)
        solved = False
        res = None

    used_greedy = False
    if solved:
        x = np.round(res.x).astype(int)
    else:
        used_greedy = True
        order = sorted(range(H), key=lambda h: (clusters[h].risk_tier != "CRITICAL", -impact[h]))
        x = np.zeros(n_vars, dtype=int)
        remaining = list(shift_caps)
        for h in order[:min(sum(shift_caps), H)]:
            preferred = shift_for_hour(clusters[h].peak_hour)
            for s in [preferred] + [i for i in range(S) if i != preferred]:
                if remaining[s] > 0:
                    x[h * S + s] = 1
                    remaining[s] -= 1
                    break

    assignments, covered_crit, covered_ids = [], 0, set()
    for h in range(H):
        for s in range(S):
            if x[h * S + s] == 1:
                assignments.append({
                    "cluster_id": clusters[h].cluster_id,
                    "hotspot": clusters[h].police_station,
                    "top_junction": clusters[h].top_junction,
                    "risk_tier": clusters[h].risk_tier,
                    "shift": shifts[s],
                    "impact_score": round(float(impact[h]), 4),
                })
                covered_ids.add(clusters[h].cluster_id)
                if clusters[h].risk_tier == "CRITICAL":
                    covered_crit += 1

    n_placeable = min(sum(shift_caps), H)
    log.info(
        "Patrol: %d assignments | critical %d/%d | hotspots %d/%d | mode=%s",
        len(assignments), covered_crit, n_critical, len(covered_ids), H,
        "hard_constraint" if require_hard_coverage else "soft_preference",
    )

    return {
        "validation_status": REAL_DATA,
        "solved_to_optimality": solved and not used_greedy,
        "used_greedy_fallback": used_greedy,
        "n_teams_requested": n_teams,
        "n_teams_placeable": n_placeable,
        "n_assignments": len(assignments),
        "critical_covered": covered_crit,
        "critical_total": n_critical,
        "distinct_hotspots_covered": len(covered_ids),
        "distinct_hotspots_total": H,
        "critical_coverage_mode": (
            "hard_constraint_full_coverage" if require_hard_coverage
            else "soft_preference_relaxed"
        ),
        "critical_coverage_note": (
            f"{n_critical} CRITICAL hotspot(s), {n_teams} team(s). "
            + (
                "Full CRITICAL coverage enforced as hard constraint."
                if require_hard_coverage else
                f"{n_critical} > {n_teams}: hard constraint relaxed to soft objective preference — "
                "all teams still placed, prioritizing CRITICAL hotspots."
            )
        ),
        "shifts": shifts,
        "shift_capacities": shift_capacities,
        "assignments": assignments,
    }
