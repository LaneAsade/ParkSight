"""
app/services/forecast_service.py — Forecasting Center backend.

Forecasts are persistence-based (last actual month, per temporal_audit.py's
walk-forward backtest) plus a learned-model result ONLY when temporal_audit.json
actually reports one. No forecast value is generated client-side, and no
confidence interval is invented — it is derived from the reported
`mae_95pct_ci`, scaled per forecast step, exactly as a naive persistence band
would be communicated.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from .artifact_loader import ArtifactLoader

_CLUSTER_ID_COL_CANDIDATES = ["cluster_id", "_cluster"]


def forecast_summary(loader: ArtifactLoader) -> Dict[str, Any]:
    temporal = loader.read_json("temporal_audit", required=False)
    if not temporal or temporal.get("skipped"):
        return {
            "validation_status": "SPEC_ONLY",
            "months_used": [],
            "excluded_months": [],
            "persistence_mae": None,
            "mae_95pct_ci": None,
            "learned_model_available": False,
            "honest_caveat": (temporal or {}).get("reason", "temporal_audit.json is unavailable."),
            "skipped_reason": (temporal or {}).get("reason"),
        }

    learned = temporal.get("learned_model")
    return {
        "validation_status": temporal.get("validation_status", "MODELED"),
        "months_used": temporal.get("months_used", []),
        "excluded_months": temporal.get("excluded_months", []),
        "persistence_mae": temporal.get("mean_mae_persistence"),
        "mae_95pct_ci": temporal.get("mae_95pct_ci"),
        "learned_model_available": learned is not None,
        "learned_model_mae": (learned or {}).get("mean_mae"),
        "learned_model_beats_persistence": (learned or {}).get("beats_persistence"),
        "honest_caveat": temporal.get("honest_caveat"),
        "skipped_reason": None,
    }


def _find_cluster_id_col(panel: pd.DataFrame) -> Optional[str]:
    for c in _CLUSTER_ID_COL_CANDIDATES:
        if c in panel.columns:
            return c
    return None


def forecast_for_cluster(loader: ArtifactLoader, cluster_id: int) -> Dict[str, Any]:
    summary = forecast_summary(loader)
    panel = loader.read_csv("monthly_panel", required=False)

    if panel is None or panel.empty:
        return {
            "cluster_id": cluster_id,
            "validation_status": "SPEC_ONLY",
            "months_used": summary["months_used"],
            "excluded_months": summary["excluded_months"],
            "series": [],
            "persistence_mae": summary["persistence_mae"],
            "mae_95pct_ci": summary["mae_95pct_ci"],
            "learned_model_available": False,
            "honest_caveat": (
                "No per-cluster monthly panel artifact was found, so a per-hotspot "
                "forecast series cannot be rendered. The pipeline-wide persistence "
                "MAE above is still reported for context."
            ),
            "skipped_reason": "monthly_panel artifact unavailable",
        }

    id_col = _find_cluster_id_col(panel)
    if id_col is None:
        return {
            "cluster_id": cluster_id, "validation_status": "SPEC_ONLY",
            "months_used": [], "excluded_months": [], "series": [],
            "persistence_mae": None, "mae_95pct_ci": None,
            "learned_model_available": False,
            "honest_caveat": "monthly_panel artifact is missing a cluster_id column.",
            "skipped_reason": "malformed monthly_panel",
        }

    sub = panel[panel[id_col].astype(str) == str(cluster_id)].copy()
    excluded = set(summary["excluded_months"])
    sub = sub[~sub["year_month"].isin(excluded)].sort_values("year_month")

    if sub.empty:
        return {
            "cluster_id": cluster_id, "validation_status": "SPEC_ONLY",
            "months_used": [], "excluded_months": list(excluded), "series": [],
            "persistence_mae": summary["persistence_mae"], "mae_95pct_ci": summary["mae_95pct_ci"],
            "learned_model_available": False,
            "honest_caveat": f"No usable monthly history for cluster {cluster_id}.",
            "skipped_reason": "no rows for cluster",
        }

    series: List[Dict[str, Any]] = [
        {"month": r["year_month"], "actual": float(r["violations"])} for _, r in sub.iterrows()
    ]

    mae_ci = summary["mae_95pct_ci"] or [None, None]
    last_val = float(sub.iloc[-1]["violations"])
    forecast_points = []
    for step in range(1, 4):
        band = None
        if mae_ci[1] is not None:
            band = float(mae_ci[1]) * (1 + 0.3 * (step - 1))
        forecast_points.append({
            "month": f"+{step}",
            "forecast": last_val,
            "low": max(0.0, last_val - band) if band is not None else None,
            "high": last_val + band if band is not None else None,
        })

    return {
        "cluster_id": cluster_id,
        "validation_status": "MODELED",
        "months_used": list(sub["year_month"]),
        "excluded_months": list(excluded),
        "series": series + forecast_points,
        "persistence_mae": summary["persistence_mae"],
        "mae_95pct_ci": summary["mae_95pct_ci"],
        "learned_model_available": summary["learned_model_available"],
        "learned_model_mae": summary.get("learned_model_mae"),
        "learned_model_beats_persistence": summary.get("learned_model_beats_persistence"),
        "honest_caveat": summary["honest_caveat"],
        "skipped_reason": None,
    }

