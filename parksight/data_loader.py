"""
data_loader.py — Load the violations CSV, apply IST correction, and run
the temporal audit (date-range consistency, adjudication backlog detection).
"""

import math
import re
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from .config import Settings
from .utils import (
    REAL_DATA, SPEC_ONLY, lon_km_per_deg_at_lat,
    assign_district, extract_month_token,
)

log = logging.getLogger(__name__)


def load_and_validate(
    path: str,
    settings: Settings,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """Load the violations CSV, apply IST correction, and produce a temporal audit.

    Returns:
        approved    — filtered DataFrame of approved violations with derived columns
        raw_df      — full raw DataFrame (all statuses)
        audit       — dict written to temporal_audit.json
    """
    log.info("Loading data from %s", path)
    df = pd.read_csv(path, low_memory=False)

    ist_offset = pd.Timedelta(hours=settings.ist_offset_hours)
    df["created_datetime_utc"] = pd.to_datetime(
        df["created_datetime"], format="mixed", utc=True, errors="coerce"
    )
    df["created_datetime_ist"] = df["created_datetime_utc"] + ist_offset
    df["hour"] = df["created_datetime_ist"].dt.hour
    df["dow"] = df["created_datetime_ist"].dt.dayofweek
    df["year_month"] = df["created_datetime_ist"].dt.to_period("M").astype(str)

    approved = (
        df[df["validation_status"] == "approved"]
        .dropna(subset=["latitude", "longitude"])
        .copy()
    )
    approved["at_junction"] = (
        approved["junction_name"].fillna("").str.strip().str.upper() != "NO JUNCTION"
    ).astype(int)
    approved["is_peak"] = approved["hour"].isin(settings.peak_hours_ist).astype(int)
    approved["vehicle_risk"] = (
        approved["vehicle_type"].map(settings.vehicle_weights).fillna(0.40)
    )
    approved["district"] = approved.apply(
        lambda r: assign_district(r["latitude"], r["longitude"], settings.districts), axis=1
    )

    raw_monthly = df.groupby("year_month").size().to_dict()
    approved_monthly = approved.groupby("year_month").size().to_dict()

    df["_is_adjudicated"] = df["validation_status"].isin(["approved", "rejected"]).astype(int)
    adj_rate = df.groupby("year_month")["_is_adjudicated"].mean().to_dict()
    median_adj_rate = float(np.median(list(adj_rate.values()))) if adj_rate else 0.0
    backlog_months = {
        m: round(r, 3)
        for m, r in adj_rate.items()
        if median_adj_rate > 0 and r < 0.5 * median_adj_rate
    }

    mean_lat = float(approved["latitude"].mean()) if len(approved) else float("nan")
    lon_km_per_deg = lon_km_per_deg_at_lat(mean_lat, settings.lon_km_per_deg_fallback)

    audit: Dict = {
        "n_total_rows": len(df),
        "n_approved": len(approved),
        "approved_pct": round(len(approved) / len(df) * 100, 1) if len(df) else 0.0,
        "n_distinct_police_stations": int(approved["police_station"].nunique()),
        "n_distinct_junctions": int(approved["junction_name"].nunique()),
        "raw_monthly_counts": raw_monthly,
        "approved_monthly_counts": approved_monthly,
        "adjudication_rate_by_month": {m: round(r, 3) for m, r in adj_rate.items()},
        "median_adjudication_rate": round(median_adj_rate, 3),
        "review_backlog_months": backlog_months,
        "validation_backlog_warning": (
            f"Month(s) {list(backlog_months.keys())} have an adjudication rate far below "
            f"the typical month ({median_adj_rate:.0%} median). This is a review-backlog "
            "artifact of the export snapshot date, not a real drop in violations. "
            "Exclude these months from trend analysis."
        ) if backlog_months else None,
        "date_range_actual_ist": (
            [str(approved["created_datetime_ist"].min()),
             str(approved["created_datetime_ist"].max())]
            if len(approved) else None
        ),
        "mean_latitude_deg": round(mean_lat, 5) if not math.isnan(mean_lat) else None,
        "lon_km_per_deg_used": round(lon_km_per_deg, 3),
        "lon_km_per_deg_note": (
            f"Derived as 111.32*cos(mean_lat) = {lon_km_per_deg:.3f} km/degree "
            f"from this dataset's mean latitude ({mean_lat:.4f}°). "
            "Not a hardcoded 40°N constant."
        ) if not math.isnan(mean_lat) else None,
        "district_note": (
            "Districts are synthetic rectangular lat/lon grid cells for analysis — "
            "NOT real Bengaluru police-zone or ward boundaries."
        ),
        "peak_hour_note": (
            "PEAK_HOURS_IST corresponds to ~07:30-17:30 IST (daytime/business hours). "
            "NOT a traffic-engineering peak-hour definition; excludes evening commute."
        ),
    }

    filename_warning = _check_filename_date_consistency(
        path, approved, settings.get("temporal", "min_rows_per_month_for_date_check", default=5)
    )
    if filename_warning:
        audit["filename_date_mismatch_warning"] = filename_warning

    log.info(
        "Approved: %d / %d (%.1f%%) | Stations: %d | Junctions: %d | lon_km_per_deg=%.3f",
        len(approved), len(df), audit["approved_pct"],
        audit["n_distinct_police_stations"], audit["n_distinct_junctions"], lon_km_per_deg,
    )
    if audit.get("validation_backlog_warning"):
        log.warning(audit["validation_backlog_warning"])
    if audit.get("filename_date_mismatch_warning"):
        log.warning(audit["filename_date_mismatch_warning"])

    return approved, df, audit


def _check_filename_date_consistency(
    path: str,
    approved: pd.DataFrame,
    min_rows_per_month: int,
) -> Optional[str]:
    """Guard against a filename implying a date range that doesn't match timestamps.

    Uses year-aware start/end-month comparison (not the old year-blind overlap
    fraction that failed silently on the source file).
    """
    if approved.empty:
        return None
    name = Path(path).stem.lower()
    m = re.search(r"([a-z0-9]+)_to_([a-z0-9]+)", name)
    if not m:
        return None
    start_tok, end_tok = m.group(1), m.group(2)
    start_month = extract_month_token(start_tok)
    end_month = extract_month_token(end_tok)
    if start_month is None or end_month is None:
        return None

    dt = approved["created_datetime_ist"].dropna()
    if dt.empty:
        return None

    ym_counts = dt.dt.to_period("M").value_counts()
    ym_counts = ym_counts[ym_counts >= min_rows_per_month]
    if ym_counts.empty:
        return None

    actual_periods = sorted(ym_counts.index)
    actual_start, actual_end = actual_periods[0], actual_periods[-1]
    actual_span = (
        (actual_end.year - actual_start.year) * 12
        + (actual_end.month - actual_start.month) + 1
    )
    expected_span = (end_month - start_month) % 12 + 1

    if actual_start.month != start_month or actual_end.month != end_month or actual_span != expected_span:
        return (
            f"Filename implies '{start_tok}-to-{end_tok}' "
            f"({expected_span} month(s), month {start_month}–{end_month}), but "
            f"actual timestamps span {actual_start} to {actual_end} "
            f"({actual_span} month(s), month {actual_start.month}–{actual_end.month}; "
            f"full range {dt.min():%Y-%m-%d} to {dt.max():%Y-%m-%d}). "
            "Confirm the intended reporting period before using month-based findings externally."
        )
    return None
