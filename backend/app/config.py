"""
app/config.py — FastAPI application configuration.

All file paths are read from environment variables (.env). Secrets (API
keys) are never read from settings.yaml and never exposed to the frontend.
This module is intentionally separate from `parksight.config.Settings`,
which owns pipeline *constants* (weights, thresholds, shifts, economic
assumptions). This module owns *where things live on disk* and *how the
API server is configured*.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_list(name: str, default: str) -> List[str]:
    raw = os.environ.get(name, default)
    return [x.strip() for x in raw.split(",") if x.strip()]


@dataclass(frozen=True)
class AppConfig:
    # Where pipeline outputs live. May contain either the artifacts directly,
    # or a set of run subdirectories (e.g. outputs/2026-06-20T10-00-00/).
    output_dir: Path = field(default_factory=lambda: Path(_env("PARKSIGHT_OUTPUT_DIR", "../outputs")))

    # settings.yaml — source of truth for districts, weights, thresholds, etc.
    settings_path: Path = field(default_factory=lambda: Path(_env("PARKSIGHT_SETTINGS_PATH", "../config/settings.yaml")))

    # Original input CSV — only used for on-demand metadata (row counts via
    # the temporal audit artifact), never re-read per request.
    input_csv: Path = field(default_factory=lambda: Path(_env("PARKSIGHT_INPUT_CSV", "../data/raw/violations.csv")))

    # Explicit run id override. If unset, the loader picks the newest valid
    # run directory automatically.
    run_id: Optional[str] = field(default_factory=lambda: os.environ.get("PARKSIGHT_RUN_ID") or None)

    # CORS — comma-separated list of allowed origins for the Vite dev server
    # (and any deployed frontend origin).
    frontend_origins: List[str] = field(
        default_factory=lambda: _env_list("FRONTEND_ORIGIN", "http://localhost:5173")
    )

    # Cache: re-parse an artifact only when its mtime changes.
    cache_enabled: bool = field(default_factory=lambda: _env("PARKSIGHT_CACHE_ENABLED", "true").lower() == "true")

    # Default patrol team count used by /api/patrol/current.
    default_patrol_teams: int = field(default_factory=lambda: int(_env("PARKSIGHT_DEFAULT_TEAMS", "10")))

    gzip_min_size_bytes: int = field(default_factory=lambda: int(_env("PARKSIGHT_GZIP_MIN_SIZE", "1000")))


app_config = AppConfig()

