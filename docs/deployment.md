# ParkSight AI — Deployment Guide

## Docker Compose (recommended)

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop
docker-compose down
```

The backend is available at `http://localhost:8000`, the frontend at `http://localhost:5173`.

## Manual deployment

### Backend

```bash
cd backend
pip install -r requirements.txt
pip install -e ..  # install parksight package from repo root
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run build
# Serve dist/ with nginx or any static server
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PARKSIGHT_OUTPUT_DIR` | `../outputs` | Pipeline artifact directory |
| `PARKSIGHT_SETTINGS_PATH` | `../config/settings.yaml` | Settings file |
| `PARKSIGHT_INPUT_CSV` | `../data/raw/violations.csv` | Input violations CSV |
| `PARKSIGHT_DEFAULT_TEAMS` | `10` | Default patrol teams for /api/overview |
| `PARKSIGHT_CACHE_ENABLED` | `true` | Cache artifacts in memory (mtime-based) |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Allowed CORS origin |
| `GOOGLE_MAPS_API_KEY` | — | Traffic enrichment |
| `MAPPLS_ACCESS_TOKEN` | — | Mappls routing |

## Production notes

- Run the pipeline as a cron job or triggered task; the backend reads immutable artifact files.
- Mount `outputs/` as a read-only volume in the backend container.
- Set `FRONTEND_ORIGIN` to your deployed frontend domain.
- Use a reverse proxy (nginx) to serve both frontend and backend under the same domain.
