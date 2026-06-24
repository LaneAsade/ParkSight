"""tests/test_overview.py"""

from __future__ import annotations

from app.services.dashboard_service import build_overview


def test_overview_aggregates_real_artifacts(loader):
    overview = build_overview(loader, default_teams=2)

    assert overview["total_approved_violations"] == 4700
    assert overview["n_hotspot_clusters"] == 4
    assert overview["n_critical_hotspots"] == 1
    assert overview["n_nonjunction_hotspots"] == 2
    assert overview["active_districts"] == 4

    # Only clusters 0 and 1 have a non-null congestion_index (cluster 2 is
    # SPEC_ONLY/null, cluster 3 has no traffic_enrichment row at all).
    assert overview["mean_congestion_index"] is not None
    assert 1.5 < overview["mean_congestion_index"] < 1.9
    assert overview["mean_congestion_validation_status"] == "PARTIAL"

    assert overview["backlog_warning"] is not None
    assert overview["filename_date_mismatch_warning"] is not None
    assert overview["spatial_stability_score"] == 0.64
    assert overview["evidence_status_counts"]["REAL_DATA"] == 3


def test_overview_patrol_coverage_uses_real_solver(loader):
    overview = build_overview(loader, default_teams=2)
    assert overview["patrol_coverage_pct"] is not None
    assert 0 <= overview["patrol_coverage_pct"] <= 100
    assert overview["patrol_teams_used"] == 2


def test_overview_handles_missing_pipeline_gracefully(empty_loader):
    overview = build_overview(empty_loader, default_teams=10)
    assert overview["n_hotspot_clusters"] is None
    assert overview["total_approved_violations"] is None
    assert "hotspot_clusters" in overview["missing_artifacts"]

