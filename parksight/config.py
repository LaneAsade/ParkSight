"""
config.py — Load settings.yaml and environment variables.

Secrets (API keys) come only from environment variables, never from the
YAML config file. All pipeline constants come from settings.yaml.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

log = logging.getLogger(__name__)

# Load .env if present (silently ignored if missing)
load_dotenv()

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "settings.yaml"


def load_settings(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load pipeline settings from settings.yaml."""
    path = Path(config_path) if config_path else _DEFAULT_CONFIG_PATH
    if not path.exists():
        log.warning("settings.yaml not found at %s — using empty config", path)
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


class Settings:
    """Thin wrapper around the settings dict with attribute-style access."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._cfg = load_settings(config_path)

    def get(self, *keys: str, default: Any = None) -> Any:
        """Nested key lookup: settings.get('dbscan', 'eps_km', default=0.5)."""
        node = self._cfg
        for k in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(k, default)
        return node

    # ── Convenience accessors ─────────────────────────────────────────

    @property
    def dbscan_eps_km(self) -> float:
        return self.get("dbscan", "eps_km", default=0.5)

    @property
    def dbscan_min_samples(self) -> int:
        return self.get("dbscan", "min_samples", default=2)

    @property
    def min_junction_violations(self) -> int:
        return self.get("hotspots", "min_junction_violations", default=100)

    @property
    def min_nonjunction_violations(self) -> int:
        return self.get("hotspots", "min_nonjunction_violations", default=30)

    @property
    def lat_km_per_deg(self) -> float:
        return self.get("spatial", "lat_km_per_deg", default=111.0)

    @property
    def lon_km_per_deg_fallback(self) -> float:
        return self.get("spatial", "lon_km_per_deg_fallback", default=108.5)

    @property
    def peak_hours_ist(self) -> set:
        return set(self.get("temporal", "peak_hours_ist", default=list(range(2, 13))))

    @property
    def ist_offset_hours(self) -> float:
        return self.get("temporal", "ist_offset_hours", default=5.5)

    @property
    def risk_weights(self) -> Dict[str, float]:
        return self.get("risk_scoring", "weights", default={
            "violation_count": 0.55,
            "at_junction_pct": 0.25,
            "vehicle_severity": 0.10,
            "peak_hour_pct": 0.10,
        })

    @property
    def tier_thresholds(self) -> Dict[str, int]:
        return self.get("risk_scoring", "tier_thresholds_percentile", default={
            "critical": 85, "high": 60, "medium": 25,
        })

    @property
    def vehicle_weights(self) -> Dict[str, float]:
        return self.get("vehicle_weights", default={})

    @property
    def districts(self) -> list:
        return self.get("districts", default=[])

    @property
    def default_teams(self) -> int:
        return self.get("patrol", "default_teams", default=10)

    @property
    def patrol_shifts(self) -> list:
        return self.get("patrol", "shifts", default=[
            "Dawn 02-07 IST", "Morning 07-12 IST",
            "Afternoon 12-19 IST", "Evening 19-02 IST",
        ])

    @property
    def economic(self) -> Dict[str, Any]:
        return self.get("economic", default={})

    @property
    def road_capacity(self) -> Dict[str, Any]:
        return self.get("road_capacity", default={})

    @property
    def traffic(self) -> Dict[str, Any]:
        return self.get("traffic", default={})

    @property
    def bootstrap_iterations(self) -> int:
        return self.get("bootstrap", "n_iterations", default=300)


class ApiKeys:
    """Read API keys from environment variables only — never from config files."""

    @staticmethod
    def google_maps() -> str:
        return os.environ.get("GOOGLE_MAPS_API_KEY", "")

    @staticmethod
    def mappls_access_token() -> str:
        return os.environ.get("MAPPLS_ACCESS_TOKEN", "")

    @staticmethod
    def mappls_client_id() -> str:
        return os.environ.get("MAPPLS_CLIENT_ID", "")

    @staticmethod
    def mappls_client_secret() -> str:
        return os.environ.get("MAPPLS_CLIENT_SECRET", "")

    @staticmethod
    def any_traffic_api_available() -> bool:
        return bool(ApiKeys.google_maps() or ApiKeys.mappls_access_token()
                    or ApiKeys.mappls_client_id())
