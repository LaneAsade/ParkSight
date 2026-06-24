# ParkSight AI — Frontend

A Vite + React enforcement console that renders the **actual artifacts** the
FastAPI backend reads from the `parksight` pipeline. It never generates
random data, synthetic forecasts, or hardcoded KPI values — every figure on
screen is fetched from `/api/*` and carries the evidence status
(`REAL_DATA` / `MODELED` / `PARTIAL` / `SPEC_ONLY`) the backend assigned it.

## Stack

- React 18 + React Router 6
- Vite 5
- Tailwind CSS 3
- Recharts (charts), lucide-react (icons)

## Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The dev server runs on `http://localhost:5173` and expects the backend at
`VITE_API_BASE_URL` (default `http://localhost:8000/api`).

## Structure

```text
src/
├── api/         one file per backend domain — thin fetch wrappers, no logic
├── hooks/       useFetch/useMutation-based hooks that call api/
├── components/  reusable UI (EvidenceChip, RiskTierBadge, Layout, Panel…)
├── pages/       one page per nav item, composed from hooks + components
├── styles/      Tailwind entry + the provenance-chip design system
├── types/       JSDoc typedefs mirroring backend/app/schemas.py
└── utils/       shared formatters (fmtNumber, fmtPercent, fmtDate…)
```

## Design system

Every number that came from a pipeline artifact renders next to an
`EvidenceChip` naming its validation status. This is deliberate — the whole
point of the console is that nobody can mistake a `MODELED` projection for a
`REAL_DATA` measurement. See `src/styles/globals.css` for the chip styling
and `tailwind.config.js` for the `evidence`/`tier` color tokens.

## Build

```bash
npm run build   # outputs to dist/
npm run preview # serve the production build locally
```

## Tests

```bash
npm run test
```

No frontend test files are included yet (the original source did not ship
any); `vitest` is wired up and ready for them.

## Known limitations

- No map library is wired in; hotspot locations are shown as
  lat/lon plus a link out to OpenStreetMap rather than an embedded map.
- The Copilot page keeps its conversation history in memory only — it
  resets on page reload.
