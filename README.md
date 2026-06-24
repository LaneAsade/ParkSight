# ParkSight AI

**ParkSight AI detects illegal parking hotspots, validates their stability, enriches them with traffic and road-capacity intelligence, and recommends evidence-tagged enforcement priorities.**

---

## Problem Statement

Bengaluru's traffic police receive hundreds of illegal parking violation reports daily. Without a systematic way to identify persistent hotspots, patrol resources are allocated reactively rather than strategically. ParkSight AI transforms raw violation records into ranked, evidence-backed enforcement priorities — and serves them through a FastAPI backend and a React dashboard so operators can act on them directly.

---

## Features

- **Temporal audit** — detects adjudication backlogs and filename/date-range mismatches
- **Selection-bias audit** — quantifies approval bias across vehicle type, station, and hour
- **DBSCAN hotspot clustering** — groups junction violations into spatial clusters with bootstrap CI
- **Non-junction hotspot detection** — hex-grid analysis for mid-block violations
- **Transparent risk scoring** — weighted percentile rank formula (no black-box classifier)
- **Spatial stability validation** — leave-one-district-out Jaccard test
- **Traffic enrichment** — Google Distance Matrix API (8-direction route robustness + temporal probing)
- **Road capacity impact** — IRC:106-2010 obstruction model with Mappls / OSM / Google geometry
- **MILP patrol optimization** — assigns teams to shifts with CRITICAL-coverage guarantee
- **Evidence ledger** — every claim tagged `REAL_DATA`, `MODELED`, or `SPEC_ONLY`
- **FastAPI backend** — serves pipeline outputs to the dashboard, including scenario/copilot endpoints
- **React + Vite dashboard** — overview, hotspots, congestion, patrol, forecast, economic, evidence, scenarios, and copilot views

---

## Repository layout

```
parksight/        Python analytics package (pip-installable, the `parksight` CLI)
backend/          FastAPI API server (serves pipeline output artifacts to the frontend)
frontend/         Vite + React dashboard
config/           settings.yaml (pipeline constants, thresholds, weights)
data/             raw/, processed/, samples/
outputs/          pipeline run artifacts (CSV + JSON + executive_report.md)
scripts/          convenience run/setup scripts (pipeline, backend, frontend)
tests/pipeline/   pipeline-level integration tests
docs/             architecture, API, schema, and evidence-model documentation
```

---

## Quick start

```bash
# 1. Install the Python package (creates the `parksight` CLI)
pip install -e .

# 2. Run the pipeline (offline, no API keys needed)
parksight --input data/raw/violations.csv --output outputs --skip-external-apis

# 3. Start the API
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000

# 4. Start the dashboard (separate terminal)
cd frontend && npm install && npm run dev
```

Or use the convenience scripts: `python scripts/run_pipeline.py`, `python scripts/run_backend.py`, `bash scripts/run_frontend.sh` (see `scripts/setup.sh` / `setup.ps1` for one-shot environment setup).

### CLI options

| Flag | Description | Default |
|------|-------------|---------|
| `--input` | Path to violations CSV | required |
| `--output` | Output directory | `outputs/` |
| `--google-api-key` | Google Maps API key | env var `GOOGLE_MAPS_API_KEY` |
| `--mappls-api-key` | Mappls API key | env var `MAPPLS_ACCESS_TOKEN` |
| `--skip-traffic` | Skip traffic enrichment | false |
| `--skip-external-apis` | Skip all external API calls | false |
| `--teams` | Number of patrol teams for MILP | 10 |

### Required API keys (optional — pipeline runs fully offline without them)

