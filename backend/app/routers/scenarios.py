"""app/routers/scenarios.py"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Any, Dict, Optional

from ..dependencies import loader_dependency
from ..services.artifact_loader import ArtifactLoader
from ..services.scenario_service import simulate_scenario

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


class EconomicOverrides(BaseModel):
    fuel_cost_per_litre: Optional[float] = None
    wage_inr_per_hour: Optional[float] = None
    enforcement_effectiveness_pct: Optional[float] = None
    scenario_multiplier: Optional[float] = None


class ScenarioSimulateRequest(BaseModel):
    additional_patrol_teams: int = 0
    risk_tier_thresholds: Optional[Dict[str, int]] = None
    economic_overrides: Optional[EconomicOverrides] = None
    assumed_violation_reduction_pct: float = 30.0


@router.post("/simulate")
def post_simulate(body: ScenarioSimulateRequest, loader: ArtifactLoader = Depends(loader_dependency)):
    economic_overrides = body.economic_overrides.dict() if body.economic_overrides else None
    return simulate_scenario(
        loader,
        additional_patrol_teams=body.additional_patrol_teams,
        risk_tier_thresholds=body.risk_tier_thresholds,
        economic_overrides=economic_overrides,
        assumed_violation_reduction_pct=body.assumed_violation_reduction_pct,
    )