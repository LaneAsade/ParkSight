"""
app/services/congestion_service.py — Congestion summaries, by-district
breakdowns, and the violations-vs-congestion relationship dataset.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .artifact_loader import ArtifactLoader


def _status_col(df: pd.DataFrame) -> str:
    return "traffic_validation_status" if "traffic_validation_status" in df.columns else "traffic_validation"


def congestion_summary(loader: ArtifactLoader) -> Dict[str, Any]:
    merged, _ = loader.merged_hotspots()
    col = _status_col(merged)
    statuses = merged[col] if col in merged.columns else pd.Series(dtype=object)

    return {
        "total_hotspots": int(len(merged)),
        "real_data_count": int((statuses == "REAL_DATA").sum()),
        "partial_count": int((statuses == "PARTIAL").sum()),
        "spec_only_count": int((statuses == "SPEC_ONLY").sum()),
        "mean_congestion_index": _round_or_none(merged.get("congestion_index")),
        "mean_delay_minutes": _round_or_none(merged.get("delay_minutes")),
    }


def congestion_by_district(loader: ArtifactLoader) -> List[Dict[str, Any]]:
    merged, _ = loader.merged_hotspots()
    if "district" not in merged.columns:
        return []
    out = []
    for district, group in merged.groupby("district"):
        out.append({
            "district": district,
            "n_hotspots": int(len(group)),
            "mean_delay_minutes": _round_or_none(group.get("delay_minutes")),
            "mean_congestion_index": _round_or_none(group.get("congestion_index")),
        })
    out.sort(key=lambda r: r["n_hotspots"], reverse=True)
    return out


def congestion_for_hotspot(loader: ArtifactLoader, cluster_id: int) -> Dict[str, Any]:
    merged, _ = loader.merged_hotspots()
    match = merged[merged["cluster_id"] == cluster_id]
    if match.empty:
        return {}
    row = match.iloc[0].replace({np.nan: None})
    return {
        "cluster_id": int(cluster_id),
        "congestion_index": row.get("congestion_index"),
        "delay_minutes": row.get("delay_minutes"),
        "avg_speed_kmh": row.get("avg_speed_kmh"),
        "validation_status": row.get(_status_col(merged)),
    }


def congestion_relationship(loader: ArtifactLoader) -> Dict[str, Any]:
    merged, _ = loader.merged_hotspots()
    col = _status_col(merged)
    points = []
    for _, row in merged.iterrows():
        cong = row.get("congestion_index")
        status = row.get(col)
        points.append({
            "cluster_id": int(row["cluster_id"]),
            "violations": int(row["violations"]) if pd.notna(row.get("violations")) else 0,
            "congestion_index": None if pd.isna(cong) else float(cong),
            "risk_tier": row.get("risk_tier"),
            "validation_status": status if isinstance(status, str) else "SPEC_ONLY",
        })

    status_counts: Dict[str, int] = {}
    if col in merged.columns:
        status_counts = {str(k): int(v) for k, v in merged[col].value_counts().to_dict().items()}

    sample_size = sum(1 for p in points if p["congestion_index"] is not None)

    return {
        "points": points,
        "sample_size": sample_size,
        "validation_status_counts": status_counts,
    }


def _round_or_none(series) -> float | None:
    if series is None:
        return None
    series = series.dropna()
    if series.empty:
        return None
    return round(float(series.mean()), 3)

