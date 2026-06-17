# EV Routing Data Pipeline (Taiwan) — Phases 1–4

ABRP-style EV route planner for Taiwan with TDX data, traffic-aware ETA, and a TypeScript web UI.

## Install backend

```bash
/Users/szu-yunko/anaconda3/bin/python -m pip install -r requirements.txt
```

## Install + build frontend (TypeScript)

```bash
cd frontend
npm install
npm run build
cd ..
```

## Run web app (ABRP-style UI)

```bash
/Users/szu-yunko/anaconda3/bin/python -m flask --app src.web_app run --debug --port 5001
```

Open `http://127.0.0.1:5001`

> **macOS note:** Port 5000 is used by AirPlay Receiver and returns HTTP 403 in Chrome. Use **5001** instead, or disable AirPlay in System Settings → General → AirDrop & Handoff.

### Dev mode (hot reload UI)

Terminal 1:
```bash
/Users/szu-yunko/anaconda3/bin/python -m flask --app src.web_app run --debug --port 5001
```

Terminal 2:
```bash
cd frontend && npm run dev
```

Open `http://127.0.0.1:5173` (proxies `/api` to Flask)

## CLI

```bash
/Users/szu-yunko/anaconda3/bin/python -m src.main --mode tdx --city Taipei --soc-now-pct 90
```

## Features

- **TDX ingestion**: charging stations, live connector status, connector specs
- **Traffic-aware ETA**: freeway VD speeds + city section congestion (per-leg factors)
- **Route planning**: min total trip time, SOC + connector constraints, 0–2 charging stops
- **Web UI**: Mapbox map + step-by-step trip/vehicle config + itinerary results, TypeScript + React

### Mapbox token (frontend)

```bash
cp frontend/.env.example frontend/.env
# Set VITE_MAPBOX_TOKEN from https://account.mapbox.com/access-tokens/
```

## TDX credentials

Copy `.env.example` → `.env` and set `TDX_CLIENT_ID`, `TDX_CLIENT_SECRET`.

## Deploy (Render + Docker)

The app ships as a single Docker image: Flask API + built React UI.

### 1. Push to GitHub

Repo should already be on GitHub (`szu-yun-ko/bda-final-project`).

### 2. Create a Render web service

1. Go to [render.com](https://render.com) → **New** → **Web Service**
2. Connect the GitHub repo
3. Set **Runtime** to **Docker**
4. Add environment variables:

| Variable | Required | Notes |
|----------|----------|-------|
| `TDX_CLIENT_ID` | Yes | From [TDX](https://tdx.transportdata.tw/) |
| `TDX_CLIENT_SECRET` | Yes | From TDX |
| `VITE_MAPBOX_TOKEN` | Yes | Public Mapbox token — used at **Docker build** time for the map |
| `TDX_BASE_URL` | No | Default in `render.yaml` |
| `TDX_TOKEN_URL` | No | Default in `render.yaml` |

5. Click **Deploy**

Or use the blueprint: **New** → **Blueprint** → point at `render.yaml` in the repo.

Health check: `GET /api/health`

### 3. Build locally (optional)

```bash
docker build \
  --build-arg VITE_MAPBOX_TOKEN=your_mapbox_token \
  -t bda-ev-route .

docker run --rm -p 8080:8080 \
  -e TDX_CLIENT_ID=... \
  -e TDX_CLIENT_SECRET=... \
  bda-ev-route
```

Open `http://localhost:8080`

### Notes

- **Free tier** may sleep after inactivity; first request can take ~30s to wake.
- Route planning calls TDX + OSRM and can take up to ~2 minutes; Render timeout is set to 180s in the Dockerfile.
- `data/cache/` is ephemeral on Render — responses may be slower on cold cache.
- Production image uses `requirements-prod.txt` (no osmnx); road geometry comes from the public OSRM API.
