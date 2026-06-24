# backend/app/services/executive_service.py
"""
Executive Intelligence Dashboard — top-line summary for senior decision makers.
"""

from __future__ import annotations
from typing import Any, Dict, List
from .artifact_loader import ArtifactLoader
from .impact_score_service import compute_impact_scores
from .congestion_intelligence import congestion_intelligence
from .economic_service import simulate_economic


def executive_summary(loader: ArtifactLoader) -> Dict[str, Any]:
    scores = compute_impact_scores(loader)
    intel = congestion_intelligence(loader)
    econ = simulate_economic(loader)

    top5_drivers = scores[:5]

    # Highest capacity loss corridors
    cap_sorted = sorted(
        [s for s in scores if s.get("capacity_loss_pct")],
        key=lambda x: x["capacity_loss_pct"],
        reverse=True,
    )[:5]

    # Most impactful enforcement opportunities (highest expected recovery)
    intel_sorted = sorted(intel, key=lambda x: x["expected_recovery_pct"], reverse=True)[:5]

    # Immediate actions count
    immediate_count = sum(1 for i in intel if i["enforcement_priority"] == "Immediate")
    high_count = sum(1 for i in intel if i["enforcement_priority"] == "High")

    total_expected_recovery = sum(i["expected_recovery_pct"] for i in intel) / max(len(intel), 1)

    return {
        "top5_congestion_drivers": top5_drivers,
        "highest_capacity_loss_corridors": cap_sorted,
        "top5_enforcement_opportunities": intel_sorted,
        "total_hotspots": len(scores),
        "critical_zones": sum(1 for s in scores if s["priority"] == "CRITICAL"),
        "high_zones": sum(1 for s in scores if s["priority"] == "HIGH"),
        "immediate_actions_required": immediate_count,
        "high_priority_actions": high_count,
        "avg_expected_recovery_pct": round(total_expected_recovery, 1),
        "economic_summary": {
            "total_modeled_impact_inr_per_year": econ.get("total_modeled_impact_inr_per_year"),
            "validation_status": econ.get("validation_status", "MODELED"),
        },
        "recommended_actions": [
            f"Deploy patrol to {i['top_junction']} — expected {i['expected_recovery_pct']}% recovery"
            for i in intel_sorted[:3]
            if i.get("top_junction")
        ],
        "validation_status": "MODELED",
    }