# SOC Monitoring Platform

> Lightweight Suricata alert ingestion + GeoIP enrichment + FastAPI + React dashboard, tuned for low-resource hosts (8 GB RAM friendly).

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi) ![React](https://img.shields.io/badge/React-18-61DAFB?logo=react) ![License](https://img.shields.io/badge/License-MIT-green)

## Architecture

```
Network Traffic
    → Suricata IDS
    → eve.json (JSON alert log)
    → Python Log Monitor Service (tail -f behaviour)
    → GeoIP Enrichment (MaxMind GeoLite2-City)
    → SQLite Database (WAL mode, indexed)
    → FastAPI REST API (Pydantic models, CORS)
    → React Dashboard (Vite + Tailwind + Recharts)
```

## Features
- Real-time Suricata `eve.json` ingestion with rotation handling
- GeoIP enrichment (MaxMind GeoLite2-City, auto-download with `MAXMIND_LICENSE_KEY`)
- SQLite storage (WAL mode, indexed) + cached analytics endpoints
- FastAPI REST API with health and alert endpoints
- React dashboard (Vite + Tailwind + Recharts), 5s polling
- Optional Gmail SMTP alerts for severity ≤ 2

## Requirements
- Python 3.10+
- Node.js 18+
- Suricata writing to `eve.json` (optional: use `backend/sample_eve.json` for testing)
- MaxMind license key (free) if you want GeoLite2 auto-download

## Quick Start (one command)

```bash
python3 setup.py
```

The interactive script will:
- Create a Python venv, install backend deps
- Install frontend deps
- Offer Suricata interface setup (optional)
- Download GeoLite2 if `MAXMIND_LICENSE_KEY` is set
- Start backend API (8000) and frontend dev server (5173)

## Manual Setup (if you prefer)

**Backend**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export EVE_JSON_PATH=/var/log/suricata/eve.json
export MAXMIND_LICENSE_KEY=your-key   # enables auto-download
python -m monitor.geoip --output GeoLite2-City.mmdb  # optional, downloads DB
python -m api.main
```

**Frontend**
```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Dashboard: http://localhost:5173 (proxied to backend at 8000).

## Project Structure

```
soc-platform/
├── backend/               # FastAPI + monitor + SQLite
│   ├── monitor/           # config, database, geoip, email, log_monitor
│   ├── api/               # FastAPI app and schemas
│   ├── data/              # SQLite DB lives here
│   └── README_backend.md  # backend details
├── frontend/              # React dashboard (Vite + Tailwind)
│   └── README_frontend.md
├── setup.py               # Interactive installer
├── setup_cli.py           # shim for legacy invocation
├── setup_guide.md         # extended install/deploy notes
└── README.md
```

## API (summary)
- `/health` — liveness + geoip/email status
- `/alerts`, `/alerts/latest`, `/alerts/severity/{level}`, `/alerts/after/{last_id}`
- Analytics: `/alerts/stats`, `/alerts/top-ips`, `/alerts/severity-distribution`, `/alerts/timeline`, `/alerts/countries`, `/alerts/top-signatures`

## GeoIP Notes
- Place `backend/GeoLite2-City.mmdb` manually **or** set `MAXMIND_LICENSE_KEY` and let `monitor.geoip` download it on first use.
- Example manual fetch: `cd backend && MAXMIND_LICENSE_KEY=your-key ./venv/bin/python -m monitor.geoip --output GeoLite2-City.mmdb`

## Production Hints
- Run Suricata as a service and point `EVE_JSON_PATH` to its `eve.json`.
- Keep a single uvicorn worker (SQLite is single-writer); use systemd to supervise.
- Serve frontend as static assets via Nginx/Caddy; point it to the API host.
- Rotate and back up `backend/data/soc_alerts.db` periodically.

## License
MIT