| Key | Purpose | Where to get |
|-----|---------|--------------|
| `GOOGLE_MAPS_API_KEY` | Distance Matrix, Roads, Places | [Google Cloud Console](https://console.cloud.google.com/) |
| `MAPPLS_ACCESS_TOKEN` | Mappls Reverse Geocode, Nearby | [Mappls Developer](https://developer.mappls.com/) |
| `MAPPLS_CLIENT_ID` | Mappls OAuth | same |
| `MAPPLS_CLIENT_SECRET` | Mappls OAuth | same |

Set these in `.env` (copy from `.env.example`). The pipeline runs fully offline with `SPEC_ONLY` labels when keys are absent.

---

## Pipeline overview

| Stage | Module | Output artifact |
|-------|--------|-----------------|
| Load & validate | `data_loader.py` | `temporal_audit.json` |
| Bias audit | `bias_audit.py` | `bias_audit.json` |
| Junction aggregation | `hotspot_detection.py` | — |
| DBSCAN clustering | `hotspot_detection.py` | `hotspot_clusters.csv` |
| Non-junction hotspots | `nonjunction_hotspots.py` | `nonjunction_hotspots.csv` |
| Risk scoring | `risk_scoring.py` | `risk_scores.csv` |
| Spatial validation | `spatial_validation.py` | `spatial_stability.json` |
| Traffic enrichment | `traffic_enrichment.py` | `traffic_enrichment.csv` |
| Capacity impact | `capacity_impact.py` | `capacity_impact.csv` |
| Patrol optimisation | `patrol_optimization.py` | `patrol_plan.csv` |
| Evidence ledger | `evidence.py` | `evidence_ledger.csv` |
| Executive report | `reporting.py` | `executive_report.md` |

## Evidence labels

Every row in every output carries one of three labels:

| Label | Meaning |
|-------|---------|
| `REAL_DATA` | Derived directly from the input violations CSV or a live API response |
| `MODELED` | Computed from real data via a formula, model, or simulation (e.g. risk scores, ERCI) |
| `SPEC_ONLY` | Structural placeholder — the relevant API was unavailable or data was insufficient |

**Rule:** if an API call fails, the pipeline continues with `SPEC_ONLY` labels. It never backfills a failed API result with a fabricated number.

## Methodology summary

**Clustering:** DBSCAN (eps=0.5 km, min_samples=2) on junction-level aggregates, using latitude-corrected km-per-degree-of-longitude.

**Risk scoring:** Weighted percentile rank — violations (55%), at-junction % (25%), vehicle severity (10%), peak-hour % (10%). Pure formula on real counts, not a trained classifier.

**Spatial validation:** Leave-one-district-out re-scoring; Jaccard overlap of CRITICAL tier with full-city result.

**Traffic enrichment:** Google Distance Matrix API — 8 compass directions per hotspot, temporal grid (4 time slots × 2 day types).

**Road capacity:** IRC:106-2010 obstruction model × HCM lane factor × signal-delay factor. Real geometry from Mappls → OSM → Google → engineering fallback.

**Patrol optimization:** Mixed-Integer Linear Program (`scipy.optimize.milp`) — maximizes risk-weighted coverage under shift-cap constraints; auto-relaxes the CRITICAL-coverage constraint if `n_critical > n_teams`.

## Known limitations

1. **Parking violation data alone cannot prove congestion impact.** Violations indicate where enforcement occurred, not where traffic actually slowed.
2. **Traffic API data is observational**, not a controlled measurement of the counterfactual without parking.
3. **Capacity loss estimates are engineering estimates, not measured causal effects**, calibrated for typical Indian roads but not field-validated at these specific junctions.
4. **Economic benefit is modeled, not directly observed**, since no measured enforcement outcome exists in the source dataset to calibrate against.
5. **External APIs may be unavailable** in restricted environments; the pipeline runs fully offline and tags externally-dependent outputs `SPEC_ONLY` when connectivity or credentials are absent.
6. **District labels are synthetic** — rectangular lat/lon grid cells, not real Bengaluru police-zone or ward boundaries.
7. **Filename / date-range mismatches in source data** should be confirmed before trusting month-based trend claims at face value.

---

## Documentation

See `docs/` for architecture, API reference, data schema, and the evidence model in more depth.

## Environment

Copy `.env.example` to `.env` (both at the repo root and inside `backend/` and `frontend/`) and set the relevant variables — `PARKSIGHT_OUTPUT_DIR`, `PARKSIGHT_SETTINGS_PATH`, `PARKSIGHT_INPUT_CSV`, and optionally `GOOGLE_MAPS_API_KEY` / `MAPPLS_ACCESS_TOKEN` for real traffic enrichment.

## Tests

```bash
# Pipeline package tests
pytest tests/pipeline -v

# Backend API tests
cd backend && pytest tests/ -v
```

## License

MIT — see `LICENSE`.
