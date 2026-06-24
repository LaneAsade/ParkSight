# backend/app/routers/executive.py
from fastapi import APIRouter, Depends
from ..dependencies import get_loader
from ..services.executive_service import executive_summary

router = APIRouter(prefix="/api/executive", tags=["executive"])

@router.get("/summary")
def get_summary(loader=Depends(get_loader)):
    return executive_summary(loader)