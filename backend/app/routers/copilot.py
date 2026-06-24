"""app/routers/copilot.py"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Any, Dict, List

from ..dependencies import get_loader
from ..services.artifact_loader import ArtifactLoader
from ..services.copilot_service import answer_query

router = APIRouter(prefix="/api/copilot", tags=["copilot"])


class CopilotQueryRequest(BaseModel):
    query: str


class CopilotQueryOut(BaseModel):
    answer: str
    supporting_data: List[Dict[str, Any]] = []
    evidence_statuses: List[str] = []
    limitations: List[str] = []


@router.post("/query", response_model=CopilotQueryOut)
def post_query(body: CopilotQueryRequest, loader: ArtifactLoader = Depends(get_loader)):
    result = answer_query(loader, body.query)
    return CopilotQueryOut(**result)