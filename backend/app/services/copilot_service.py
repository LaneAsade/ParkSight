"""
app/services/copilot_service.py — Deterministic, data-grounded copilot.

No external LLM call. Every answer is derived from the loaded artifacts and
returns the supporting records and evidence labels that back it up. Unknown
queries get an honest "I can't answer that yet" rather than an invented one.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from .artifact_loader import ArtifactLoader
from .congestion_service import congestion_by_district
from .patrol_service import simulate_patrol

_TEAM_DELTA_RE = re.compile(r"(\d+)\s*(more|additional)?\s*(patrol\s*)?teams?")


def answer_query(loader: ArtifactLoader, query: str) -> Dict[str, Any]:
    q = query.lower().strip()
    merged, _ = loader.merged_hotspots()

    if "highest" in q and "risk" in q:
        top = merged.sort_values("risk_score", ascending=False).iloc[0]
        return {
            "answer": (
                f"{top['top_junction']} ({top['police_station']}) is the highest-risk hotspot — "
                f"score {top['risk_score']}, tier {top['risk_tier']}. It logged {int(top['violations'])} "
                f"violations with {top.get('pct_at_junction')}% at-junction and {top.get('pct_peak_hour')}% "
                f"in peak hours."
            ),
            "supporting_data": [top.replace({float("nan"): None}).to_dict()],
            "evidence_statuses": ["REAL_DATA", "MODELED"],
            "limitations": ["risk_score is a transparent percentile-rank formula, not a trained classifier."],
        }

    team_match = _TEAM_DELTA_RE.search(q)
    if team_match and ("patrol" in q or "team" in q):
        n = int(team_match.group(1))
        base_teams = 10
        before = simulate_patrol(loader, merged, base_teams)
        after = simulate_patrol(loader, merged, base_teams + n)
        return {
            "answer": (
                f"Adding {n} teams ({base_teams} → {base_teams + n}) moves CRITICAL coverage from "
                f"{before['critical_covered']}/{before['critical_total']} to "
                f"{after['critical_covered']}/{after['critical_total']}, and overall hotspot coverage "
                f"from {before['overall_coverage_pct']}% to {after['overall_coverage_pct']}%."
            ),
            "supporting_data": [
                {"teams": base_teams, **{k: before[k] for k in ("critical_covered", "critical_total", "overall_coverage_pct")}},
                {"teams": base_teams + n, **{k: after[k] for k in ("critical_covered", "critical_total", "overall_coverage_pct")}},
            ],
            "evidence_statuses": [before["validation_status"], after["validation_status"]],
            "limitations": ["Patrol simulation uses the actual MILP solver; coverage projections are MODELED, not measured."],
        }

    by_district = congestion_by_district(loader)
    for entry in by_district:
        first_word = entry["district"].lower().split(" ")[0]
        if first_word in q and "congestion" in q:
            return {
                "answer": (
                    f"{entry['district']} has {entry['n_hotspots']} tracked hotspot(s) with a mean "
                    f"congestion index of {entry['mean_congestion_index']}×."
                ),
                "supporting_data": [entry],
                "evidence_statuses": ["PARTIAL"],
                "limitations": ["Congestion index reflects only hotspots with successful traffic API probes."],
            }

    junction_match = merged[merged["top_junction"].str.lower().str.contains(
        re.escape(q.split(" ")[0]), na=False
    )] if q else merged.iloc[0:0]
    if not junction_match.empty:
        c = junction_match.iloc[0]
        return {
            "answer": (
                f"{c['top_junction']} sits in tier {c['risk_tier']} (score {c['risk_score']}). "
                f"Drivers: {int(c['violations'])} violations, {c.get('pct_at_junction')}% at-junction "
                f"concentration, top vehicle {c.get('top_vehicle')}. Congestion index reads "
                f"{c.get('congestion_index')}× free-flow, tagged {c.get('traffic_validation_status') or c.get('traffic_validation')}."
            ),
            "supporting_data": [c.replace({float("nan"): None}).to_dict()],
            "evidence_statuses": ["REAL_DATA", "MODELED"],
            "limitations": [],
        }

    return {
        "answer": (
            "I can answer questions about a specific junction, the highest-risk hotspot, district "
            "congestion, or patrol team what-ifs. Try one of the example prompts."
        ),
        "supporting_data": [],
        "evidence_statuses": [],
        "limitations": ["Query did not match a known pattern — this copilot does not call an external LLM."],
    }

