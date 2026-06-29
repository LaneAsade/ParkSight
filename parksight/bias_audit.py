"""
bias_audit.py — Selection-bias audit for the approval process.

Fits a logistic regression of approval status ~ vehicle_type + police_station
+ hour (cyclically encoded) on the adjudicated subset, and reports McFadden
pseudo-R². A high R² means systematic approval bias; low means independent.
"""

import logging
from typing import Dict

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, log_loss
from sklearn.preprocessing import OrdinalEncoder

from .utils import REAL_DATA, SPEC_ONLY

log = logging.getLogger(__name__)

try:
    import pandas as pd
    _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False


def _cyclical_hour_features(hour: np.ndarray) -> np.ndarray:
    """Encode hour-of-day as sin/cos pair so hour 23 and 0 are adjacent."""
    radians = 2 * np.pi * hour.astype(float) / 24.0
    return np.column_stack([np.sin(radians), np.cos(radians)])


def bias_audit(raw_df) -> Dict:
    """Estimate systematic approval bias via logistic regression.

    Restricted to rows with validation_status in {approved, rejected}.
    Returns a metadata dict written to bias_audit.json.
    """
    import pandas as pd
    log.info("Running selection-bias audit...")

    d = raw_df[raw_df["validation_status"].isin(["approved", "rejected"])][
        ["validation_status", "vehicle_type", "police_station", "hour"]
    ].copy()
    excluded_n = len(raw_df) - len(d)

    if len(d) == 0:
        return {
            "validation_status": SPEC_ONLY,
            "skipped": True,
            "reason": (
                "No adjudicated rows — bias audit requires approved + rejected records. "
                "All records may still be pending review."
            ),
            "excluded_unadjudicated_rows": int(excluded_n),
        }

    d["is_approved"] = (d["validation_status"] == "approved").astype(int)
    d["vehicle_type"] = d["vehicle_type"].fillna("UNKNOWN")
    d["police_station"] = d["police_station"].fillna("UNKNOWN")
    d["hour"] = d["hour"].fillna(6).astype(int)
    d_samp = d.sample(min(50_000, len(d)), random_state=42)

    if d_samp["is_approved"].nunique() < 2:
        only_class = "approved" if d_samp["is_approved"].iloc[0] == 1 else "rejected"
        return {
            "validation_status": SPEC_ONLY,
            "skipped": True,
            "reason": (
                f"All adjudicated rows are '{only_class}' — logistic regression requires both "
                "classes. The file may be pre-filtered to one validation_status."
            ),
            "sample_size": len(d_samp),
            "excluded_unadjudicated_rows": int(excluded_n),
        }

    enc = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    x_cat = enc.fit_transform(d_samp[["vehicle_type", "police_station"]])
    x_hour = _cyclical_hour_features(d_samp["hour"].values)
    X = np.hstack([x_cat, x_hour])
    y = d_samp["is_approved"].values

    lr = LogisticRegression(max_iter=500, random_state=42).fit(X, y)
    p = lr.predict_proba(X)[:, 1]
    ll_model = -log_loss(y, p, normalize=False)
    p0 = y.mean()
    ll_null = float(np.sum(y * np.log(p0 + 1e-9) + (1 - y) * np.log(1 - p0 + 1e-9)))
    pseudo_r2 = round(1 - ll_model / (ll_null + 1e-9), 4)

    lr_bal = LogisticRegression(max_iter=500, class_weight="balanced", random_state=42).fit(X, y)
    bal_acc = round(float(balanced_accuracy_score(y, lr_bal.predict(X))), 4)

    if pseudo_r2 < 0.10:
        interpretation = "LOW (<0.10): approval is largely independent of these features."
    elif pseudo_r2 < 0.25:
        interpretation = "MODERATE (0.10–0.25): some systematic approval bias detected."
    else:
        interpretation = "HIGH (>0.25): strong systematic bias — counts may not represent true rates."

    log.info("Bias audit: pseudo-R²=%.4f (%s)", pseudo_r2, interpretation)
    return {
        "validation_status": REAL_DATA,
        "sample_size": len(d_samp),
        "excluded_unadjudicated_rows": int(excluded_n),
        "mcfadden_pseudo_r2": pseudo_r2,
        "balanced_accuracy_supplementary": bal_acc,
        "interpretation": interpretation,
        "note": (
            "Restricted to adjudicated records; pseudo-R² from unweighted fit; "
            "hour encoded cyclically (sin/cos) rather than as a flat ordinal scale."
        ),
    }
