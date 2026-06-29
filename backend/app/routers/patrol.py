"""app/routers/patrol.py"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import loader_dependency
from ..services.artifact_loader import ArtifactLoader
from ..services.patrol_service import current_patrol, simulate_patrol
from ..config import app_config
from ..schemas import PatrolSimulateRequest

router = APIRouter(prefix="/api/patrol", tags=["patrol"])


@router.get("/current")
def get_current_patrol(loader: ArtifactLoader = Depends(loader_dependency)):
    return current_patrol(loader, app_config.default_patrol_teams)


@router.post("/simulate")
def post_simulate(body: PatrolSimulateRequest, loader: ArtifactLoader = Depends(loader_dependency)):
    merged, _ = loader.merged_hotspots()
    return simulate_patrol(loader, merged, body.teams)