from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from .artifact_loader import ArtifactLoader


def evidence_summary(loader: ArtifactLoader) -> Dict[str, Any]:
    df = loader.read_csv("evidence_ledger", required=False)
    if df is None or df.empty:
        return {
            "validation_status": "SPEC_ONLY",
            "skipped_reason": "No evidence_ledger artifact found.",
            "total_claims": 0,
            "status_counts": {},
        }
    df = df.replace({np.nan: None})
    counts = {str(k): int(v) for k, v in df["validation_status"].value_counts().items()} \
        if "validation_status" in df.columns else {}
    return {
        "validation_status": "REAL_DATA",
        "total_claims": len(df),
        "status_counts": counts,
    }


def list_evidence(
    loader: ArtifactLoader,
    status: Optional[str] = None,
    search: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    df = loader.read_csv("evidence_ledger", required=False)
    if df is None or df.empty:
        return [], 0
    df = df.replace({np.nan: None})

    if status:
        df = df[df["validation_status"] == status.upper()]
    if search:
        df = df[df["claim"].str.contains(search, case=False, na=False)]
    if source:
        df = df[df["source_module"] == source] if "source_module" in df.columns else df

    total = len(df)
    page = df.iloc[offset: offset + limit]
    return page.to_dict(orient="records"), total