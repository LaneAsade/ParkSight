"""
nonjunction_hotspots.py — Hex-grid detection for mid-block (non-junction) violations.

Uses a simple 0.005° lat/lon grid (~550 m cells at Bengaluru's latitude)
to surface concentrations of violations not associated with any named junction.
"""

import logging

import pandas as pd

from .config import Settings
from .utils import assign_district

log = logging.getLogger(__name__)

_CELL_DEG = 0.005   # ~550 m cells at ~13°N


def build_nonjunction_hotspots(approved: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    """Return hex-grid cells with at least min_nonjunction_violations mid-block violations."""
    no_jn = approved[approved["at_junction"] == 0].copy()
    if no_jn.empty:
        log.info("Non-junction hotspot cells: 0")
        return pd.DataFrame(columns=["hex_id", "violations", "lat", "lon", "police_station", "district"])

    no_jn["hex_id"] = (
        (no_jn["latitude"] / _CELL_DEG).astype(int).astype(str)
        + "_"
        + (no_jn["longitude"] / _CELL_DEG).astype(int).astype(str)
    )
    grp = (
        no_jn.groupby("hex_id")
        .agg(
            violations=("id", "count"),
            lat=("latitude", "mean"),
            lon=("longitude", "mean"),
            police_station=("police_station", lambda x: x.mode().iloc[0]),
        )
        .reset_index()
    )
    grp = grp[grp["violations"] >= settings.min_nonjunction_violations].copy()
    grp["district"] = grp.apply(
        lambda r: assign_district(r["lat"], r["lon"], settings.districts), axis=1
    )
    log.info(
        "Non-junction hotspot cells (≥%d violations): %d",
        settings.min_nonjunction_violations, len(grp),
    )
    return grp.sort_values("violations", ascending=False).reset_index(drop=True)
