# backend/app/routers/impact_scores.py
from fastapi import APIRouter, Depends
from ..dependencies import get_loader
from ..services.impact_score_service import compute_impact_scores

router = APIRouter(prefix="/api/impact-scores", tags=["impact-scores"])

@router.get("")
def get_impact_scores(loader=Depends(get_loader)):
    return {"items": compute_impact_scores(loader)}