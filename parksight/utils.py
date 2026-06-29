"""
utils.py — Shared helpers used across pipeline modules.
"""

import math
import re
import logging
from typing import Optional

import pandas as pd

log = logging.getLogger(__name__)

# Validation-status constants — used throughout the pipeline
REAL_DATA = "REAL_DATA"
MODELED = "MODELED"
SPEC_ONLY = "SPEC_ONLY"


def lon_km_per_deg_at_lat(mean_lat_deg: float, fallback: float = 108.5) -> float:
    """True km-per-degree-of-longitude at a given latitude.

    1 degree of longitude spans 111.32 km at the equator and shrinks by
    cos(latitude) towards the poles. Bengaluru at ~13°N gives ~108.5 km/deg,
    not the ~85 km/deg appropriate for 40°N latitudes.

    Falls back to the supplied value (default: Bengaluru ballpark) if
    mean_lat_deg is NaN or None.
    """
    if mean_lat_deg is None or (isinstance(mean_lat_deg, float) and math.isnan(mean_lat_deg)):
        return fallback
    return 111.32 * math.cos(math.radians(mean_lat_deg))


def assign_district(lat: float, lon: float, districts: list) -> str:
    """Map a (lat, lon) point to a synthetic district bucket.

    Districts is a list of [lat_min, lat_max, lon_min, lon_max, name] rows
    loaded from settings.yaml. Returns "Peripheral Bengaluru" when no
    district matches.

    Note: these are synthetic rectangular grid cells for analysis, not real
    administrative boundaries.
    """
    for entry in districts:
        lat_min, lat_max, lon_min, lon_max, name = entry
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return name
    return "Peripheral Bengaluru"


# Month-name → number mapping for filename date parsing
_MONTH_NAMES = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_MONTH_NAME_PATTERN = "|".join(sorted(_MONTH_NAMES.keys(), key=len, reverse=True))


def extract_month_token(token: str) -> Optional[int]:
    """Resolve a filename token to a calendar month (1–12).

    Handles bare month names ('jan'), month+year ('jan2024'), and
    numeric YYYY-MM / MM-YYYY tokens. Returns None for non-month tokens.
    """
    token = token.lower()
    if token in _MONTH_NAMES:
        return _MONTH_NAMES[token]
    m = re.match(rf"^({_MONTH_NAME_PATTERN})(\d{{4}})$", token)
    if m:
        return _MONTH_NAMES[m.group(1)]
    m = re.match(r"^(\d{4})[-_](\d{1,2})$", token)
    if m:
        mm = int(m.group(2))
        return mm if 1 <= mm <= 12 else None
    m = re.match(r"^(\d{1,2})[-_](\d{4})$", token)
    if m:
        mm = int(m.group(1))
        return mm if 1 <= mm <= 12 else None
    return None


def safe_run(stage_name: str, fn, *args, fallback=None, failures: dict = None, **kwargs):
    """Run a pipeline stage with exception isolation.

    On failure: records the error in `failures`, logs a warning, and returns
    `fallback`. The pipeline continues rather than crashing.
    """
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        log.warning("Stage '%s' failed — continuing with fallback. Error: %s", stage_name, msg)
        if failures is not None:
            failures[stage_name] = msg
        return fallback
