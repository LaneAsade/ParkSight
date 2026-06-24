"""tests/test_economic.py"""

from __future__ import annotations

from app.services.economic_service import economic_assumptions, simulate_economic


def test_assumptions_come_from_settings_yaml(loader):
    assumptions = economic_assumptions(loader)
    assert assumptions["fuel_cost_per_litre"] > 0
    assert "Base" in assumptions["sensitivity_scenarios"]


def test_simulate_economic_is_modeled_and_uses_real_delay_data(loader):
    result = simulate_economic(
        loader, fuel_cost_per_litre=100.0, wage_inr_per_hour=120.0,
        enforcement_effectiveness_pct=50.0, scenario_multiplier=1.0,
    )
    assert result["validation_status"] == "MODELED"
    assert result["total_modeled_impact_inr_per_year"] > 0
    assert any("modeled" in c.lower() for c in result["caveats"])


def test_simulate_economic_handles_missing_congestion_data(empty_loader):
    # empty_loader has no hotspot_clusters at all -> merged_hotspots() raises,
    # which simulate_economic does not catch itself — routers are responsible
    # for translating ArtifactError into an HTTP 404. Asserted explicitly so
    # this isn't silently swallowed by a future refactor.
    import pytest
    from app.services.artifact_loader import ArtifactError
    with pytest.raises(ArtifactError):
        simulate_economic(
            empty_loader, fuel_cost_per_litre=None, wage_inr_per_hour=None,
            enforcement_effectiveness_pct=55.0, scenario_multiplier=1.0,
        )

