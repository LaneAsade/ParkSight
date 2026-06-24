"""
app/services/scenario_service.py — Scenario Simulator backend.

Stacks patrol-team, risk-threshold, economic, and violation-reduction
interventions on top of the real baseline computed from current artifacts.
`settings.yaml` is never mutated — thresholds are recomputed in memory only.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from .artifact_loader import ArtifactLoader
from .economic_service import simulate_economic
from .patrol_service import simulate_patrol
from ..config import app_config


def _tier_with_thresholds(merged, critical_pct: float, high_pct: float, medium_pct: float) -> int:
    scores = merged["risk_score"].dropna()
    if scores.empty:
        return 0
    p85 = np.percentile(scores, critical_pct)
    return int((scores >= p85).sum())


def simulate_scenario(
    loader: ArtifactLoader,
    additional_patrol_teams: int,
    risk_tier_thresholds: Optional[Dict[str, int]],
    economic_overrides: Optional[Dict[str, Any]],
    assumed_violation_reduction_pct: float,
) -> Dict[str, Any]:
    merged, _ = loader.merged_hotspots()
    base_teams = app_config.default_patrol_teams
    scenario_teams = base_teams + additional_patrol_teams

    baseline_patrol = simulate_patrol(loader, merged, base_teams)
    scenario_patrol = simulate_patrol(loader, merged, scenario_teams)

    thresholds = risk_tier_thresholds or {}
    critical_pct = thresholds.get("critical", 85)
    baseline_critical = int((merged["risk_tier"] == "CRITICAL").sum())
    scenario_critical = _tier_with_thresholds(merged, critical_pct, thresholds.get("high", 60), thresholds.get("medium", 25))

    econ_kwargs = dict(
        fuel_cost_per_litre=None, wage_inr_per_hour=None,
        enforcement_effectiveness_pct=55.0, scenario_multiplier=1.0,
    )
    if economic_overrides:
        econ_kwargs.update({k: v for k, v in economic_overrides.items() if v is not None})

    baseline_econ = simulate_economic(loader, **econ_kwargs)

    reduction_factor = 1 - (assumed_violation_reduction_pct / 100.0)
    scenario_econ_kwargs = dict(econ_kwargs)
    scenario_econ_kwargs["scenario_multiplier"] = econ_kwargs["scenario_multiplier"] * reduction_factor
    scenario_econ = simulate_economic(loader, **scenario_econ_kwargs)

    def sv(value, status, assumptions):
        return {"value": value, "validation_status": status, "assumptions": assumptions}

    baseline = {
        "coverage_pct": sv(baseline_patrol["overall_coverage_pct"], baseline_patrol["validation_status"],
                            [f"{base_teams} patrol teams"]),
        "critical_covered": sv(baseline_patrol["critical_covered"], baseline_patrol["validation_status"],
                                [f"{base_teams} patrol teams"]),
        "critical_hotspots": sv(baseline_critical, "REAL_DATA", ["85th percentile threshold (default)"]),
        "annual_modeled_impact_inr": sv(baseline_econ.get("total_modeled_impact_inr_per_year"),
                                         baseline_econ["validation_status"], ["default economic assumptions"]),
    }
    scenario = {
        "coverage_pct": sv(scenario_patrol["overall_coverage_pct"], scenario_patrol["validation_status"],
                            [f"{scenario_teams} patrol teams (+{additional_patrol_teams})"]),
        "critical_covered": sv(scenario_patrol["critical_covered"], scenario_patrol["validation_status"],
                                [f"{scenario_teams} patrol teams (+{additional_patrol_teams})"]),
        "critical_hotspots": sv(scenario_critical, "MODELED",
                                 [f"{critical_pct}th percentile threshold" if thresholds else "unchanged threshold"]),
        "annual_modeled_impact_inr": sv(scenario_econ.get("total_modeled_impact_inr_per_year"),
                                         scenario_econ["validation_status"],
                                         [f"{assumed_violation_reduction_pct}% assumed violation reduction"] + (
                                             list(f"{k}={v}" for k, v in (economic_overrides or {}).items() if v is not None)
                                         )),
    }
    return {"baseline": baseline, "scenario": scenario}

