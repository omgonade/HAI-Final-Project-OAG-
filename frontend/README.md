# Frontend: Adult Census Income Predictor

Next.js (App Router, TypeScript, Tailwind) interface for the fairness-mitigated income
prediction model. Three pages:

- **`/` — Predict**: input form built from the backend's `/feature-schema`, submits to
  `/predict`, shows the served (feature elimination) prediction alongside what the
  unmitigated baseline model would have said for the same input.
- **`/about` — Model Card**: scope, limitations, and known bias sources, from
  `/metadata`.
- **`/fairness` — Fairness Dashboard**: overall performance and fairness metrics
  (before/after mitigation, by-sex subgroup breakdown), from `/metrics`.

## Local run

```bash
cd frontend
npm install
cp .env.example .env.local   # point NEXT_PUBLIC_API_URL at your running backend
npm run dev
```

Requires the backend running (see `../backend/README.md`) — the pages fetch live data
from it, there's nothing hardcoded.

## Deploying (Vercel)

- New Project, pointed at this repo, **Root Directory: `frontend`**.
- Env var: `NEXT_PUBLIC_API_URL=https://<your-render-backend>.onrender.com`
