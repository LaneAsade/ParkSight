# ParkSight AI — API Reference

Base URL: `http://localhost:8000/api`

## System

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/system/status` | Pipeline status, artifact manifest, API key availability |
| GET | `/system/runs` | List available pipeline run directories |
| GET | `/system/config` | Settings: districts, weights, thresholds, shifts |
| POST | `/system/reload` | Clear in-memory artifact cache |

## Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/overview` | Aggregated KPIs: violation counts, hotspot summary, congestion mean, patrol coverage |

## Hotspots

| Method | Path | Description |
|--------|------|-------------|
| GET | `/hotspots` | Paginated, filterable hotspot list (risk_tier, district, search, sort) |
| GET | `/hotspots/{cluster_id}` | Single hotspot detail with merged traffic + capacity data |
| GET | `/nonjunction-hotspots` | Non-junction hex-bin hotspots |

## Congestion

| Method | Path | Description |
|--------|------|-------------|
| GET | `/congestion/summary` | Mean delay, count by evidence status |
| GET | `/congestion/by-district` | Per-district congestion aggregates |
| GET | `/congestion/hotspots/{cluster_id}` | Congestion detail for one hotspot |
| GET | `/congestion/relationship` | Violations vs congestion scatter data |

## Patrol

| Method | Path | Description |
|--------|------|-------------|
| GET | `/patrol/current` | Current assignment with default team count |
| POST | `/patrol/simulate` | Simulate with `{"teams": N}` |

## Forecast

| Method | Path | Description |
|--------|------|-------------|
| GET | `/forecast/summary` | Global forecast metadata (months, MAE, caveats) |
| GET | `/forecast/{cluster_id}` | Per-cluster monthly series + 3-month persistence forecast |

## Economic

| Method | Path | Description |
|--------|------|-------------|
| GET | `/economic/assumptions` | Default economic parameters from settings.yaml |
| POST | `/economic/simulate` | Model impact with custom fuel cost / wage / effectiveness |

## Evidence

| Method | Path | Description |
|--------|------|-------------|
| GET | `/evidence` | Paginated evidence ledger (filterable by status, source, search) |
| GET | `/evidence/summary` | Count by evidence status |

## Scenarios

| Method | Path | Description |
|--------|------|-------------|
| POST | `/scenarios/simulate` | Baseline vs scenario comparison (patrol teams, thresholds, economic) |

## Copilot

| Method | Path | Description |
|--------|------|-------------|
| POST | `/copilot/query` | Natural language Q&A grounded in pipeline artifacts |

## Error format

All 404 errors return:
```json
{"detail": {"code": "MISSING_ARTIFACT", "message": "...", "artifact": "hotspot_clusters", "required": true}}
```
