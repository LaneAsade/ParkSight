"""
app/services/hotspot_service.py — Hotspot listing, detail, and non-junction
hotspot retrieval.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .artifact_loader import ArtifactLoader

_NULLABLE_NUMERIC = [
    "congestion_index", "delay_minutes", "avg_speed_kmh",
    "lane_count", "road_width_m", "capacity_loss_pct", "erci_index",
    "ci_low", "ci_high",
]


def _row_to_dict(row: pd.Series) -> Dict[str, Any]:
    d = row.replace({np.nan: None}).to_dict()
    # station_breakdown may arrive as a stringified dict from CSV — leave as-is if so.
    return d


def _coerce_optional(d: Dict[str, Any]) -> Dict[str, Any]:
    for k in _NULLABLE_NUMERIC:
        if k in d and (d[k] is None or (isinstance(d[k], float) and np.isnan(d[k]))):
            d[k] = None
    return d


def list_hotspots(
    loader: ArtifactLoader,
    district: Optional[str] = None,
    risk_tier: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    police_station: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "violations",
    sort_order: str = "desc",
) -> Tuple[List[Dict[str, Any]], int]:
    merged, _ = loader.merged_hotspots()
    df = merged.copy()

    if district:
        df = df[df["district"] == district]
    if risk_tier:
        df = df[df["risk_tier"] == risk_tier.upper()]
    if vehicle_type:
        df = df[df["top_vehicle"] == vehicle_type]
    if police_station:
        df = df[df["police_station"] == police_station]
    if search:
        df = df[df["top_junction"].str.contains(search, case=False, na=False)]

    if sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=(sort_order == "asc"), na_position="last")

    total = len(df)
    page = df.iloc[offset: offset + limit]

    items = [_coerce_optional(_row_to_dict(row)) for _, row in page.iterrows()]
    return items, total


def get_hotspot(loader: ArtifactLoader, cluster_id: int) -> Optional[Dict[str, Any]]:
    merged, _ = loader.merged_hotspots()
    match = merged[merged["cluster_id"] == cluster_id]
    if match.empty:
        return None
    return _coerce_optional(_row_to_dict(match.iloc[0]))


def list_nonjunction_hotspots(loader: ArtifactLoader) -> List[Dict[str, Any]]:
    df = loader.read_csv("nonjunction_hotspots", required=False)
    if df is None or df.empty:
        return []
    df = df.replace({np.nan: None})
    return df.to_dict(orient="records")

