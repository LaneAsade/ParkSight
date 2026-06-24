"""
app/dependencies.py — FastAPI dependency providers.
"""

from __future__ import annotations

from .services.artifact_loader import ArtifactLoader, get_artifact_loader


def loader_dependency() -> ArtifactLoader:
    return get_artifact_loader()


# Alias used by newer routers
get_loader = loader_dependency