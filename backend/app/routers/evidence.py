"""app/routers/evidence.py"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from ..dependencies import loader_dependency
from ..schemas import EvidenceListOut, EvidenceRecordOut, EvidenceSummaryOut
from ..services.artifact_loader import ArtifactLoader
from ..services.evidence_service import evidence_summary, list_evidence

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.get("", response_model=EvidenceListOut)
def get_evidence(
    status: Optional[str] = None,
    search: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    loader: ArtifactLoader = Depends(loader_dependency),
) -> EvidenceListOut:
    items, total = list_evidence(loader, status=status, search=search, source=source, limit=limit, offset=offset)
    return EvidenceListOut(total=total, limit=limit, offset=offset, items=[EvidenceRecordOut(**i) for i in items])


@router.get("/summary", response_model=EvidenceSummaryOut)
def get_evidence_summary(loader: ArtifactLoader = Depends(loader_dependency)) -> EvidenceSummaryOut:
    return EvidenceSummaryOut(**evidence_summary(loader))

