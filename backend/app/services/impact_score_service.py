# backend/app/services/impact_score_service.py
"""
Impact Score — replaces violation-focused risk_score with a 6-factor
traffic-improvement score (0–100).

Formula weights (PRD spec):
  Violation Volume      30%
  Congestion Severity   25%
  Capacity Loss         20%
  Peak Hour Density     10%
  Road Importance       10%
  Vehicle Severity       5%
"""

from __future__ import annotations
from typing import Any, Dict, List
import numpy as np
import pandas as pd
from .artifact_loader import ArtifactLoader


_VEHICLE_SEVERITY = {
    "TRUCK": 1.0,
    "BUS": 1.0,
    "MAXI-CAB": 0.8,
    "AUTO": 0.5,
    "BIKE": 0.3,
    "CAR": 0.4,
}

_ROAD_CLASS_IMPORTANCE = {
    "motorway": 1.0, "trunk": 0.9, "primary": 0.8,
    "secondary": 0.6, "tertiary": 0.4, "residential": 0.2,
}


def _pct_rank(series: pd.Series) -> pd.Series:
    """Percentile rank 0-1, NaN → 0."""
    return series.rank(pct=True).fillna(0)


def compute_impact_scores(loader: ArtifactLoader) -> List[Dict[str, Any]]:
    merged, _ = loader.merged_hotspots()
    if merged.empty:
        return []

    # ── Factor 1: Violation Volume (30%) ────────────────────────────────────
    f_volume = _pct_rank(merged.get("violations", pd.Series(0, index=merged.index)))

    # ── Factor 2: Congestion Severity (25%) ─────────────────────────────────
    cong = merged.get("congestion_index", pd.Series(np.nan, index=merged.index))
    f_congestion = _pct_rank(cong.fillna(0))

    # ── Factor 3: Capacity Loss (20%) ───────────────────────────────────────
    cap = merged.get("capacity_loss_pct", pd.Series(np.nan, index=merged.index))
    f_capacity = _pct_rank(cap.fillna(0))

    # ── Factor 4: Peak Hour Density (10%) ───────────────────────────────────
    peak = merged.get("pct_peak_hour", pd.Series(np.nan, index=merged.index))
    f_peak = _pct_rank(peak.fillna(0))

    # ── Factor 5: Road Importance (10%) ─────────────────────────────────────
    road = merged.get("road_class", pd.Series("tertiary", index=merged.index))
    road_score = road.map(lambda r: _ROAD_CLASS_IMPORTANCE.get(str(r).lower(), 0.3))
    f_road = _pct_rank(road_score)

    # ── Factor 6: Vehicle Severity (5%) ─────────────────────────────────────
    veh = merged.get("top_vehicle", pd.Series("CAR", index=merged.index))
    veh_score = veh.map(lambda v: _VEHICLE_SEVERITY.get(str(v).upper(), 0.3))
    f_vehicle = _pct_rank(veh_score)

    # ── Weighted composite ───────────────────────────────────────────────────
    impact_raw = (
        0.30 * f_volume +
        0.25 * f_congestion +
        0.20 * f_capacity +
        0.10 * f_peak +
        0.10 * f_road +
        0.05 * f_vehicle
    )
    impact_score = (impact_raw * 100).round(1)

    def priority(score: float) -> str:
        if score >= 75: return "CRITICAL"
        if score >= 50: return "HIGH"
        if score >= 25: return "MEDIUM"
        return "LOW"

    results = []
    for i, row in merged.iterrows():
        score = float(impact_score.loc[i])
        results.append({
            "cluster_id": int(row["cluster_id"]),
            "top_junction": row.get("top_junction"),
            "district": row.get("district"),
            "impact_score": score,
            "priority": priority(score),
            "factors": {
                "violation_volume": round(float(f_volume.loc[i]) * 100, 1),
                "congestion_severity": round(float(f_congestion.loc[i]) * 100, 1),
                "capacity_loss": round(float(f_capacity.loc[i]) * 100, 1),
                "peak_hour_density": round(float(f_peak.loc[i]) * 100, 1),
                "road_importance": round(float(f_road.loc[i]) * 100, 1),
                "vehicle_severity": round(float(f_vehicle.loc[i]) * 100, 1),
            },
            "congestion_index": row.get("congestion_index"),
            "capacity_loss_pct": row.get("capacity_loss_pct"),
            "violations": int(row.get("violations", 0)),
            "lat": row.get("lat"),
            "lon": row.get("lon"),
        })

    results.sort(key=lambda r: r["impact_score"], reverse=True)
    return results