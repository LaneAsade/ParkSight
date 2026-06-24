"""tests/test_artifact_loader.py"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from app.services.artifact_loader import ArtifactError


def test_discovers_required_artifact(loader):
    path = loader.artifact_path("hotspot_clusters")
    assert path is not None
    assert path.name == "hotspot_clusters.csv"


def test_missing_optional_artifact_returns_none(loader):
    assert loader.read_csv("risk_scores", required=False) is None


def test_missing_required_artifact_raises(empty_loader):
    with pytest.raises(ArtifactError) as exc_info:
        empty_loader.merged_hotspots()
    assert exc_info.value.code == "MISSING_ARTIFACT"
    assert exc_info.value.required is True


def test_artifact_status_lists_available_and_missing(loader):
    available, missing = loader.artifact_status()
    assert "hotspot_clusters" in available
    assert "traffic_enrichment" in available
    assert "risk_scores" in missing
    assert "patrol_plan" in missing


def test_merge_renames_and_fills_columns(loader):
    merged, diagnostics = loader.merged_hotspots()
    assert len(merged) == 4
    # cluster 0 has real traffic data
    row0 = merged[merged["cluster_id"] == 0].iloc[0]
    assert row0["congestion_index"] == pytest.approx(1.82)
    assert row0["traffic_validation_status"] == "REAL_DATA"
    # cluster 3 has neither capacity nor traffic enrichment rows
    row3 = merged[merged["cluster_id"] == 3].iloc[0]
    assert pd.isna(row3["congestion_index"])
    assert pd.isna(row3.get("road_class"))


def test_merge_diagnostics_track_unmatched_rows(loader):
    _, diagnostics = loader.merged_hotspots()
    cap = diagnostics["capacity_impact"]
    assert cap.present is True
    assert cap.matched == 3
    assert cap.unmatched == 1  # cluster_id 3 has no capacity row
    missing = diagnostics["risk_scores"]
    assert missing.present is False


def test_duplicate_cluster_ids_are_detected_and_deduped(tmp_path, fixtures_config):
    from app.services.artifact_loader import ArtifactLoader

    dup_dir = tmp_path / "dup_outputs"
    dup_dir.mkdir()
    df = pd.read_csv(fixtures_config.output_dir / "hotspot_clusters.csv")
    dup_row = df.iloc[[0]].copy()
    pd.concat([df, dup_row], ignore_index=True).to_csv(dup_dir / "hotspot_clusters.csv", index=False)

    from dataclasses import replace
    cfg = replace(fixtures_config, output_dir=dup_dir)
    dup_loader = ArtifactLoader(cfg)

    merged, diagnostics = dup_loader.merged_hotspots()
    assert len(merged) == 4  # deduped back down
    assert diagnostics["hotspot_clusters"].duplicate_keys == 1


def test_malformed_json_raises_artifact_error(tmp_path, fixtures_config):
    from dataclasses import replace
    from app.services.artifact_loader import ArtifactLoader

    bad_dir = tmp_path / "bad_outputs"
    bad_dir.mkdir()
    (bad_dir / "temporal_audit.json").write_text("{not valid json")
    cfg = replace(fixtures_config, output_dir=bad_dir)
    bad_loader = ArtifactLoader(cfg)

    with pytest.raises(ArtifactError) as exc_info:
        bad_loader.read_json("temporal_audit", required=True)
    assert exc_info.value.code == "MALFORMED_ARTIFACT"

