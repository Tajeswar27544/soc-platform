# SOC Platform — Backend

## Overview
Python-based backend for the SOC Monitoring Platform. Ingests Suricata eve.json alerts in real time, enriches them with GeoIP data, stores them in SQLite, and exposes a FastAPI REST API for the React dashboard.

## Quick Start

```bash
cd backend/

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (see below)
export EVE_JSON_PATH="/var/log/suricata/eve.json"
export GEOIP_DB_PATH="./GeoLite2-City.mmdb"
export MAXMIND_LICENSE_KEY="your-maxmind-license-key"  # enables auto-download of GeoLite2
export SMTP_EMAIL="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"

# Run the API server (includes log monitor thread)
python -m api.main
```

The server starts on `http://0.0.0.0:8000`. API docs at `/docs`.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `EVE_JSON_PATH` | `/var/log/suricata/eve.json` | Path to Suricata eve.json |
| `GEOIP_DB_PATH` | `./GeoLite2-City.mmdb` | Path to MaxMind GeoLite2-City database |
| `MAXMIND_LICENSE_KEY` | *(empty)* | MaxMind license key — if set, the backend auto-downloads GeoLite2 on first use |
| `SQLITE_DB_PATH` | `./data/soc_alerts.db` | SQLite database file |
| `SMTP_EMAIL` | *(empty)* | Gmail address for alerts |
| `SMTP_PASSWORD` | *(empty)* | Gmail App Password |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server host |
| `SMTP_PORT` | `465` | SMTP SSL port |
| `ALERT_RECIPIENT` | Same as SMTP_EMAIL | Alert email recipient |
| `EMAIL_SEVERITY_THRESHOLD` | `2` | Max severity to trigger email |
| `API_HOST` | `0.0.0.0` | API bind address |
| `API_PORT` | `8000` | API port |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated CORS origins |
| `MONITOR_POLL_INTERVAL` | `1.0` | Seconds between eve.json reads |
| `MONITOR_BATCH_SIZE` | `50` | Alerts per DB batch insert |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/alerts` | All alerts (paginated) |
| GET | `/alerts/latest` | Most recent alerts |
| GET | `/alerts/severity/{level}` | Filter by severity |
| GET | `/alerts/stats` | Dashboard statistics |
| GET | `/alerts/top-ips` | Top source IPs |
| GET | `/alerts/severity-distribution` | Severity breakdown |
| GET | `/alerts/timeline` | Hourly timeline |
| GET | `/alerts/countries` | Country distribution |
| GET | `/alerts/top-signatures` | Top triggered signatures |

## Running Monitor Standalone

If you prefer running the monitor separately from the API:

```bash
# Terminal 1 — Monitor only
python -m monitor.log_monitor

# Terminal 2 — API only (comment out monitor thread in lifespan)
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Downloading GeoLite2 manually

If you prefer to fetch the database yourself (or need to refresh it monthly), run:

```bash
cd backend
MAXMIND_LICENSE_KEY=your-key python -m monitor.geoip --output GeoLite2-City.mmdb
```

The backend will also attempt this automatically on first startup when `MAXMIND_LICENSE_KEY` is set.
