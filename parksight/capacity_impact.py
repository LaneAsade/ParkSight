"""
capacity_impact.py — Road capacity impact estimation (IRC:106-2010 / HCM 2000).

Acquires real road geometry from Mappls → OSM → Google → engineering fallback,
then computes Effective Road Capacity Index (ERCI) and capacity loss per hotspot.

All outputs carry data_source, confidence_level, and validation_status.
No causal language — capacity loss is an engineering estimate, not a measured
traffic outcome.
"""

import logging
import math
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests

from .config import ApiKeys, Settings
from .utils import REAL_DATA, MODELED, SPEC_ONLY

log = logging.getLogger(__name__)

# Geometry source tags
GEO_MAPPLS = "MAPPLS_API"
GEO_OSM = "OPENSTREETMAP"
GEO_GOOGLE = "GOOGLE_ROADS_API"
GEO_FALLBACK = "ENGINEERING_ESTIMATE"

_OSM_HIGHWAY_TO_CLASS = {
    "motorway": "arterial_major", "motorway_link": "arterial_major",
    "trunk": "arterial_major", "trunk_link": "arterial_major",
    "primary": "arterial_major", "primary_link": "arterial_major",
    "secondary": "arterial_minor", "secondary_link": "arterial_minor",
    "tertiary": "collector", "tertiary_link": "collector",
    "unclassified": "collector", "residential": "local",
    "living_street": "local", "service": "local",
}


@dataclass
class RoadGeometry:
    cluster_id: str
    road_class: str = "collector"
    lane_count: int = 2
    road_width_m: float = 7.0
    one_way: bool = False
    signal_density: float = 0.0
    intersection_density: float = 0.0
    road_name: Optional[str] = None
    geometry_source: str = GEO_FALLBACK
    validation_status: str = SPEC_ONLY
    confidence_level: str = "LOW"
    lane_count_inferred: bool = True


