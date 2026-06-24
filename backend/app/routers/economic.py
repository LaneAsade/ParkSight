"""app/routers/economic.py"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import loader_dependency
from ..schemas import EconomicAssumptionsOut, EconomicSimulateOut, EconomicSimulateRequest
from ..services.artifact_loader import ArtifactLoader
from ..services.economic_service import economic_assumptions, simulate_economic

router = APIRouter(prefix="/api/economic", tags=["economic"])


@router.get("/assumptions", response_model=EconomicAssumptionsOut)
def get_assumptions(loader: ArtifactLoader = Depends(loader_dependency)) -> EconomicAssumptionsOut:
    return EconomicAssumptionsOut(**economic_assumptions(loader))


@router.post("/simulate", response_model=EconomicSimulateOut)
def post_simulate(
    body: EconomicSimulateRequest, loader: ArtifactLoader = Depends(loader_dependency)
) -> EconomicSimulateOut:
    result = simulate_economic(
        loader,
        fuel_cost_per_litre=body.fuel_cost_per_litre,
        wage_inr_per_hour=body.wage_inr_per_hour,
        enforcement_effectiveness_pct=body.enforcement_effectiveness_pct,
        scenario_multiplier=body.scenario_multiplier,
    )
    return EconomicSimulateOut(**result)

