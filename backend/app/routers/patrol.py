"""app/routers/patrol.py"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..dependencies import loader_dependency
from ..services.artifact_loader import ArtifactLoader
from ..services.patrol_service import current_patrol, simulate_patrol
from ..config import app_config

router = APIRouter(prefix="/api/patrol", tags=["patrol"])


class PatrolSimulateRequest(BaseModel):
    n_teams: int = 10


@router.get("/current")
def get_current_patrol(loader: ArtifactLoader = Depends(loader_dependency)):
    return current_patrol(loader, app_config.default_patrol_teams)


@router.post("/simulate")
def post_simulate(body: PatrolSimulateRequest, loader: ArtifactLoader = Depends(loader_dependency)):
    merged, _ = loader.merged_hotspots()
    return simulate_patrol(loader, merged, body.n_teams)