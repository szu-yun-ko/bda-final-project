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
