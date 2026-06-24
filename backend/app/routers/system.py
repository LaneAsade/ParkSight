"""app/routers/system.py — health, pipeline status, run listing, config, reload."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..config import app_config
from ..dependencies import loader_dependency
from ..schemas import ApiSourceStatus, RunInfo, SystemConfigOut, SystemStatus
from ..services.artifact_loader import ArtifactLoader

router = APIRouter(prefix="/api", tags=["system"])


def _api_sources() -> ApiSourceStatus:
    import os
    google = "AVAILABLE" if os.environ.get("GOOGLE_MAPS_API_KEY") else "UNAVAILABLE"
    mappls = "AVAILABLE" if (os.environ.get("MAPPLS_ACCESS_TOKEN") or os.environ.get("MAPPLS_CLIENT_ID")) else "UNAVAILABLE"
    # OSM (Overpass) needs no key — it's "available" unless explicitly disabled.
    osm = "UNAVAILABLE" if os.environ.get("PARKSIGHT_DISABLE_OSM") == "true" else "AVAILABLE"
    return ApiSourceStatus(google_traffic=google, mappls=mappls, osm=osm)  # type: ignore[arg-type]


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/system/status", response_model=SystemStatus)
def system_status(loader: ArtifactLoader = Depends(loader_dependency)) -> SystemStatus:
    available, missing = loader.artifact_status()
    run_dir = loader.active_run_dir()
    pipeline_status = "NOT_FOUND" if not run_dir.exists() else ("READY" if "hotspot_clusters" in available else "DEGRADED")

    diagnostics = {}
    if "hotspot_clusters" in available:
        try:
            _, diag = loader.merged_hotspots()
            diagnostics = {k: v.as_dict() for k, v in diag.items()}
        except Exception:  # noqa: BLE001
            pass

    last_modified = None
    if run_dir.exists():
        files = [f for f in run_dir.iterdir() if f.is_file()]
        if files:
            import pandas as pd
            newest = max(files, key=lambda f: f.stat().st_mtime)
            last_modified = pd.Timestamp(newest.stat().st_mtime, unit="s").isoformat()

    return SystemStatus(
        pipeline_status=pipeline_status,  # type: ignore[arg-type]
        active_run=loader.active_run_label(),
        output_dir=str(loader.output_dir),
        last_modified=last_modified,
        available_artifacts=available,
        missing_artifacts=missing,
        api_sources=_api_sources(),
        merge_diagnostics=diagnostics,
    )


@router.get("/system/runs", response_model=list[RunInfo])
def system_runs(loader: ArtifactLoader = Depends(loader_dependency)) -> list[RunInfo]:
    return [RunInfo(**r) for r in loader.list_runs()]


@router.get("/system/config", response_model=SystemConfigOut)
def system_config(loader: ArtifactLoader = Depends(loader_dependency)) -> SystemConfigOut:
    settings = loader.settings_dict()
    districts = [d[-1] if isinstance(d, list) else d.get("name") for d in settings.get("districts", [])]
    return SystemConfigOut(
        districts=districts,
        risk_weights=settings.get("risk_scoring", {}).get("weights", {}),
        tier_thresholds_percentile=settings.get("risk_scoring", {}).get("tier_thresholds_percentile", {}),
        patrol_shifts=settings.get("patrol", {}).get("shifts", []),
        economic_assumptions=settings.get("economic", {}),
        dbscan=settings.get("dbscan", {}),
        road_capacity_summary={
            "base_capacity_veh_hr_per_dir": settings.get("road_capacity", {}).get("base_capacity_veh_hr_per_dir", {}),
            "max_obstruction_loss": settings.get("road_capacity", {}).get("max_obstruction_loss", {}),
        },
        integrations_available=_api_sources(),
    )


@router.post("/system/reload")
def system_reload(loader: ArtifactLoader = Depends(loader_dependency)) -> dict:
    """Clears the in-memory artifact cache. Files are re-read on next request
    (and only re-parsed if their mtime actually changed)."""
    loader._cache.clear()  # noqa: SLF001 — intentional cache-bust, same module concern
    loader._yaml_cache = None  # noqa: SLF001
    return {"status": "reloaded", "active_run": loader.active_run_label()}

