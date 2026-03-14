# SOC Monitoring Platform

> A lightweight, production-quality Network Intrusion Detection Monitoring Platform designed for resource-constrained environments.

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

## Project Structure

```
soc-platform/
│
├── backend/
│   ├── monitor/
│   │   ├── __init__.py
│   │   ├── config.py          # Centralised configuration
│   │   ├── database.py        # SQLite schema, CRUD, analytics
│   │   ├── geoip.py           # MaxMind GeoIP lookups
│   │   ├── email_alert.py     # Gmail SMTP alert emails
│   │   └── log_monitor.py     # Real-time eve.json tail service
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app with all endpoints
│   │   └── models.py          # Pydantic response schemas
│   │
│   ├── data/                  # Auto-created, contains SQLite DB
│   ├── requirements.txt
│   └── README_backend.md
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── MetricCard.jsx
│   │   │   ├── SeverityChart.jsx
│   │   │   ├── TimelineChart.jsx
│   │   │   ├── TopIPsChart.jsx
│   │   │   ├── SignatureTable.jsx
│   │   │   ├── CountryTable.jsx
│   │   │   ├── LiveFeed.jsx
│   │   │   ├── LoadingSpinner.jsx
│   │   │   └── ErrorBanner.jsx
│   │   ├── pages/
│   │   │   └── Dashboard.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   │
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── README_frontend.md
│
├── setup_guide.md             # Complete installation & deployment guide
└── README.md                  # This file
```

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/soc-platform.git
cd soc-platform
```


### 2. Automated Setup (Recommended)

Run the interactive setup script from the project root:

```bash
python3 setup_cli.py
```

This script will:
- Set up the backend Python environment and dependencies
- Set up the frontend Node/React environment
- Guide you through GeoIP database download
- Detect and configure Suricata (IDS) if installed
- Help configure email alerts

> **Suricata:** If Suricata is not installed, the script will prompt you to install it. Suricata is required for live log monitoring. Install with:
> ```bash
> sudo apt update && sudo apt install suricata
> ```
> Then re-run the setup script to auto-configure Suricata.

> **GeoIP:** The script will guide you to download the free GeoLite2-City database from [MaxMind](https://www.maxmind.com/en/geolite2/signup) and place it in `backend/`. Country lookups return `Unknown` if omitted.

> **Email Alerts:** The script will help you configure Gmail SMTP for high-severity alert emails.

After setup, follow the script's instructions to start backend and frontend servers.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/alerts` | All alerts (paginated) |
| `GET` | `/alerts/latest` | Most recent alerts |
| `GET` | `/alerts/severity/{level}` | Filter by severity (1-4) |
| `GET` | `/alerts/stats` | Dashboard aggregate stats |
| `GET` | `/alerts/top-ips` | Top source IPs |
| `GET` | `/alerts/severity-distribution` | Severity breakdown |
| `GET` | `/alerts/timeline` | Hourly counts (24h) |
| `GET` | `/alerts/countries` | Country distribution |
| `GET` | `/alerts/top-signatures` | Most triggered signatures |

## Key Features

- **Real-time log monitoring** — tail -f behaviour, handles log rotation
- **GeoIP enrichment** — country resolution for attacker IPs
- **Email alerts** — automatic Gmail notification for severity ≤ 2
- **SQLite with WAL** — concurrent read/write, indexed queries
- **Auto-refresh dashboard** — 5-second polling, live feed panel
- **Dark SOC theme** — professional grid layout with Recharts visualizations
- **Low resource usage** — no ELK stack, no heavy databases, ~200 MB RAM total

## Technology Stack

| Layer | Technology |
|---|---|
| IDS Engine | Suricata |
| Backend | Python 3.10+, FastAPI, SQLite, geoip2 |
| Frontend | React 18, Vite, Tailwind CSS, Recharts |
| Email | smtplib (Gmail SMTP SSL) |
| Deployment | systemd, Nginx (optional) |

---

## Security Explanation

### Suricata Severity Logic

Suricata assigns severity levels to alerts based on rule metadata:

| Severity | Meaning | Examples |
|---|---|---|
| **1** | Critical / High | Active exploitation, malware C2 communication, known CVE exploits |
| **2** | Medium-High | Suspicious activity, policy violations, potential recon |
| **3** | Informational | Low confidence matches, generic protocol anomalies |
| **4** | Not suspicious | Purely informational, DNS lookups to known domains |

### Why Severity ≤ 2 Triggers Email

Severity 1 and 2 alerts represent **actionable threats** that require immediate analyst attention:

