"""app/routers/congestion.py"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import loader_dependency
from ..schemas import (
    CongestionByDistrictOut, CongestionRelationshipOut, CongestionSummaryOut, ErrorResponse,
)
from ..services.artifact_loader import ArtifactError, ArtifactLoader
from ..services.congestion_service import (
    congestion_by_district, congestion_for_hotspot, congestion_relationship, congestion_summary,
)

router = APIRouter(prefix="/api/congestion", tags=["congestion"])


@router.get("/summary", response_model=CongestionSummaryOut)
def get_summary(loader: ArtifactLoader = Depends(loader_dependency)) -> CongestionSummaryOut:
    try:
        return CongestionSummaryOut(**congestion_summary(loader))
    except ArtifactError as exc:
        raise HTTPException(status_code=404, detail=exc.to_dict()) from exc


@router.get("/by-district", response_model=list[CongestionByDistrictOut])
def get_by_district(loader: ArtifactLoader = Depends(loader_dependency)) -> list[CongestionByDistrictOut]:
    return [CongestionByDistrictOut(**r) for r in congestion_by_district(loader)]


@router.get("/hotspots/{cluster_id}")
def get_hotspot_congestion(cluster_id: int, loader: ArtifactLoader = Depends(loader_dependency)) -> dict:
    result = congestion_for_hotspot(loader, cluster_id)
    if not result:
        raise HTTPException(status_code=404, detail={
            "code": "HOTSPOT_NOT_FOUND", "message": f"No hotspot with cluster_id={cluster_id}.",
            "artifact": "hotspot_clusters", "required": False,
        })
    return result


@router.get("/relationship", response_model=CongestionRelationshipOut)
def get_relationship(loader: ArtifactLoader = Depends(loader_dependency)) -> CongestionRelationshipOut:
    return CongestionRelationshipOut(**congestion_relationship(loader))

