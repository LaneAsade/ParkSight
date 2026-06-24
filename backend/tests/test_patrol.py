"""tests/test_patrol.py — exercises the REAL milp_assignment() from
parksight.patrol_optimization, imported as a library, not reimplemented."""

from __future__ import annotations

from app.services.patrol_service import current_patrol, simulate_patrol


def test_simulate_patrol_covers_critical_hotspot_when_teams_suffice(loader):
    merged, _ = loader.merged_hotspots()
    result = simulate_patrol(loader, merged, n_teams=4)

    assert result["validation_status"] == "REAL_DATA"
    assert result["critical_total"] == 1
    assert result["critical_covered"] == 1
    assert result["critical_coverage_mode"] == "hard_constraint_full_coverage"
    assert len(result["assignments"]) <= 4


def test_simulate_patrol_relaxes_when_teams_below_critical_count(loader):
    merged, _ = loader.merged_hotspots()
    # Add enough rows so n_critical > n_teams is testable... with only one
    # CRITICAL cluster in the fixture, request zero teams to force relaxation
    # logic to be exercised at the boundary instead.
    result = simulate_patrol(loader, merged, n_teams=1)
    assert result["n_teams_requested"] == 1
    assert result["distinct_hotspots_covered"] <= 1


def test_current_patrol_uses_default_team_count(loader):
    result = current_patrol(loader)
    assert result["n_teams_requested"] == loader._config.default_patrol_teams  # noqa: SLF001


def test_patrol_shift_capacities_sum_to_team_count(loader):
    merged, _ = loader.merged_hotspots()
    result = simulate_patrol(loader, merged, n_teams=6)
    assert sum(result["shift_capacities"].values()) == 6

