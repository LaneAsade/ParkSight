# ParkSight AI — Backend

FastAPI service that reads the **actual artifacts produced by the `parksight`
pipeline** (CSV/JSON files in `outputs/`) and serves them to the React
dashboard. It never regenerates, fabricates, or randomizes data — every
number traces back to a pipeline artifact, and missing data is returned as
`null`, never backfilled.

## Layout

```
backend/
├── app/
│   ├── main.py              FastAPI app, CORS, gzip, exception handling
│   ├── config.py             Env-driven AppConfig (paths, CORS, cache)
│   ├── schemas.py             Pydantic response/request models
│   ├── dependencies.py         FastAPI DI providers
│   ├── routers/                One module per API area (thin — HTTP only)
│   └── services/                 Business logic, reads artifacts via artifact_loader
└── tests/                          pytest suite against tests/fixtures/
```

## Run locally

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # edit if your outputs/ or config/ live elsewhere
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for interactive Swagger docs.

## Configuration

All paths are environment-driven (see `.env.example`). Defaults assume the
backend is run from inside `backend/` with the rest of the repo as siblings:

| Variable | Default | Meaning |
|---|---|---|
| `PARKSIGHT_OUTPUT_DIR` | `../outputs` | Where pipeline artifacts live |
| `PARKSIGHT_SETTINGS_PATH` | `../config/settings.yaml` | Pipeline config (districts, weights, thresholds) |
| `PARKSIGHT_INPUT_CSV` | `../data/raw/violations.csv` | Metadata only — never re-read per request |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS allow-list (comma-separated) |
| `PARKSIGHT_DEFAULT_TEAMS` | `10` | Default patrol team count |

The patrol endpoints (`/api/patrol/current`, `/api/patrol/simulate`) import
the **real** `parksight.patrol_optimization.milp_assignment` solver as a
library — the API never reimplements the MILP in JavaScript or Python.

## Tests

```bash
cd backend
pytest tests/ -v
```

Tests run entirely against `tests/fixtures/` (a small, hand-built artifact
set), never against a live pipeline run.

## Artifact discovery

`services/artifact_loader.py` looks for canonical filenames (with tolerant
pattern matching) directly inside `PARKSIGHT_OUTPUT_DIR`, or inside the
newest timestamped run subdirectory if the pipeline writes one run per
folder. Required artifacts missing → HTTP 404 with a structured error body
(`{"error": {"code": "MISSING_ARTIFACT", ...}}`). Optional artifacts missing
→ the corresponding fields are `null`, never fabricated.
