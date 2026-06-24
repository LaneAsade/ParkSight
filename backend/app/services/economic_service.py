"""
app/services/economic_service.py — Economic Impact Simulator backend.

All figures here are MODELED, never measured: `closed_datetime` is null in
the source dataset, so there is no ground-truth enforcement outcome to
calibrate against. Every response explicitly says so.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .artifact_loader import ArtifactLoader

CAVEATS = [
    "Economic benefit is modeled from fixed-rate assumptions, not directly observed.",
    "closed_datetime is null in the source dataset — there is no measured enforcement "
    "outcome to calibrate these figures against.",
    "Figures assume a fixed fraction of violations are simultaneously present at peak "
    "hour; treat as directional, not an audited savings estimate.",
]


def economic_assumptions(loader: ArtifactLoader) -> Dict[str, Any]:
    econ = loader.settings_dict().get("economic", {})
    return {
        "fuel_cost_per_litre": econ.get("fuel_cost_per_litre", 103.0),
        "fuel_burn_idle_litres_per_hour": econ.get("fuel_burn_idle_litres_per_hour", 0.8),
        "co2_per_litre_fuel": econ.get("co2_per_litre_fuel", 2.31),
        "wage_inr_per_hour": econ.get("avg_wage_inr_per_hour", 120.0),
        "working_days_per_year": econ.get("working_days_per_year", 300),
        "sensitivity_scenarios": econ.get("sensitivity_scenarios", {"Pessimistic": 0.7, "Base": 1.0, "Optimistic": 1.3}),
    }


def simulate_economic(
    loader: ArtifactLoader,
    fuel_cost_per_litre: Optional[float],
    wage_inr_per_hour: Optional[float],
    enforcement_effectiveness_pct: float,
    scenario_multiplier: float,
) -> Dict[str, Any]:
    defaults = economic_assumptions(loader)
    fuel = fuel_cost_per_litre if fuel_cost_per_litre is not None else defaults["fuel_cost_per_litre"]
    wage = wage_inr_per_hour if wage_inr_per_hour is not None else defaults["wage_inr_per_hour"]
    fuel_burn = defaults["fuel_burn_idle_litres_per_hour"]
    co2_per_litre = defaults["co2_per_litre_fuel"]
    working_days = defaults["working_days_per_year"]

    merged, _ = loader.merged_hotspots()
    total_violations = int(merged["violations"].sum()) if "violations" in merged.columns else None
    avg_delay_hr = None
    if "delay_minutes" in merged.columns:
        delay_series = merged["delay_minutes"].dropna()
        if not delay_series.empty:
            avg_delay_hr = float(delay_series.mean()) / 60.0

    if total_violations is None or avg_delay_hr is None:
        return {
            "validation_status": "SPEC_ONLY",
            "estimated_delay_hours_per_year": None,
            "estimated_fuel_litres_per_year": None,
            "fuel_cost_inr_per_year": None,
            "co2_kg_per_year": None,
            "time_value_inr_per_year": None,
            "total_modeled_impact_inr_per_year": None,
            "units": {"currency": "INR", "fuel": "litres", "co2": "kg", "time": "hours"},
            "assumptions": {
                "fuel_cost_per_litre": fuel, "wage_inr_per_hour": wage,
                "enforcement_effectiveness_pct": enforcement_effectiveness_pct,
                "scenario_multiplier": scenario_multiplier,
            },
            "caveats": CAVEATS + ["No congestion delay data is available — cannot model economic impact."],
        }

    effectiveness = enforcement_effectiveness_pct / 100.0
    annual_time_hrs = total_violations * avg_delay_hr * effectiveness * working_days * scenario_multiplier
    annual_fuel_litres = total_violations * fuel_burn * avg_delay_hr * effectiveness * working_days * scenario_multiplier
    annual_fuel_cost = annual_fuel_litres * fuel
    annual_co2 = annual_fuel_litres * co2_per_litre
    annual_wage_value = annual_time_hrs * wage
    total = annual_fuel_cost + annual_wage_value

    return {
        "validation_status": "MODELED",
        "estimated_delay_hours_per_year": round(annual_time_hrs, 1),
        "estimated_fuel_litres_per_year": round(annual_fuel_litres, 1),
        "fuel_cost_inr_per_year": round(annual_fuel_cost, 2),
        "co2_kg_per_year": round(annual_co2, 1),
        "time_value_inr_per_year": round(annual_wage_value, 2),
        "total_modeled_impact_inr_per_year": round(total, 2),
        "units": {"currency": "INR", "fuel": "litres", "co2": "kg", "time": "hours"},
        "assumptions": {
            "fuel_cost_per_litre": fuel, "wage_inr_per_hour": wage,
            "enforcement_effectiveness_pct": enforcement_effectiveness_pct,
            "scenario_multiplier": scenario_multiplier,
            "fuel_burn_idle_litres_per_hour": fuel_burn,
            "co2_per_litre_fuel": co2_per_litre,
            "working_days_per_year": working_days,
            "total_violations_used": total_violations,
            "mean_delay_minutes_used": round(avg_delay_hr * 60, 2),
        },
        "caveats": CAVEATS,
    }

