"""app/routers/overview.py"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..config import app_config
from ..dependencies import loader_dependency
from ..schemas import OverviewOut
from ..services.artifact_loader import ArtifactLoader
from ..services.dashboard_service import build_overview

router = APIRouter(prefix="/api", tags=["overview"])


@router.get("/overview", response_model=OverviewOut)
def get_overview(loader: ArtifactLoader = Depends(loader_dependency)) -> OverviewOut:
    return OverviewOut(**build_overview(loader, app_config.default_patrol_teams))