- **Severity 1**: An active attack is likely in progress — malware callbacks, exploit attempts, data exfiltration. These need immediate investigation and potential incident response.
- **Severity 2**: Suspicious behaviour that may indicate reconnaissance, policy violations, or early-stage attacks. These warrant rapid triage.

Severity 3-4 alerts generate too much noise for email notifications. They are still stored and visible on the dashboard for pattern analysis, but emailing on every low-confidence match would cause **alert fatigue** — analysts would start ignoring all emails, defeating the purpose of notifications.

### Signature-Based IDS Limitations

Suricata is a **signature-based** IDS, which means:

**Strengths:**
- Very fast detection of **known** attack patterns
- Low false positive rate for well-maintained rule sets
- Minimal CPU overhead — pattern matching is O(n) with Aho-Corasick
- Community rule sets (ET Open, ET Pro) cover thousands of known threats

**Weaknesses:**
- **Zero-day attacks** will not be detected — no signature exists yet
- **Encrypted traffic** (TLS 1.3) cannot be inspected without TLS interception
- **Polymorphic malware** can evade static signatures
- **Evasion techniques** (fragmentation, encoding) can bypass simple rules
- Rule sets must be **regularly updated** to remain effective

**Mitigation strategies:**
- Combine with anomaly-based detection (Zeek, ML-based tools) for defense in depth
- Run `suricata-update` daily via cron for latest rules
- Monitor for unusual traffic volumes even without specific signature matches
- Use TLS inspection proxies for encrypted traffic visibility where legally permissible

### False Positive Handling

False positives are inevitable with any IDS. Strategies for this platform:

1. **Dashboard triage**: The severity distribution chart helps analysts see if low-severity alerts dominate
2. **Signature analysis**: The "Most Triggered Signatures" table reveals noisy rules
3. **IP analysis**: The "Top Source IPs" chart identifies if internal IPs trigger alerts (common false positive source)
4. **Rule tuning**: Suppress or threshold noisy rules in `/etc/suricata/threshold.config`:
   ```
   suppress gen_id 1, sig_id 2100498, track by_src, ip 192.168.1.0/24
   threshold gen_id 1, sig_id 2100498, type limit, track by_src, count 1, seconds 3600
   ```
5. **Category filtering**: Use the severity filter endpoint to focus analyst time on high-confidence alerts

### Performance Considerations for 8 GB RAM

This platform is specifically optimised for low-memory environments:

| Component | Memory Usage | Optimization |
|---|---|---|
| Suricata | ~500-800 MB | Default config, `max-pending-packets: 1024` |
| Python backend | ~80-120 MB | Single process, no thread pool |
| SQLite | ~8 MB cache | `PRAGMA cache_size=-8000` |
| GeoIP reader | ~60 MB | Memory-mapped file, shared across lookups |
| React frontend | Browser only | No server-side rendering |
| **Total server-side** | **~700 MB - 1 GB** | Leaves 7 GB for OS + Suricata |

Key optimizations:
- **SQLite WAL mode**: Allows concurrent reads (API) while writing (monitor) without locking
- **Batch inserts**: Reduces I/O syscalls by grouping alerts
- **Single uvicorn worker**: No process duplication — SQLite is single-writer anyway
- **Polling instead of WebSocket**: Lower server overhead, no persistent connections
- **No ELK stack**: Elasticsearch alone would consume 2-4 GB minimum

### Why ELK Stack Was Avoided

The ELK (Elasticsearch + Logstash + Kibana) stack is the industry standard for log analysis but is **entirely inappropriate** for an 8 GB RAM system:

| Component | Minimum RAM | Issue |
|---|---|---|
| Elasticsearch | 2 GB (JVM heap) | Java-based, needs 4-8 GB for production |
| Logstash | 1 GB (JVM heap) | Another Java process with heavy overhead |
| Kibana | 500 MB | Node.js process, moderate overhead |
| **Total** | **3.5+ GB** | Would consume nearly half of available RAM |

Additional ELK concerns for this use case:
- **Disk I/O**: Elasticsearch creates Lucene indexes that thrash slow disks
- **Complexity**: Three separate services to configure, monitor, and update
- **Startup time**: JVM warm-up takes 30-60 seconds
- **Overkill**: For a single data source (Suricata), SQLite queries are sufficient

Our stack (SQLite + FastAPI + React) uses **~200 MB total** vs ELK's **3.5+ GB** while providing all the dashboard functionality needed for a Mini SOC.

---

## License

MIT
