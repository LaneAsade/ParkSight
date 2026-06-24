"""
patrol_service.py — Patrol plan retrieval and simulation.
"""
from __future__ import annotations
from typing import Any, Dict, List
import sys
from pathlib import Path
import pandas as pd
from .artifact_loader import ArtifactLoader
from ..config import app_config

# Make the pipeline importable from the backend
_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def current_patrol(loader: ArtifactLoader, n_teams: int) -> Dict[str, Any]:
    plan = loader.read_csv("patrol_plan", required=False)
    merged, _ = loader.merged_hotspots()
    n_clusters = len(merged)
    n_critical = int((merged["risk_tier"] == "CRITICAL").sum()) if "risk_tier" in merged.columns else 0

    if plan is None or plan.empty:
        return {
            "validation_status": "SPEC_ONLY",
            "n_teams_requested": n_teams,
            "n_assignments": 0,
            "critical_covered": 0,
            "critical_total": n_critical,
            "overall_coverage_pct": 0.0,
            "assignments": [],
            "skipped_reason": "No patrol_plan artifact found — run the pipeline first.",
        }

    covered_ids = set(plan["cluster_id"].unique()) if "cluster_id" in plan.columns else set()
    covered_crit = int((merged[merged["cluster_id"].isin(covered_ids)]["risk_tier"] == "CRITICAL").sum()) \
        if "risk_tier" in merged.columns else 0
    coverage_pct = round(len(covered_ids) / max(n_clusters, 1) * 100, 1)

    return {
        "validation_status": "REAL_DATA",
        "n_teams_requested": n_teams,
        "n_assignments": int(len(plan)),
        "critical_covered": covered_crit,
        "critical_total": n_critical,
        "overall_coverage_pct": coverage_pct,
        "distinct_hotspots_covered": len(covered_ids),
        "distinct_hotspots_total": n_clusters,
        "assignments": plan.replace({float("nan"): None}).to_dict(orient="records"),
    }


def simulate_patrol(loader: ArtifactLoader, merged: pd.DataFrame, n_teams: int) -> Dict[str, Any]:
    """Re-run MILP in memory for scenario simulation."""
    try:
        from parksight.patrol_optimization import milp_assignment
        from parksight.config import Settings
        settings = Settings(config_path=app_config.settings_path)
    except Exception:
        # Fallback: scale linearly from current plan
        plan = loader.read_csv("patrol_plan", required=False)
        n_clusters = len(merged)
        n_critical = int((merged["risk_tier"] == "CRITICAL").sum()) if "risk_tier" in merged.columns else 0
        if plan is None or plan.empty:
            return {"validation_status": "SPEC_ONLY", "critical_covered": 0,
                    "critical_total": n_critical, "overall_coverage_pct": 0.0}
        base = len(plan["cluster_id"].unique()) if "cluster_id" in plan.columns else 0
        scaled = min(n_clusters, max(base, round(base * n_teams / max(app_config.default_patrol_teams, 1))))
        return {
            "validation_status": "MODELED",
            "critical_covered": min(n_critical, n_teams),
            "critical_total": n_critical,
            "overall_coverage_pct": round(scaled / max(n_clusters, 1) * 100, 1),
        }

    from parksight.hotspot_detection import HotspotCluster
    import numpy as np
    clusters = []
    for _, row in merged.iterrows():
        c = HotspotCluster(
            cluster_id=int(row["cluster_id"]),
            top_junction=str(row.get("top_junction", "")),
            police_station=str(row.get("police_station", "")),
            district=str(row.get("district", "")),
            violations=int(row.get("violations", 0)),
            n_junctions=int(row.get("n_junctions", 1)),
            pct_at_junction=float(row.get("pct_at_junction", 100)),
            pct_peak_hour=float(row.get("pct_peak_hour", 50)),
            top_vehicle=str(row.get("top_vehicle", "CAR")),
            peak_hour=int(row.get("peak_hour", 9)),
            lat=float(row.get("lat", 12.97)),
            lon=float(row.get("lon", 77.59)),
        )
        c.risk_score = float(row.get("risk_score", 50))
        c.risk_tier = str(row.get("risk_tier", "MEDIUM"))
        clusters.append(c)

    result = milp_assignment(clusters, n_teams, settings)
    n_clusters = len(clusters)
    covered = len(set(a["cluster_id"] for a in result.get("assignments", [])))
    return {
        "validation_status": "MODELED",
        "critical_covered": result.get("critical_covered", 0),
        "critical_total": result.get("critical_total", 0),
        "overall_coverage_pct": round(covered / max(n_clusters, 1) * 100, 1),
        "n_assignments": result.get("n_assignments", 0),
    }