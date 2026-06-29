"""
hotspot_detection.py — Junction-level aggregation and DBSCAN clustering.

Produces HotspotCluster objects that carry member row indices (for bootstrap
resampling) and full station breakdowns (for multi-jurisdiction detection).
"""

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score

from .config import Settings
from .utils import REAL_DATA, SPEC_ONLY, assign_district

log = logging.getLogger(__name__)


@dataclass
class HotspotCluster:
    cluster_id: int
    top_junction: str
    police_station: str
    district: str
    violations: int
    n_junctions: int
    pct_at_junction: float
    pct_peak_hour: float
    top_vehicle: str
    peak_hour: int
    lat: float
    lon: float
    risk_score: float = 0.0
    risk_tier: str = "LOW"
    ci_low: float = 0.0
    ci_high: float = 0.0
    station_breakdown: Dict[str, float] = field(default_factory=dict)
    multi_jurisdiction: bool = False
    member_row_indices: np.ndarray = field(default_factory=lambda: np.array([], dtype=int))


def build_junction_aggregates(approved: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    """Aggregate violations to junction level and compute km-space coordinates."""
    lon_km_per_deg = _get_lon_km(approved, settings)
    jn = approved[approved["at_junction"] == 1].copy()
    if jn.empty:
        return pd.DataFrame()

    grp = (
        jn.groupby("junction_name")
        .agg(
            violations=("id", "count"),
            at_junction_pct=("at_junction", "mean"),
            is_peak_pct=("is_peak", "mean"),
            lat=("latitude", "mean"),
            lon=("longitude", "mean"),
            police_station=("police_station", lambda x: x.mode().iloc[0]),
            top_vehicle=("vehicle_type", lambda x: x.mode().iloc[0]),
            peak_hour=("hour", lambda x: x.mode().iloc[0]),
        )
        .reset_index()
    )
    grp = grp[grp["violations"] >= settings.min_junction_violations].copy()
    grp["district"] = grp.apply(
        lambda r: assign_district(r["lat"], r["lon"], settings.districts), axis=1
    )
    grp["lat_km"] = grp["lat"] * settings.lat_km_per_deg
    grp["lon_km"] = grp["lon"] * lon_km_per_deg

    # Attach per-junction row indices and station counts for downstream use
    surviving = set(grp["junction_name"])
    idx_by_jn: Dict[str, np.ndarray] = {}
    stations_by_jn: Dict[str, Dict] = {}
    jn_reset = jn.reset_index(drop=False)
    for jname, sub in jn_reset[jn_reset["junction_name"].isin(surviving)].groupby("junction_name"):
        idx_by_jn[jname] = sub["index"].to_numpy()
        stations_by_jn[jname] = sub["police_station"].value_counts().to_dict()
    grp["_row_indices"] = grp["junction_name"].map(idx_by_jn)
    grp["_station_counts"] = grp["junction_name"].map(stations_by_jn)

    log.info("Qualifying junctions (≥%d violations): %d", settings.min_junction_violations, len(grp))
    return grp


def run_dbscan(junctions: pd.DataFrame, settings: Settings) -> Tuple[pd.DataFrame, np.ndarray, Dict]:
    """Cluster junction centroids with DBSCAN and compute bootstrap CI on cluster count."""
    lon_km_per_deg = _get_lon_km_from_junctions(junctions, settings)

    if junctions.empty:
        meta = {
            "validation_status": SPEC_ONLY,
            "skipped": True,
            "reason": (
                f"No junction has ≥{settings.min_junction_violations} approved violations. "
                "This can happen on short time windows or small jurisdictions."
            ),
            "n_clusters": 0,
        }
        log.warning(meta["reason"])
        return junctions.assign(_cluster=pd.Series(dtype=int)), np.array([], dtype=int), meta

    coords = junctions[["lat_km", "lon_km"]].values
    labels = DBSCAN(
        eps=settings.dbscan_eps_km, min_samples=settings.dbscan_min_samples, n_jobs=-1
    ).fit_predict(coords)
    n_clusters = int(np.sum(np.unique(labels) != -1))
    mask = labels != -1
    sil = (
        float(silhouette_score(coords[mask], labels[mask]))
        if n_clusters >= 2 and mask.sum() >= 2 * n_clusters
        else -1.0
    )

    jitter_std = settings.get("dbscan", "jitter_std_km", default=0.03)
    jitter_trials = settings.get("dbscan", "jitter_trials", default=15)
    boot_counts = []
    for seed in range(jitter_trials):
        rng = np.random.RandomState(seed)
        jittered = coords + rng.normal(0, jitter_std, coords.shape)
        lbl = DBSCAN(eps=settings.dbscan_eps_km, min_samples=settings.dbscan_min_samples).fit_predict(jittered)
        boot_counts.append(int(np.sum(np.unique(lbl) != -1)))
    ci_lo, ci_hi = np.percentile(boot_counts, [5, 95])

    meta = {
        "validation_status": REAL_DATA,
        "n_clusters": n_clusters,
        "silhouette": round(sil, 4),
        "n_clusters_ci_90pct": [round(float(ci_lo), 1), round(float(ci_hi), 1)],
        "lon_km_per_deg_used": round(lon_km_per_deg, 3),
    }
    log.info(
        "DBSCAN: %d clusters | silhouette=%.4f | 90%% CI on count: [%.0f, %.0f]",
        n_clusters, sil, ci_lo, ci_hi,
    )
    return junctions.assign(_cluster=labels), labels, meta


def build_hotspot_clusters(junctions: pd.DataFrame, labels: np.ndarray, settings: Settings) -> List[HotspotCluster]:
    """Build HotspotCluster objects from DBSCAN-labelled junction data."""
    if junctions.empty or len(labels) == 0:
        return []

    share_threshold = settings.get("jurisdiction", "share_threshold", default=0.10)
    vehicle_weights = settings.vehicle_weights

    junctions = junctions.copy()
    junctions["_cluster"] = labels
    clusters = []

    for cid in sorted(junctions["_cluster"].unique()):
        if cid == -1:
            continue
        g = junctions[junctions["_cluster"] == cid]
        wt = g["violations"].values
        clat = float(np.average(g["lat"], weights=wt))
        clon = float(np.average(g["lon"], weights=wt))
        top_row = g.loc[g["violations"].idxmax()]

        merged: Counter = Counter()
        for sc in g["_station_counts"]:
            if isinstance(sc, dict):
                merged.update(sc)
        total = sum(merged.values()) or 1
        station_breakdown = {st: round(n / total, 4) for st, n in merged.most_common()}
        top_station = next(iter(station_breakdown), str(top_row["police_station"]))
        runner_up_share = list(station_breakdown.values())[1] if len(station_breakdown) > 1 else 0.0

        member_idx_parts = [ri for ri in g["_row_indices"] if isinstance(ri, np.ndarray)]
        member_row_indices = np.concatenate(member_idx_parts) if member_idx_parts else np.array([], dtype=int)

        clusters.append(HotspotCluster(
            cluster_id=int(cid),
            top_junction=str(top_row["junction_name"]),
            police_station=top_station,
            district=assign_district(clat, clon, settings.districts),
            violations=int(g["violations"].sum()),
            n_junctions=int(len(g)),
            pct_at_junction=round(float(np.average(g["at_junction_pct"], weights=wt)) * 100, 1),
            pct_peak_hour=round(float(np.average(g["is_peak_pct"], weights=wt)) * 100, 1),
            top_vehicle=str(top_row["top_vehicle"]),
            peak_hour=int(top_row["peak_hour"]),
            lat=round(clat, 5),
            lon=round(clon, 5),
            station_breakdown=station_breakdown,
            multi_jurisdiction=runner_up_share >= share_threshold,
            member_row_indices=member_row_indices,
        ))

    clusters.sort(key=lambda c: -c.violations)
    n_multi = sum(1 for c in clusters if c.multi_jurisdiction)
    log.info("Built %d hotspot clusters (%d multi-jurisdiction)", len(clusters), n_multi)
    return clusters


def _get_lon_km(approved: pd.DataFrame, settings: Settings) -> float:
    from .utils import lon_km_per_deg_at_lat
    mean_lat = float(approved["latitude"].mean()) if len(approved) else float("nan")
    return lon_km_per_deg_at_lat(mean_lat, settings.lon_km_per_deg_fallback)


def _get_lon_km_from_junctions(junctions: pd.DataFrame, settings: Settings) -> float:
    from .utils import lon_km_per_deg_at_lat
    if junctions.empty:
        return settings.lon_km_per_deg_fallback
    mean_lat = float(junctions["lat"].mean())
    return lon_km_per_deg_at_lat(mean_lat, settings.lon_km_per_deg_fallback)
