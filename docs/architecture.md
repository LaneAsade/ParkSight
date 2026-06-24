# ParkSight AI — Architecture

## Overview

```
violations.csv
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  parksight (Python package)                             │
│                                                         │
│  data_loader → bias_audit → hotspot_detection           │
│       → nonjunction_hotspots → risk_scoring             │
│       → spatial_validation → traffic_enrichment         │
│       → capacity_impact → patrol_optimization           │
│       → evidence → reporting                            │
│                                                         │
│  Artifacts written to: outputs/                         │
└─────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  backend (FastAPI)                                      │
│                                                         │
│  ArtifactLoader reads outputs/ and merges artifacts     │
│  into unified hotspot records. Routers expose:          │
│  /api/overview, /api/hotspots, /api/congestion,         │
│  /api/patrol, /api/forecast, /api/economic,             │
│  /api/evidence, /api/scenarios, /api/copilot,           │
│  /api/system/status                                     │
└─────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  frontend (Vite + React)                                │
│                                                         │
│  Dashboard pages consume the backend API via            │
│  src/api/ (client.js + domain modules) and              │
│  src/hooks/ (useFetch, useHotspots, usePatrol, …)       │
└─────────────────────────────────────────────────────────┘
```

## Evidence labelling

Every figure produced by the pipeline carries one of four labels:

| Label | Meaning |
|-------|---------|
| `REAL_DATA` | Directly observed from the violations CSV or a live external API. |
| `PARTIAL` | Mix of real data and spec/modelled values. |
| `MODELED` | Computed from real data via a calibrated model (e.g. economic impact). |
| `SPEC_ONLY` | No real data available; uses spec-defined default or estimation. |

Labels are never upgraded downstream — a SPEC_ONLY claim cannot become REAL_DATA by further computation.

## Key design decisions

- **Offline-first**: the pipeline runs completely without network access (`--skip-external-apis`). All API-dependent stages fall back to `SPEC_ONLY` values.
- **Immutable outputs**: the pipeline writes to `outputs/` and never reads back its own outputs within a single run.
- **No client-side data synthesis**: the frontend never generates values — it only renders what the backend computes from pipeline artifacts.
- **Real solver**: the patrol optimisation uses `scipy.optimize.milp` (branch-and-bound), with a greedy fallback. No simplified JS reimplementation.