class _MapplsTokenManager:
    _token: Optional[str] = None
    _expires_at: float = 0.0

    @classmethod
    def get_token(cls) -> Optional[str]:
        if not (ApiKeys.mappls_client_id() and ApiKeys.mappls_client_secret()):
            return ApiKeys.mappls_access_token() or None
        if cls._token and time.time() < cls._expires_at - 60:
            return cls._token
        try:
            resp = requests.post(
                "https://outpost.mapmyindia.com/api/security/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": ApiKeys.mappls_client_id(),
                    "client_secret": ApiKeys.mappls_client_secret(),
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            cls._token = data.get("access_token") or data.get("token")
            cls._expires_at = time.time() + int(data.get("expires_in", 3600))
            return cls._token
        except Exception as exc:
            log.debug("Mappls token refresh failed: %s", exc)
            return None


def _mappls_headers() -> Dict[str, str]:
    token = _MapplsTokenManager.get_token()
    return {"Authorization": f"Bearer {token}"} if token else {}


def _osm_road_class(lat: float, lon: float, radius: int = 50) -> Optional[Dict]:
    query = f"[out:json][timeout:10];way(around:{radius},{lat},{lon})[highway];out tags;"
    try:
        resp = requests.get(
            "https://overpass-api.de/api/interpreter", params={"data": query}, timeout=15
        )
        if resp.status_code != 200:
            return None
        ways = resp.json().get("elements", [])
        if not ways:
            return None
        priority = list(_OSM_HIGHWAY_TO_CLASS.keys())
        best = min(
            ways,
            key=lambda w: priority.index(w.get("tags", {}).get("highway", "service"))
            if w.get("tags", {}).get("highway") in priority else len(priority),
        )
        tags = best.get("tags", {})
        hw = tags.get("highway", "unclassified")
        rc = _OSM_HIGHWAY_TO_CLASS.get(hw, "collector")
        lc_raw = tags.get("lanes")
        lc = int(lc_raw) if lc_raw and str(lc_raw).isdigit() else None
        return {
            "road_name": tags.get("name"),
            "road_class": rc,
            "lane_count": lc,
            "lane_count_inferred": lc is None,
            "one_way": tags.get("oneway", "no").lower() in ("yes", "true", "1"),
        }
    except Exception as exc:
        log.debug("OSM query failed: %s", exc)
        return None


def _infer_road_class_btp(junction_name: str) -> str:
    """BTP junction-naming heuristic → road class estimate."""
    name_low = junction_name.lower()
    major_kw = ["mg road", "outer ring", "hosur road", "bellary road", "nh", "expressway"]
    minor_kw = ["main road", "infantry", "residency", "palace road"]
    local_kw = ["lane", "cross road", "1st cross", "layout"]
    for kw in major_kw:
        if kw in name_low:
            return "arterial_major"
    for kw in minor_kw:
        if kw in name_low:
            return "arterial_minor"
    for kw in local_kw:
        if kw in name_low:
            return "local"
    m = re.match(r"BTP(\d+)", junction_name.upper())
    if m:
        n = int(m.group(1))
        if n < 50: return "arterial_minor"
        if n < 150: return "collector"
        return "local"
    return "collector"


def _default_lane_count(road_class: str) -> int:
    return {"arterial_major": 4, "arterial_minor": 2, "collector": 2, "local": 2}.get(road_class, 2)


def _estimate_road_width(lane_count: int, road_class: str) -> float:
    lane_width = 3.5 if road_class in ("arterial_major", "arterial_minor") else 3.0
    return round(lane_count * lane_width + 1.0, 1)


def _acquire_geometry(cluster_id: str, lat: float, lon: float, junction_name: str) -> RoadGeometry:
    """Try Mappls → OSM → engineering fallback."""
    geo = RoadGeometry(cluster_id=cluster_id)

    # Mappls reverse geocode
    headers = _mappls_headers()
    if headers:
        try:
            resp = requests.get(
                "https://apis.mappls.com/advancedmaps/v1/rev_geocode",
                params={"lat": lat, "lng": lon}, headers=headers, timeout=10,
            )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    r = results[0]
                    geo.road_name = r.get("street") or r.get("road") or r.get("name")
                    geo.geometry_source = GEO_MAPPLS
                    geo.validation_status = REAL_DATA
                    geo.confidence_level = "HIGH"
        except Exception as exc:
            log.debug("Mappls reverse geocode failed: %s", exc)
        time.sleep(0.05)

    # OSM fallback if Mappls didn't provide road class
    if geo.geometry_source == GEO_FALLBACK or geo.road_class == "collector":
        osm = _osm_road_class(lat, lon)
        if osm:
            geo.road_class = osm["road_class"]
            geo.lane_count = osm["lane_count"] or _default_lane_count(osm["road_class"])
            geo.lane_count_inferred = osm["lane_count_inferred"]
            geo.one_way = osm["one_way"]
            geo.road_name = geo.road_name or osm.get("road_name")
            geo.geometry_source = GEO_OSM
            geo.validation_status = REAL_DATA
            geo.confidence_level = "HIGH"
        time.sleep(0.05)

    # Engineering fallback
    if geo.geometry_source == GEO_FALLBACK:
        rc = _infer_road_class_btp(junction_name)
        lc = _default_lane_count(rc)
        geo.road_class = rc
        geo.lane_count = lc
        geo.lane_count_inferred = True
        geo.validation_status = SPEC_ONLY
        geo.confidence_level = "LOW"

    geo.road_width_m = _estimate_road_width(geo.lane_count, geo.road_class)
    return geo


def compute_capacity_impact(clusters_df: pd.DataFrame, settings: Settings, skip_apis: bool = False) -> pd.DataFrame:
    """Main entry point — acquire geometry and compute ERCI for every cluster."""
    cfg = settings.road_capacity
    base_cap = cfg.get("base_capacity_veh_hr_per_dir", {
        "arterial_major": 1800, "arterial_minor": 1600, "collector": 1400, "local": 1000,
    })
    lane_factor = {int(k): v for k, v in cfg.get("lane_factor", {1: 1.0, 2: 1.8, 3: 2.5, 4: 3.1, 5: 3.65, 6: 4.1}).items()}
    max_obs_loss = cfg.get("max_obstruction_loss", {"arterial_major": 0.28, "arterial_minor": 0.33, "collector": 0.38, "local": 0.45})
    vd_sat = cfg.get("vd_saturation", 15.0)
    corridor_km = cfg.get("corridor_length_km", 0.5)
    reporting_days = cfg.get("reporting_days", 141)
    jcl_per_junction = cfg.get("junction_capacity_loss_per_junction", 0.05)
    max_jcl = cfg.get("max_junction_capacity_loss", 0.20)
    junction_radius = cfg.get("junction_search_radius_km", 0.5)

    LAT_KM = 111.0
    LON_KM = 111.32 * math.cos(math.radians(12.98))

    rows = []
    for _, c in clusters_df.iterrows():
        cid = str(c["cluster_id"])
        lat, lon = float(c["lat"]), float(c["lon"])
        violations = int(c["violations"])
        vpd = violations / max(reporting_days, 1)

        if skip_apis:
            geo = RoadGeometry(cluster_id=cid)
            rc = _infer_road_class_btp(str(c.get("top_junction", "")))
            geo.road_class = rc
            geo.lane_count = _default_lane_count(rc)
            geo.lane_count_inferred = True
            geo.road_width_m = _estimate_road_width(geo.lane_count, rc)
        else:
            geo = _acquire_geometry(cid, lat, lon, str(c.get("top_junction", "")))

        # Nearby hotspot density as intersection proxy
        if len(clusters_df) > 1:
            dlat = clusters_df["lat"].values - lat
            dlon = clusters_df["lon"].values - lon
            dist_km = np.sqrt((dlat * LAT_KM) ** 2 + (dlon * LON_KM) ** 2)
            nearby = int(np.sum((dist_km > 0.001) & (dist_km <= junction_radius)))
        else:
            nearby = 0
        inter_density = nearby / max(corridor_km, 0.01)

        lc = geo.lane_count
        rc = geo.road_class
        lf = lane_factor.get(min(max(lc, 1), 6), 4.1)
        lane_km = max(lc, 1) * corridor_km
        vd = vpd / max(lane_km, 0.001)
        max_loss = max_obs_loss.get(rc, 0.35)
        obf = 1.0 - min(vd / vd_sat, 1.0) * max_loss
        n_junctions = inter_density * junction_radius
        jf = 1.0 - min(n_junctions * jcl_per_junction, max_jcl)
        base = float(base_cap.get(rc, 1400))
        base_capacity = base * lf
        eff_capacity = base_capacity * obf * jf
        cap_loss_pct = round((base_capacity - eff_capacity) / base_capacity * 100, 2)
        erci = round(100 - cap_loss_pct, 1)

        if cap_loss_pct < 10:
            cap_tier, cap_desc = "LOW", "0–10%: minor obstruction"
        elif cap_loss_pct < 25:
            cap_tier, cap_desc = "MEDIUM", "10–25%: noticeable obstruction"
        elif cap_loss_pct < 40:
            cap_tier, cap_desc = "HIGH", "25–40%: significant obstruction"
        else:
            cap_tier, cap_desc = "SEVERE", ">40%: near-saturation obstruction"

        rows.append({
            "cluster_id": c["cluster_id"],
            "road_name": geo.road_name or str(c.get("top_junction", "")),
            "road_class": rc,
            "lane_count": lc,
            "lane_count_inferred": geo.lane_count_inferred,
            "road_width_m": geo.road_width_m,
            "violations_per_day": round(vpd, 3),
            "violation_density_per_lane_km": round(vd, 3),
            "obstruction_factor": round(obf, 4),
            "junction_factor": round(jf, 4),
            "lane_factor": round(lf, 3),
            "base_capacity_veh_hr": round(base_capacity, 1),
            "effective_capacity_veh_hr": round(eff_capacity, 1),
            "capacity_loss_pct": cap_loss_pct,
            "erci_index": erci,
            "capacity_loss_tier": cap_tier,
            "capacity_loss_description": cap_desc,
            "risk_score": c.get("risk_score", None),
            "risk_tier": c.get("risk_tier", None),
            "geometry_source": geo.geometry_source,
            "validation_status": geo.validation_status,
            "confidence_level": geo.confidence_level,
            "causal_caveat": (
                "Capacity loss is an engineering estimate (IRC:106-2010 obstruction model). "
                "It is associated with — NOT a proven causal effect of — illegal parking. "
                "Allowed language: 'associated with', 'correlated with'. "
                "Forbidden: 'causes', 'attributable to', 'proves'."
            ),
        })

    out = pd.DataFrame(rows)
    n_real = int((out["validation_status"] == REAL_DATA).sum())
    log.info("Capacity impact: %d clusters | %d with real geometry", len(out), n_real)
    return out
