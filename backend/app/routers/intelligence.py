# backend/app/routers/intelligence.py
from fastapi import APIRouter, Depends
from ..dependencies import get_loader
from ..services.congestion_intelligence import congestion_intelligence

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])

@router.get("")
def get_intelligence(loader=Depends(get_loader)):
    return {"items": congestion_intelligence(loader)}