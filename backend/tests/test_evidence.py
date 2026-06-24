"""tests/test_evidence.py"""

from __future__ import annotations

from app.services.evidence_service import evidence_summary, list_evidence


def test_evidence_summary_counts_by_status(loader):
    summary = evidence_summary(loader)
    assert summary["total"] == 5
    assert summary["counts"]["REAL_DATA"] == 3
    assert summary["counts"]["SPEC_ONLY"] == 1
    assert summary["counts"]["MODELED"] == 1


def test_evidence_filters_by_status_never_upgrades_label(loader):
    items, total = list_evidence(loader, status="SPEC_ONLY")
    assert total == 1
    assert items[0]["status"] == "SPEC_ONLY"


def test_evidence_search_matches_claim_text(loader):
    items, total = list_evidence(loader, search="congestion")
    assert total == 1
    assert "congestion" in items[0]["claim"].lower()


def test_evidence_pagination(loader):
    items, total = list_evidence(loader, limit=2, offset=0)
    assert total == 5
    assert len(items) == 2
    items2, _ = list_evidence(loader, limit=2, offset=2)
    assert len(items2) == 2
    assert items != items2

