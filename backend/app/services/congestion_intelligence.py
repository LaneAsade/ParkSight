# backend/app/services/congestion_intelligence.py
"""
Congestion Intelligence Layer — converts analytics into operational decisions.

Outputs per hotspot:
  - Congestion Severity label
  - Capacity Recovery Potential
  - Expected Enforcement Impact
  - Recommended Action
  - Expected Recovery %
  - Priority (Immediate / High / Medium / Low)
"""

from __future__ import annotations
from typing import Any, Dict, List
import numpy as np
from .artifact_loader import ArtifactLoader
from .impact_score_service import compute_impact_scores


_PATROL_COVERAGE_RADIUS_KM = 2.0


def congestion_intelligence(loader: ArtifactLoader) -> List[Dict[str, Any]]:
    scores = compute_impact_scores(loader)
    merged, _ = loader.merged_hotspots()

    # Build lookup
    hotspot_map = {int(r["cluster_id"]): r for _, r in merged.iterrows()}

    results = []
    for s in scores:
        cid = s["cluster_id"]
        row = hotspot_map.get(cid, {})

        cap_loss = s.get("capacity_loss_pct") or 0
        cong_idx = s.get("congestion_index") or 1.0
        impact = s["impact_score"]

        # Severity label
        if cong_idx >= 2.0 or cap_loss >= 30:
            severity = "HIGH"
        elif cong_idx >= 1.4 or cap_loss >= 15:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        # How many teams to recommend
        if impact >= 75:
            teams = 3
            priority = "Immediate"
        elif impact >= 50:
            teams = 2
            priority = "High"
        elif impact >= 25:
            teams = 1
            priority = "Medium"
        else:
            teams = 0
            priority = "Low"

        # Expected recovery (modelled: ~60% of cap_loss recovered per team)
        recovery = min(cap_loss * 0.6 * teams, cap_loss) if teams > 0 else 0

        action = (
            f"Deploy {teams} patrol team{'s' if teams != 1 else ''}"
            if teams > 0
            else "Monitor — no immediate action required"
        )

        results.append({
            "cluster_id": cid,
            "top_junction": s.get("top_junction"),
            "district": s.get("district"),
            "impact_score": impact,
            "priority_tier": s["priority"],
            "congestion_severity": severity,
            "capacity_loss_pct": cap_loss,
            "congestion_index": cong_idx,
            "recommended_action": action,
            "patrol_teams_recommended": teams,
            "expected_recovery_pct": round(recovery, 1),
            "enforcement_priority": priority,
            "lat": s.get("lat"),
            "lon": s.get("lon"),
        })

    return results