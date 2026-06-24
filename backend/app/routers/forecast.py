"""app/routers/forecast.py"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import loader_dependency
from ..schemas import ForecastOut
from ..services.artifact_loader import ArtifactLoader
from ..services.forecast_service import forecast_for_cluster, forecast_summary

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


@router.get("/summary")
def get_forecast_summary(loader: ArtifactLoader = Depends(loader_dependency)) -> dict:
    return forecast_summary(loader)


@router.get("/{cluster_id}", response_model=ForecastOut)
def get_forecast(cluster_id: int, loader: ArtifactLoader = Depends(loader_dependency)) -> ForecastOut:
    return ForecastOut(**forecast_for_cluster(loader, cluster_id))

