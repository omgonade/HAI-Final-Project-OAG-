# Backend: Adult Census Income Predictor API

FastAPI service that serves predictions and fairness metrics from the models trained
by `../pipeline.py`. It does not train anything itself — it only loads the artifacts
in `artifacts/` (committed to git) and answers requests.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/metadata` | Model card content (task, scope, limitations, bias sources) |
| GET | `/metrics` | Performance + fairness metrics for all four models (baseline, feature elimination, reweighting, threshold optimization) |
| GET | `/feature-schema` | Categorical options + numeric ranges, for building the input form |
| POST | `/predict` | Body = raw feature values; returns both the served (feature elimination) prediction and the baseline model's prediction for comparison |

## Local run

```bash
cd backend
python -m venv venv
venv\Scripts\Activate.ps1      # Windows PowerShell; source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
uvicorn main:app --reload
```

Runs on `http://localhost:8000` by default. CORS allows `http://localhost:3000` and
`http://127.0.0.1:3000` by default (override with the `ALLOWED_ORIGINS` env var,
comma-separated, when the frontend is deployed elsewhere).

## Regenerating `artifacts/`

The `.joblib`/`.json` files in `artifacts/` are produced by running `pipeline.py` from
the repo root (`python pipeline.py`) — it trains the models and writes them there as
part of its normal run. Re-run it and commit the updated files whenever the model or
mitigation strategy changes; the backend itself never retrains anything.

## Deploying (Render)

- New Web Service, pointed at this repo, **Root Directory: `backend`**.
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Env var: `ALLOWED_ORIGINS=https://<your-vercel-app>.vercel.app`

No dataset download or training step is needed at deploy time — `artifacts/` is
already committed.
