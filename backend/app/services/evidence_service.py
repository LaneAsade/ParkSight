from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from .artifact_loader import ArtifactLoader


def evidence_summary(loader: ArtifactLoader) -> Dict[str, Any]:
    df = loader.read_csv("evidence_ledger", required=False)
    if df is None or df.empty:
        return {"total": 0, "counts": {}}
    df = df.replace({np.nan: None})
    counts = {str(k): int(v) for k, v in df["status"].value_counts().items()} \
        if "status" in df.columns else {}
    return {
        "total": len(df),
        "counts": counts,
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
        df = df[df["status"] == status.upper()]
    if search:
        df = df[df["claim"].str.contains(search, case=False, na=False)]
    if source:
        df = df[df["source"] == source] if "source" in df.columns else df

    total = len(df)
    page = df.iloc[offset: offset + limit]
    return page.to_dict(orient="records"), total