# backend/app/services/event_simulator.py
"""
Event-Aware Intelligence — predict parking demand and congestion
spillover from major events (concerts, sports, festivals).
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import math


# km radius within which nearby hotspots get an uplift
_SPILLOVER_RADIUS_KM = 3.0
# Parking demand factor: what fraction of attendees arrive by car
_CAR_FRACTION = 0.45
# Avg occupants per car
_AVG_OCCUPANTS = 2.5


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def simulate_event(
    event_name: str,
    venue_name: str,
    venue_lat: float,
    venue_lon: float,
    attendance: int,
    venue_capacity: int,
    hotspots: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Returns event impact analysis including spillover zones and patrol recommendation.
    """
    # Expected cars
    expected_cars = int(attendance * _CAR_FRACTION / _AVG_OCCUPANTS)
    overflow = max(0, expected_cars - venue_capacity)

    # Identify nearby hotspots as spillover zones
    spillover_zones = []
    for h in hotspots:
        lat, lon = h.get("lat"), h.get("lon")
        if lat is None or lon is None:
            continue
        dist = _haversine(venue_lat, venue_lon, lat, lon)
        if dist <= _SPILLOVER_RADIUS_KM:
            uplift = max(0, 1 - dist / _SPILLOVER_RADIUS_KM)  # 0–1
            extra_cap_loss = round(uplift * 25, 1)  # up to 25% extra capacity loss
            spillover_zones.append({
                "cluster_id": h["cluster_id"],
                "top_junction": h.get("top_junction"),
                "distance_km": round(dist, 2),
                "spillover_uplift": round(uplift * 100, 1),
                "expected_extra_capacity_loss_pct": extra_cap_loss,
                "lat": lat,
                "lon": lon,
            })

    spillover_zones.sort(key=lambda z: z["distance_km"])

    # Expected capacity loss for venue zone
    capacity_fill = attendance / max(venue_capacity, 1)
    expected_capacity_loss = round(min(capacity_fill * 30, 40), 1)

    # Risk classification
    if expected_capacity_loss >= 25 or len(spillover_zones) >= 5:
        risk = "HIGH"
    elif expected_capacity_loss >= 15 or len(spillover_zones) >= 3:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    # Patrol recommendation
    patrol_teams = max(2, math.ceil(len(spillover_zones) * 0.8))

    return {
        "event_name": event_name,
        "venue_name": venue_name,
        "venue_lat": venue_lat,
        "venue_lon": venue_lon,
        "attendance": attendance,
        "venue_capacity": venue_capacity,
        "expected_cars": expected_cars,
        "overflow_vehicles": overflow,
        "expected_capacity_loss_pct": expected_capacity_loss,
        "congestion_risk": risk,
        "spillover_zones": spillover_zones,
        "spillover_zone_count": len(spillover_zones),
        "recommended_patrol_teams": patrol_teams,
        "economic_impact_est_inr": int(expected_capacity_loss * 8000),  # modelled
        "validation_status": "MODELED",
        "disclaimer": "All outputs are modelled projections, not measured outcomes.",
    }