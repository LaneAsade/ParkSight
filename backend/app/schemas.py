"""
app/schemas.py — Pydantic response/request models.

Evidence labels (REAL_DATA / MODELED / SPEC_ONLY / PARTIAL) are preserved
verbatim from the pipeline artifacts everywhere they appear. Numeric fields
that the pipeline could not produce are `None` (JSON `null`), never 0.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

EvidenceStatus = Literal["REAL_DATA", "MODELED", "SPEC_ONLY", "PARTIAL"]
RiskTier = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]


# ───────────────────────── Errors ─────────────────────────

class ErrorDetail(BaseModel):
    code: str
    message: str
    artifact: Optional[str] = None
    required: Optional[bool] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ───────────────────────── System ─────────────────────────

class ArtifactDiagnostic(BaseModel):
    matched: int = 0
    unmatched: int = 0
    duplicate_keys: int = 0
    present: bool = False
    path: Optional[str] = None
    last_modified: Optional[str] = None
    row_count: Optional[int] = None
    error: Optional[str] = None


class ApiSourceStatus(BaseModel):
    google_traffic: Literal["AVAILABLE", "UNAVAILABLE", "PARTIAL"]
    mappls: Literal["AVAILABLE", "UNAVAILABLE"]
    osm: Literal["AVAILABLE", "UNAVAILABLE"]


class SystemStatus(BaseModel):
    pipeline_status: Literal["READY", "DEGRADED", "NOT_FOUND"]
    active_run: Optional[str]
    output_dir: str
    last_modified: Optional[str]
    available_artifacts: List[str]
    missing_artifacts: List[str]
    api_sources: ApiSourceStatus
    merge_diagnostics: Dict[str, ArtifactDiagnostic] = Field(default_factory=dict)


class RunInfo(BaseModel):
    run_id: str
    path: str
    last_modified: Optional[str]
    is_active: bool


class SystemConfigOut(BaseModel):
    districts: List[str]
    risk_weights: Dict[str, float]
    tier_thresholds_percentile: Dict[str, int]
    patrol_shifts: List[str]
    economic_assumptions: Dict[str, Any]
    dbscan: Dict[str, Any]
    road_capacity_summary: Dict[str, Any]
    integrations_available: ApiSourceStatus


# ───────────────────────── Overview ─────────────────────────

class OverviewOut(BaseModel):
    model_config = ConfigDict(extra="allow")   
    total_input_rows: Optional[int] = None
    total_approved_violations: Optional[int] = None
    approval_pct: Optional[float] = None
    n_hotspot_clusters: Optional[int] = None
    n_nonjunction_hotspots: Optional[int] = None
    n_critical_hotspots: Optional[int] = None
    active_districts: Optional[int] = None
    distinct_police_stations: Optional[int] = None
    distinct_junctions: Optional[int] = None
    mean_congestion_index: Optional[float] = None
    mean_congestion_validation_status: Optional[EvidenceStatus] = None
    patrol_coverage_pct: Optional[float] = None
    patrol_teams_used: Optional[int] = None
    evidence_status_counts: Dict[str, int] = {}
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    backlog_warning: Optional[str] = None
    filename_date_mismatch_warning: Optional[str] = None
    dbscan_silhouette: Optional[float] = None
    cluster_count_ci: Optional[List[float]] = None
    spatial_stability_score: Optional[float] = None
    spatial_stability_interpretation: Optional[str] = None
    active_run: Optional[str] = None
    last_pipeline_update: Optional[str] = None
    available_artifacts: List[str] = []
    missing_artifacts: List[str] = []
    bias_pseudo_r2: Optional[float] = None      
    bias_interpretation: Optional[str] = None   

# ───────────────────────── Hotspots ─────────────────────────

class HotspotOut(BaseModel):
    cluster_id: int
    top_junction: Optional[str]
    police_station: Optional[str]
    district: Optional[str]
    violations: Optional[int]
    n_junctions: Optional[int]
    pct_at_junction: Optional[float]
    pct_peak_hour: Optional[float]
    top_vehicle: Optional[str]
    peak_hour: Optional[int]
    lat: Optional[float]
    lon: Optional[float]
    risk_score: Optional[float]
    risk_tier: Optional[RiskTier]
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    station_breakdown: Optional[Dict[str, float]] = None
    multi_jurisdiction: Optional[bool] = None

    congestion_index: Optional[float] = None
    delay_minutes: Optional[float] = None
    avg_speed_kmh: Optional[float] = None
    traffic_validation_status: Optional[EvidenceStatus] = None

    road_class: Optional[str] = None
    lane_count: Optional[int] = None
    road_width_m: Optional[float] = None
    geometry_source: Optional[str] = None
    geometry_validation_status: Optional[EvidenceStatus] = None
    confidence_level: Optional[str] = None
    capacity_loss_pct: Optional[float] = None
    capacity_loss_tier: Optional[str] = None
    erci_index: Optional[float] = None


class HotspotListOut(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[HotspotOut]


class NonJunctionHotspotOut(BaseModel):
    hex_id: str
    violations: Optional[int]
    lat: Optional[float]
    lon: Optional[float]
    police_station: Optional[str]
    district: Optional[str]


# ───────────────────────── Congestion ─────────────────────────

class CongestionSummaryOut(BaseModel):
    total_hotspots: int
    real_data_count: int
    partial_count: int
    spec_only_count: int
    mean_congestion_index: Optional[float]
    mean_delay_minutes: Optional[float]


class CongestionByDistrictOut(BaseModel):
    district: str
    n_hotspots: int
    mean_delay_minutes: Optional[float]
    mean_congestion_index: Optional[float]


class CongestionRelationshipPoint(BaseModel):
    cluster_id: int
    violations: int
    congestion_index: Optional[float]
    risk_tier: Optional[RiskTier]
    validation_status: EvidenceStatus


class CongestionRelationshipOut(BaseModel):
    points: List[CongestionRelationshipPoint]
    sample_size: int
    validation_status_counts: Dict[str, int]
    observational_caveat: str = (
        "This relationship is observational. Violations indicate where enforcement "
        "occurred, not a controlled measurement of congestion without parking. "
        "Do not interpret this as a causal effect."
    )


# ───────────────────────── Patrol ─────────────────────────

class PatrolAssignmentOut(BaseModel):
    cluster_id: int
    hotspot: Optional[str]
    top_junction: Optional[str]
    risk_tier: Optional[RiskTier]
    shift: str
    impact_score: float


class PatrolSimulateRequest(BaseModel):
    teams: int = Field(ge=1, le=500)


class PatrolResultOut(BaseModel):
    validation_status: EvidenceStatus
    solved_to_optimality: bool
    used_greedy_fallback: bool
    n_teams_requested: int
    n_teams_placeable: int
    n_assignments: int
    critical_covered: int
    critical_total: int
    distinct_hotspots_covered: int
    distinct_hotspots_total: int
    overall_coverage_pct: float
    critical_coverage_mode: str
    critical_coverage_note: str
    skipped_reason: Optional[str] = None
    shifts: List[str]
    assignments: List[PatrolAssignmentOut]
    shift_capacities: Dict[str, int] = Field(default_factory=dict)


# ───────────────────────── Forecast ─────────────────────────

class ForecastPoint(BaseModel):
    month: str
    actual: Optional[float] = None
    forecast: Optional[float] = None
    low: Optional[float] = None
    high: Optional[float] = None


class ForecastOut(BaseModel):
    cluster_id: Optional[int]
    validation_status: EvidenceStatus
    months_used: List[str]
    excluded_months: List[str]
    series: List[ForecastPoint]
    persistence_mae: Optional[float]
    mae_95pct_ci: Optional[List[float]]
    learned_model_available: bool
    learned_model_mae: Optional[float] = None
    learned_model_beats_persistence: Optional[bool] = None
    honest_caveat: Optional[str]
    skipped_reason: Optional[str] = None


# ───────────────────────── Economic ─────────────────────────

class EconomicAssumptionsOut(BaseModel):
    fuel_cost_per_litre: float
    fuel_burn_idle_litres_per_hour: float
    co2_per_litre_fuel: float
    wage_inr_per_hour: float
    working_days_per_year: int
    sensitivity_scenarios: Dict[str, float]


class EconomicSimulateRequest(BaseModel):
    fuel_cost_per_litre: Optional[float] = None
    wage_inr_per_hour: Optional[float] = None
    enforcement_effectiveness_pct: float = Field(default=55.0, ge=0, le=100)
    scenario_multiplier: float = Field(default=1.0, gt=0, le=5)


class EconomicSimulateOut(BaseModel):
    validation_status: EvidenceStatus = "MODELED"
    estimated_delay_hours_per_year: Optional[float]
    estimated_fuel_litres_per_year: Optional[float]
    fuel_cost_inr_per_year: Optional[float]
    co2_kg_per_year: Optional[float]
    time_value_inr_per_year: Optional[float]
    total_modeled_impact_inr_per_year: Optional[float]
    units: Dict[str, str]
    assumptions: Dict[str, Any]
    caveats: List[str]


# ───────────────────────── Evidence ─────────────────────────

class EvidenceRecordOut(BaseModel):
    claim: str
    value: Optional[str]
    status: EvidenceStatus
    source: Optional[str]
    confidence: Optional[str]


class EvidenceListOut(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[EvidenceRecordOut]


class EvidenceSummaryOut(BaseModel):
    counts: Dict[str, int]
    total: int


# ───────────────────────── Scenarios ─────────────────────────

class ScenarioValue(BaseModel):
    value: Optional[float]
    validation_status: EvidenceStatus
    assumptions: List[str] = Field(default_factory=list)


class ScenarioSimulateRequest(BaseModel):
    additional_patrol_teams: int = Field(default=0, ge=0, le=200)
    risk_tier_thresholds: Optional[Dict[str, int]] = None
    economic_overrides: Optional[EconomicSimulateRequest] = None
    assumed_violation_reduction_pct: float = Field(default=0.0, ge=0, le=100)


class ScenarioSimulateOut(BaseModel):
    baseline: Dict[str, ScenarioValue]
    scenario: Dict[str, ScenarioValue]
    note: str = "All scenario deltas are illustrative projections layered on MODELED baselines — not measured outcomes."


# ───────────────────────── Copilot ─────────────────────────

class CopilotQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class CopilotQueryOut(BaseModel):
    answer: str
    supporting_data: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_statuses: List[EvidenceStatus] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)

