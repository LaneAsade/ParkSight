"""
tests/conftest.py — Points the backend at tests/fixtures/ instead of a real
pipeline output directory, and gives every test a clean ArtifactLoader.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _TESTS_DIR.parent
_PROJECT_ROOT = _BACKEND_DIR.parent

if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.config import AppConfig  # noqa: E402
from app.services.artifact_loader import ArtifactLoader  # noqa: E402


@pytest.fixture()
def fixtures_config() -> AppConfig:
    return AppConfig(
        output_dir=_TESTS_DIR / "fixtures",
        settings_path=_PROJECT_ROOT / "config" / "settings.yaml",
        input_csv=_PROJECT_ROOT / "data" / "raw" / "violations.csv",
        run_id=None,
        frontend_origins=["http://localhost:5173"],
        cache_enabled=False,
        default_patrol_teams=10,
    )


@pytest.fixture()
def loader(fixtures_config: AppConfig) -> ArtifactLoader:
    return ArtifactLoader(fixtures_config)


@pytest.fixture()
def empty_loader(tmp_path: Path, fixtures_config: AppConfig) -> ArtifactLoader:
    """A loader pointed at an empty output directory — exercises the
    'no artifacts at all' path."""
    cfg = AppConfig(
        output_dir=tmp_path / "empty_outputs",
        settings_path=fixtures_config.settings_path,
        input_csv=fixtures_config.input_csv,
        run_id=None,
        frontend_origins=fixtures_config.frontend_origins,
        cache_enabled=False,
        default_patrol_teams=10,
    )
    (tmp_path / "empty_outputs").mkdir(parents=True, exist_ok=True)
    return ArtifactLoader(cfg)

