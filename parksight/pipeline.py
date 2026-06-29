"""
pipeline.py — Orchestrates every ParkSight AI stage end-to-end and writes
all artifacts to the output directory.

Callable both as a library:

    from parksight.pipeline import run_pipeline
    run_pipeline(input_path="data/raw/violations.csv", output_dir="outputs/")

and via the CLI (parksight.cli), which is a thin argparse wrapper around
this function.

Each stage is isolated with `utils.safe_run` — a stage failure is recorded
in `failures` and the pipeline continues with a safe fallback rather than
crashing, so a partial run still produces whatever artifacts it can.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from .bias_audit import bias_audit
from .capacity_impact import compute_capacity_impact
from .config import Settings
from .data_loader import load_and_validate
from .evidence import build_evidence_ledger
from .hotspot_detection import build_hotspot_clusters, build_junction_aggregates, run_dbscan
from .nonjunction_hotspots import build_nonjunction_hotspots
from .patrol_optimization import milp_assignment
from .reporting import generate_executive_report
from .risk_scoring import score_and_tier
from .spatial_validation import validate_spatial_stability
from .temporal_audit import build_monthly_panel, walk_forward_forecast
from .traffic_enrichment import enrich_with_traffic
from .utils import safe_run

log = logging.getLogger(__name__)


def run_pipeline(
    input_path: str,
    output_dir: str = "outputs/",
    config_path: Optional[str] = None,
    teams: Optional[int] = None,
    skip_traffic: bool = False,
    skip_external_apis: bool = False,
    google_api_key: Optional[str] = None,
    mappls_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the full ParkSight AI pipeline and write every artifact.

    Returns a dict summarizing what was produced (also useful for tests
    and for the CLI's exit-status decision), and never raises on a single
    stage's failure — see `failures` in the returned summary.
    """
    if google_api_key:
        os.environ["GOOGLE_MAPS_API_KEY"] = google_api_key
    if mappls_api_key:
        os.environ["MAPPLS_ACCESS_TOKEN"] = mappls_api_key
    skip_traffic = skip_traffic or skip_external_apis

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    settings = Settings(config_path=Path(config_path) if config_path else None)
    failures: Dict[str, str] = {}

    log.info("=== ParkSight AI pipeline starting ===")
    log.info("Input: %s | Output: %s", input_path, out_dir)

    # 1-2. Load + temporal audit
    approved, raw_df, audit = load_and_validate(input_path, settings)
    _write_json(out_dir / "temporal_audit.json", audit)

    # 3. Bias audit
    bias = safe_run("bias_audit", bias_audit, raw_df, fallback={}, failures=failures)
    _write_json(out_dir / "bias_audit.json", bias)

    # 4. Hotspot detection
    junctions = safe_run(
        "hotspot_detection.build_junction_aggregates", build_junction_aggregates,
        approved, settings, fallback=pd.DataFrame(), failures=failures,
    )
    labels = None
    dbscan_meta: Dict[str, Any] = {}
    if junctions is not None and not junctions.empty:
        result = safe_run(
            "hotspot_detection.run_dbscan", run_dbscan, junctions, settings,
            fallback=(junctions, None, {}), failures=failures,
        )
        junctions, labels, dbscan_meta = result
    clusters = []
    if junctions is not None and not junctions.empty and labels is not None:
        clusters = safe_run(
            "hotspot_detection.build_hotspot_clusters", build_hotspot_clusters,
            junctions, labels, settings, fallback=[], failures=failures,
        ) or []
    _write_json(out_dir / "dbscan_meta.json", dbscan_meta)

    cluster_df = _clusters_to_df(clusters)
    if not cluster_df.empty:
        cluster_df.to_csv(out_dir / "hotspot_clusters.csv", index=False, encoding="utf-8")

    # 5. Non-junction hotspots
    nonjunction_df = safe_run(
        "nonjunction_hotspots", build_nonjunction_hotspots, approved, settings,
        fallback=pd.DataFrame(), failures=failures,
    )
    if nonjunction_df is not None and not nonjunction_df.empty:
        nonjunction_df.to_csv(out_dir / "nonjunction_hotspots.csv", index=False, encoding="utf-8")

    # 6. Risk scoring
    risk_meta: Dict[str, Any] = {}
    if clusters:
        clusters, risk_meta = safe_run(
            "risk_scoring", score_and_tier, clusters, settings,
            fallback=(clusters, {}), failures=failures,
        )
        cluster_df = _clusters_to_df(clusters)
        cluster_df.to_csv(out_dir / "hotspot_clusters.csv", index=False, encoding="utf-8")
        risk_df = cluster_df[["cluster_id", "risk_score", "risk_tier"]].copy()
        risk_df["validation_status"] = "REAL_DATA"
        risk_df.to_csv(out_dir / "risk_scores.csv", index=False, encoding="utf-8")

    # 7. Spatial stability
    spatial: Dict[str, Any] = {}
    if clusters:
        spatial = safe_run(
            "spatial_validation", validate_spatial_stability, clusters, settings,
            fallback={}, failures=failures,
        )
    _write_json(out_dir / "spatial_stability.json", spatial)

    # 8. Traffic enrichment
    traffic_df = pd.DataFrame()
    if clusters:
        traffic_df = safe_run(
            "traffic_enrichment", enrich_with_traffic, cluster_df, settings, skip_traffic,
            fallback=pd.DataFrame(), failures=failures,
        )
        if traffic_df is not None and not traffic_df.empty:
            traffic_df.to_csv(out_dir / "traffic_enrichment.csv", index=False, encoding="utf-8")

    # 9. Road capacity impact
    capacity_df = pd.DataFrame()
    if clusters:
        capacity_df = safe_run(
            "capacity_impact", compute_capacity_impact, cluster_df, settings, skip_external_apis,
            fallback=pd.DataFrame(), failures=failures,
        )
        if capacity_df is not None and not capacity_df.empty:
            capacity_df.to_csv(out_dir / "capacity_impact.csv", index=False, encoding="utf-8")

    # 10. Patrol optimization
    n_teams = teams if teams is not None else settings.default_teams
    patrol = safe_run(
        "patrol_optimization", milp_assignment, clusters, n_teams, settings,
        fallback={}, failures=failures,
    )
    if patrol:
        pd.DataFrame(patrol.get("assignments", [])).to_csv(out_dir / "patrol_plan.csv", index=False, encoding="utf-8")

    # 10b. Monthly panel + walk-forward forecast (feeds the backend forecast endpoints)
    if clusters:
        panel = safe_run(
            "temporal_audit.build_monthly_panel", build_monthly_panel, approved,
            [c.cluster_id for c in clusters], [c.lat for c in clusters], [c.lon for c in clusters],
            fallback=pd.DataFrame(), failures=failures,
        )
        if panel is not None and not panel.empty:
            panel.to_csv(out_dir / "monthly_panel.csv", index=False, encoding="utf-8")
        exclude_months = list((audit or {}).get("review_backlog_months", {}).keys())
        forecast = safe_run(
            "temporal_audit.walk_forward_forecast", walk_forward_forecast, panel, exclude_months,
            fallback={}, failures=failures,
        )
        if forecast:
            # Merge forecast results into temporal_audit.json so the backend's
            # forecast_service (which reads temporal_audit) sees them.
            merged_audit = {**audit, **forecast}
            _write_json(out_dir / "temporal_audit.json", merged_audit)

    # 11. Evidence ledger
    evidence_df = build_evidence_ledger(
        audit, bias, dbscan_meta, risk_meta, spatial, traffic_df, capacity_df, patrol,
    )
    if not evidence_df.empty:
        evidence_df.to_csv(out_dir / "evidence_ledger.csv", index=False, encoding="utf-8")

    # 12. Executive report
    report_md = generate_executive_report(
        audit, bias, dbscan_meta, risk_meta, spatial, clusters, patrol, evidence_df, failures,
    )
    (out_dir / "executive_report.md").write_text(report_md, encoding="utf-8")

    summary = {
        "n_input_rows": int(len(raw_df)),
        "n_approved": int(len(approved)),
        "n_clusters": len(clusters),
        "n_failures": len(failures),
        "failures": failures,
        "output_dir": str(out_dir),
    }
    log.info("=== Pipeline complete: %s ===", summary)
    return summary


def _clusters_to_df(clusters) -> pd.DataFrame:
    if not clusters:
        return pd.DataFrame()
    return pd.DataFrame([
        {
            "cluster_id": c.cluster_id,
            "top_junction": c.top_junction,
            "police_station": c.police_station,
            "district": c.district,
            "violations": c.violations,
            "n_junctions": c.n_junctions,
            "pct_at_junction": c.pct_at_junction,
            "pct_peak_hour": c.pct_peak_hour,
            "top_vehicle": c.top_vehicle,
            "peak_hour": c.peak_hour,
            "lat": c.lat,
            "lon": c.lon,
            "risk_score": c.risk_score,
            "risk_tier": c.risk_tier,
        }
        for c in clusters
    ])


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    if data is None:
        data = {}
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
