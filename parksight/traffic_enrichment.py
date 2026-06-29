"""
traffic_enrichment.py — Traffic congestion probing via Google Distance Matrix API.

Probes each hotspot in 8 compass directions at the current time (route
robustness) and across 4 time-of-day slots × 2 day types (temporal grid).

Every call returns an explicit validation_status label. Failed API calls are
recorded as SPEC_ONLY — congestion values are never fabricated on failure.
"""

import hashlib
import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from .config import ApiKeys, Settings
from .utils import REAL_DATA, SPEC_ONLY

log = logging.getLogger(__name__)

_DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
_SQRT2_2 = 0.7071067811865476

PROBE_DIRECTIONS = {
    "N": (1, 0), "S": (-1, 0), "E": (0, 1), "W": (0, -1),
    "NE": (_SQRT2_2, _SQRT2_2), "NW": (_SQRT2_2, -_SQRT2_2),
    "SE": (-_SQRT2_2, _SQRT2_2), "SW": (-_SQRT2_2, -_SQRT2_2),
}

IST_UTC_OFFSET_HOURS = 5.5


@dataclass
class ProbeResult:
    ok: bool
    source: str
    congestion_index: Optional[float] = None
    delay_minutes: Optional[float] = None
    avg_speed_kmh: Optional[float] = None
    error: Optional[str] = None


class _Cache:
    def __init__(self, path: Path, ttl_s: int = 21600) -> None:
        self._conn = sqlite3.connect(str(path))
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, payload TEXT, ts REAL)"
        )
        self._conn.commit()
        self._ttl_s = ttl_s

    def _key(self, params: Dict) -> str:
        return hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()

    def get(self, params: Dict) -> Optional[Dict]:
        row = self._conn.execute(
            "SELECT payload, ts FROM cache WHERE key=?", (self._key(params),)
        ).fetchone()
        if not row:
            return None
        payload, ts = row
        if time.time() - ts > self._ttl_s:
            return None
        return json.loads(payload)

    def set(self, params: Dict, payload: Dict) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO cache (key, payload, ts) VALUES (?, ?, ?)",
            (self._key(params), json.dumps(payload), time.time()),
        )
        self._conn.commit()


class TrafficClient:
    """Thin Google Distance Matrix client with caching, retry, and fail-closed semantics."""

    def __init__(self, api_key: str, cache_path: Optional[Path] = None, settings: Optional[Settings] = None) -> None:
        self._api_key = api_key
        self._has_key = bool(api_key)
        cfg = settings.traffic if settings else {}
        self._timeout = cfg.get("request_timeout_seconds", 10)
        self._max_retries = cfg.get("max_retries", 3)
        self._backoff = cfg.get("retry_backoff_seconds", 1.5)
        ttl = cfg.get("cache_ttl_seconds", 21600)
        self._cache = _Cache(cache_path or Path("google_traffic_cache.sqlite"), ttl_s=ttl)
        self._session = requests.Session()
        if not self._has_key:
            log.warning("No GOOGLE_MAPS_API_KEY — all traffic probes will be SPEC_ONLY")

    def probe(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        departure_time: Optional[int] = None,
    ) -> ProbeResult:
        """Single Distance Matrix probe. Returns SPEC_ONLY if key is absent or call fails."""
        if not self._has_key:
            return ProbeResult(ok=False, source=SPEC_ONLY, error="No API key")

        params = {
            "origins": f"{origin[0]},{origin[1]}",
            "destinations": f"{destination[0]},{destination[1]}",
            "mode": "driving",
            "units": "metric",
            "departure_time": str(int(departure_time)) if departure_time else "now",
            "traffic_model": "best_guess",
        }

        cached = self._cache.get(params)
        if cached:
            return self._parse_response(cached, source="CACHE")

        last_err = None
        for attempt in range(1, self._max_retries + 1):
            try:
                resp = self._session.get(
                    _DISTANCE_MATRIX_URL,
                    params={**params, "key": self._api_key},
                    timeout=self._timeout,
                )
                resp.raise_for_status()
                payload = resp.json()
                if payload.get("status") == "OK":
                    self._cache.set(params, payload)
                    return self._parse_response(payload, source=REAL_DATA)
                last_err = f"{payload.get('status')}: {payload.get('error_message', '')}"
                if payload.get("status") not in ("OVER_QUERY_LIMIT", "UNKNOWN_ERROR"):
                    break
            except Exception as exc:
                last_err = f"{type(exc).__name__}: {exc}"
            time.sleep(self._backoff * attempt)

        return ProbeResult(ok=False, source=SPEC_ONLY, error=last_err)

    @staticmethod
    def _parse_response(payload: Dict, source: str) -> ProbeResult:
        try:
            el = payload["rows"][0]["elements"][0]
            if el.get("status") != "OK":
                return ProbeResult(ok=False, source=SPEC_ONLY, error=f"Element: {el.get('status')}")
            dur_t = float(el.get("duration_in_traffic", el["duration"])["value"])
            dur_f = float(el["duration"]["value"])
            dist = float(el["distance"]["value"])
            cong = dur_t / dur_f if dur_f > 0 else None
            delay = (dur_t - dur_f) / 60.0 if dur_f > 0 else None
            speed = (dist / 1000.0) / (dur_t / 3600.0) if dur_t > 0 else None
            return ProbeResult(ok=True, source=source, congestion_index=cong, delay_minutes=delay, avg_speed_kmh=speed)
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            return ProbeResult(ok=False, source=SPEC_ONLY, error=str(exc))


