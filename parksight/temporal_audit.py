"""
temporal_audit.py — Monthly walk-forward forecast vs persistence baseline.

Excludes adjudication-backlog months (detected in data_loader) from the
training series so right-censored months don't masquerade as real dips.
"""

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error

from .utils import MODELED, SPEC_ONLY

log = logging.getLogger(__name__)

MIN_MONTHS_FOR_MODEL = 6


def build_monthly_panel(
    approved: pd.DataFrame,
    cluster_ids: List[int],
    cluster_lats: List[float],
    cluster_lons: List[float],
) -> pd.DataFrame:
    """Assign each approved violation to its nearest cluster centroid and
    aggregate monthly counts into a panel."""
    if not cluster_ids or approved.empty:
        return pd.DataFrame(columns=["_cluster", "year_month", "violations"])

    approved = approved.copy()
    approved["year_month"] = approved["created_datetime_ist"].dt.to_period("M").astype(str)

    c_lats = np.array(cluster_lats)
    c_lons = np.array(cluster_lons)
    c_ids = np.array(cluster_ids)
    lat_arr = approved["latitude"].values
    lon_arr = approved["longitude"].values
    d2 = (lat_arr[:, None] - c_lats[None, :]) ** 2 + (lon_arr[:, None] - c_lons[None, :]) ** 2
    approved = approved.assign(_cluster=c_ids[d2.argmin(axis=1)])

    panel = (
        approved.groupby(["_cluster", "year_month"])
        .size()
        .reset_index(name="violations")
        .sort_values(["_cluster", "year_month"])
    )
    return panel


def walk_forward_forecast(
    panel: pd.DataFrame,
    exclude_months: Optional[List[str]] = None,
) -> Dict:
    """Walk-forward backtest of a persistence (last-month) baseline.

    Returns a metadata dict written to temporal_audit.json. A learned
    model (GradientBoostingRegressor) is attempted only when ≥6 usable
    months exist after excluding backlog months.
    """
    log.info("Running walk-forward forecast backtest...")
    if panel.empty:
        return {
            "validation_status": SPEC_ONLY,
            "skipped": True,
            "reason": "No monthly panel data (no clusters or no approved rows).",
        }

    exclude = set(exclude_months or [])
    months = sorted(m for m in panel["year_month"].unique() if m not in exclude)
    if len(months) < 2:
        return {
            "validation_status": SPEC_ONLY,
            "skipped": True,
            "reason": f"Only {len(months)} usable month(s) after excluding backlog — need ≥2.",
        }

    wide = (
        panel[panel["year_month"].isin(months)]
        .pivot(index="_cluster", columns="year_month", values="violations")
        .fillna(0)[months]
    )

    steps = []
    for i in range(len(months) - 1):
        y_true = wide[months[i + 1]].values
        y_pred = wide[months[i]].values
        steps.append({
            "train_month": months[i],
            "target_month": months[i + 1],
            "n_clusters": len(wide),
            "mae_persistence": round(float(mean_absolute_error(y_true, y_pred)), 1),
        })

    mae_vals = [s["mae_persistence"] for s in steps]
    rng = np.random.RandomState(0)
    boot = [rng.choice(mae_vals, size=len(mae_vals), replace=True).mean() for _ in range(500)]
    ci_lo, ci_hi = np.percentile(boot, [2.5, 97.5])

    learned_result = None
    if len(months) >= MIN_MONTHS_FOR_MODEL:
        learned_result = _fit_learned_model(wide, months, mae_vals)

    return {
        "validation_status": MODELED,
        "months_used": months,
        "excluded_months": list(exclude),
        "n_persistence_steps": len(steps),
        "persistence_steps": steps,
        "mean_mae_persistence": round(float(np.mean(mae_vals)), 1),
        "mae_95pct_ci": [round(float(ci_lo), 1), round(float(ci_hi), 1)],
        "learned_model": learned_result,
        "honest_caveat": (
            f"Only {len(months)} usable calendar month(s). "
            + ("Persistence baseline (last month's count) is the only defensible forecast."
               if learned_result is None else
               "Learned model attempted with leave-one-transition-out CV.")
        ),
    }


def _fit_learned_model(wide: pd.DataFrame, months: list, baseline_mae: list) -> Optional[Dict]:
    """Attempt a GradientBoostingRegressor with leave-one-transition-out CV.
    Returns None if sklearn is unavailable or fitting fails."""
    try:
        from sklearn.ensemble import GradientBoostingRegressor
    except ImportError:
        return None

    feats, labels, t_idx = [], [], []
    for i in range(1, len(months) - 1):
        for c in wide.index:
            row = wide.loc[c, months[: i + 1]].values
            feats.append([row[-1], row.mean(), row.std() if len(row) > 1 else 0.0, len(row)])
            labels.append(wide.loc[c, months[i + 1]])
            t_idx.append(i)

    feats = np.array(feats)
    labels = np.array(labels)
    t_idx = np.array(t_idx)
    model_maes = []
    for held in sorted(set(t_idx)):
        train, test = t_idx != held, t_idx == held
        if train.sum() < 10 or test.sum() < 1:
            continue
        gbr = GradientBoostingRegressor(n_estimators=80, max_depth=2, learning_rate=0.08, random_state=42)
        gbr.fit(feats[train], labels[train])
        model_maes.append(float(mean_absolute_error(labels[test], gbr.predict(feats[test]))))

    if not model_maes:
        return None
    mean_model_mae = float(np.mean(model_maes))
    return {
        "method": "Leave-one-transition-out GradientBoostingRegressor",
        "mean_mae": round(mean_model_mae, 1),
        "beats_persistence": bool(mean_model_mae < float(np.mean(baseline_mae))),
    }
