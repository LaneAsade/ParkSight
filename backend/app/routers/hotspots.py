"""app/routers/hotspots.py"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import loader_dependency
from ..schemas import ErrorResponse, HotspotListOut, HotspotOut, NonJunctionHotspotOut
from ..services.artifact_loader import ArtifactError, ArtifactLoader
from ..services.hotspot_service import get_hotspot, list_hotspots, list_nonjunction_hotspots

router = APIRouter(prefix="/api/hotspots", tags=["hotspots"])


@router.get("", response_model=HotspotListOut, responses={404: {"model": ErrorResponse}})
def get_hotspots(
    district: Optional[str] = None,
    risk_tier: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    police_station: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort_by: str = "violations",
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    loader: ArtifactLoader = Depends(loader_dependency),
) -> HotspotListOut:
    try:
        items, total = list_hotspots(
            loader, district=district, risk_tier=risk_tier, vehicle_type=vehicle_type,
            police_station=police_station, search=search, limit=limit, offset=offset,
            sort_by=sort_by, sort_order=sort_order,
        )
    except ArtifactError as exc:
        raise HTTPException(status_code=404, detail=exc.to_dict()) from exc
    return HotspotListOut(total=total, limit=limit, offset=offset, items=[HotspotOut(**i) for i in items])


@router.get("/{cluster_id}", response_model=HotspotOut, responses={404: {"model": ErrorResponse}})
def get_hotspot_detail(cluster_id: int, loader: ArtifactLoader = Depends(loader_dependency)) -> HotspotOut:
    try:
        record = get_hotspot(loader, cluster_id)
    except ArtifactError as exc:
        raise HTTPException(status_code=404, detail=exc.to_dict()) from exc
    if record is None:
        raise HTTPException(status_code=404, detail={
            "code": "HOTSPOT_NOT_FOUND", "message": f"No hotspot with cluster_id={cluster_id}.",
            "artifact": "hotspot_clusters", "required": False,
        })
    return HotspotOut(**record)


nonjunction_router = APIRouter(prefix="/api", tags=["hotspots"])

@nonjunction_router.get("/nonjunction-hotspots", response_model=list[NonJunctionHotspotOut])
def get_nonjunction_hotspots(loader: ArtifactLoader = Depends(loader_dependency)) -> list[NonJunctionHotspotOut]:
    return [NonJunctionHotspotOut(**r) for r in list_nonjunction_hotspots(loader)]