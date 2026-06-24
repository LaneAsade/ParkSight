# ParkSight AI — Development Guide

## Setup

```bash
# Clone and enter
git clone <repo> && cd parksight-ai

# Python environment (3.11+)
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]

# Frontend
cd frontend && npm install
```

## Running locally

```bash
# Pipeline
parksight --input data/samples/sample_violations.csv --output outputs --skip-external-apis

# Backend (from repo root)
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm run dev
```

## Running tests

```bash
# Backend tests (requires parksight installed)
cd backend && pytest tests/ -v

# Pipeline tests
pytest tests/pipeline/ -v
```

## Secrets

Copy `.env.example` → `.env` and fill in:
- `GOOGLE_MAPS_API_KEY` — for real traffic probe data (optional)
- `MAPPLS_ACCESS_TOKEN` + `MAPPLS_CLIENT_ID` — for Mappls routing (optional)

Without API keys, all stages run offline with `SPEC_ONLY` labels.

## Evidence labels

Every function that adds a data claim must set `validation_status` to `REAL_DATA`, `PARTIAL`, `MODELED`, or `SPEC_ONLY`. Never upgrade a label downstream.

## Adding a new pipeline stage

1. Create `parksight/my_stage.py`.
2. Add the stage call to `parksight/pipeline.py` inside `_run_stage()`.
3. Add a new `ARTIFACT_PATTERN` to `backend/app/services/artifact_loader.py` if you write a new artifact.
4. Add router + service to `backend/app/routers/` and `backend/app/services/` if needed.
5. Wire into `frontend/src/api/` and `frontend/src/hooks/` for UI consumption.