def _next_future_utc(hour_ist: int, weekdays: List[int]) -> datetime:
    """Find the next UTC timestamp when it will be `hour_ist` IST on a `weekdays` day."""
    now_utc = datetime.now(timezone.utc)
    ist_now = now_utc + timedelta(hours=IST_UTC_OFFSET_HOURS)
    candidate = ist_now.replace(hour=hour_ist, minute=0, second=0, microsecond=0)
    for _ in range(8):
        if candidate.weekday() in weekdays and candidate > ist_now:
            return candidate - timedelta(hours=IST_UTC_OFFSET_HOURS)
        candidate += timedelta(days=1)
    return candidate - timedelta(hours=IST_UTC_OFFSET_HOURS)


def enrich_with_traffic(clusters_df, settings: Settings, skip: bool = False):
    """Probe all hotspot clusters directionally and produce traffic_enrichment.csv rows."""
    import pandas as pd

    if skip:
        log.info("Traffic enrichment skipped (--skip-traffic)")
        return pd.DataFrame()

    api_key = ApiKeys.google_maps()
    if not api_key:
        log.warning("No GOOGLE_MAPS_API_KEY — traffic enrichment will produce SPEC_ONLY rows")

    cfg = settings.traffic
    probe_offset = cfg.get("probe_offset_deg", 0.01)
    n_dirs = cfg.get("n_directions", 8)
    min_dirs_real = cfg.get("min_directions_for_real_label", 2)
    client = TrafficClient(api_key=api_key, settings=settings)
    direction_items = list(PROBE_DIRECTIONS.items())[:n_dirs]

    rows = []
    for _, c in clusters_df.iterrows():
        lat, lon = float(c["lat"]), float(c["lon"])
        cong_vals, speed_vals, delay_vals = [], [], []
        n_ok = 0

        for dname, (dlat, dlon) in direction_items:
            origin = (lat, lon)
            dest = (lat + dlat * probe_offset, lon + dlon * probe_offset)
            result = client.probe(origin, dest)
            time.sleep(0.05)
            if result.ok:
                n_ok += 1
                if result.congestion_index is not None:
                    cong_vals.append(result.congestion_index)
                if result.avg_speed_kmh is not None:
                    speed_vals.append(result.avg_speed_kmh)
                if result.delay_minutes is not None:
                    delay_vals.append(result.delay_minutes)

        import numpy as np
        status = REAL_DATA if n_ok >= min_dirs_real else (SPEC_ONLY if n_ok == 0 else "PARTIAL")
        rows.append({
            "cluster_id": c["cluster_id"],
            "n_directions_attempted": len(direction_items),
            "n_directions_succeeded": n_ok,
            "mean_congestion_index": round(float(np.mean(cong_vals)), 4) if cong_vals else None,
            "mean_avg_speed_kmh": round(float(np.mean(speed_vals)), 2) if speed_vals else None,
            "mean_delay_minutes": round(float(np.mean(delay_vals)), 2) if delay_vals else None,
            "validation_status": status,
        })
        log.debug("Cluster %s: n_ok=%d, cong=%.3f", c["cluster_id"], n_ok,
                  float(np.mean(cong_vals)) if cong_vals else float("nan"))

    return pd.DataFrame(rows)
