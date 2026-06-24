# backend/app/routers/events.py
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..dependencies import get_loader
from ..services.event_simulator import simulate_event

router = APIRouter(prefix="/api/events", tags=["events"])


class EventRequest(BaseModel):
    event_name: str
    venue_name: str
    venue_lat: float
    venue_lon: float
    attendance: int
    venue_capacity: int


@router.post("/simulate")
def simulate(req: EventRequest, loader=Depends(get_loader)):
    from ..services.hotspot_service import list_hotspots
    items, _ = list_hotspots(loader)           # ← call with no extra args
    return simulate_event(
        event_name=req.event_name,
        venue_name=req.venue_name,
        venue_lat=req.venue_lat,
        venue_lon=req.venue_lon,
        attendance=req.attendance,
        venue_capacity=req.venue_capacity,
        hotspots=items,
    )