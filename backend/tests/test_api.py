"""
tests/test_api.py — End-to-end smoke tests through the actual HTTP routes,
with the artifact loader monkeypatched onto the fixtures directory.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(loader, monkeypatch):
    from app.main import app
    from app.dependencies import loader_dependency as original_dep

    app.dependency_overrides.clear()
    app.dependency_overrides[original_dep] = lambda: loader
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_overview_endpoint(client):
    resp = client.get("/api/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_approved_violations"] == 4700
    assert body["n_hotspot_clusters"] == 4


def test_hotspots_list_and_filter(client):
    resp = client.get("/api/hotspots", params={"risk_tier": "CRITICAL"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["cluster_id"] == 0


def test_hotspot_detail_404_for_unknown_cluster(client):
    resp = client.get("/api/hotspots/999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "HOTSPOT_NOT_FOUND"


def test_patrol_simulate_endpoint(client):
    resp = client.post("/api/patrol/simulate", json={"teams": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_teams_requested"] == 3
    assert body["used_greedy_fallback"] in (True, False)


def test_evidence_endpoint(client):
    resp = client.get("/api/evidence", params={"status": "REAL_DATA"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 3


def test_economic_simulate_endpoint(client):
    resp = client.post("/api/economic/simulate", json={"enforcement_effectiveness_pct": 60})
    assert resp.status_code == 200
    body = resp.json()
    assert body["validation_status"] == "MODELED"


def test_copilot_query_endpoint(client):
    resp = client.post("/api/copilot/query", json={"query": "what is the highest risk hotspot"})
    assert resp.status_code == 200
    body = resp.json()
    assert "Silk Board" in body["answer"]

