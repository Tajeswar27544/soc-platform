"""
FastAPI REST API for the SOC Monitoring Platform.

Provides structured JSON endpoints consumed by the React dashboard.
All responses use Pydantic models for type-safe, documented schemas.

Runs the Suricata log monitor in a background thread so a single
process handles both ingestion and API serving — keeping resource
usage low on 8 GB RAM systems.
"""

import time
import threading
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Query, Path, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure config (and logging setup) is loaded first
from monitor.config import CORS_ORIGINS, API_HOST, API_PORT
from monitor.database import (
    init_db,
    fetch_all_alerts,
    fetch_latest_alerts,
    fetch_alerts_by_severity,
    fetch_stats,
    fetch_top_ips,
    fetch_severity_distribution,
    fetch_timeline,
    fetch_country_distribution,
    fetch_top_signatures,
    fetch_alerts_after,
    fetch_alert_count,
)
from monitor.log_monitor import run_monitor
from monitor.geoip import close_reader, is_geoip_loaded
from monitor.email_alert import is_email_configured

from api.models import (
    AlertListResponse,
    StatsResponse,
    TopIPsResponse,
    SeverityDistributionResponse,
    TimelineResponse,
    CountryDistributionResponse,
    TopSignaturesResponse,
    HealthResponse,
)

logger: logging.Logger = logging.getLogger("soc.api")

_startup_time: float = 0.0  # set in lifespan


# ---------------------------------------------------------------------------
# Lifespan: start monitor thread on startup, clean up on shutdown
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Simple TTL cache — reduces SQLite load on 5-second dashboard polling
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL: float = 4.0  # seconds — just under the 5s frontend poll interval


def _cached(key: str, fn, *args, **kwargs) -> Any:
    """Lightweight TTL cache wrapper for analytics queries."""
    now = time.monotonic()
    if key in _cache:
        ts, value = _cache[key]
        if now - ts < _CACHE_TTL:
            return value
    value = fn(*args, **kwargs)
    _cache[key] = (now, value)
    return value


def _monitor_watchdog() -> None:
    """Restart the log-monitor thread if it crashes unexpectedly.

    Checks every 30 seconds. A crashed monitor means silent data loss —
    this prevents hours-long gaps in alert ingestion going unnoticed.
    """
    while True:
        time.sleep(30)
        running = {t.name for t in threading.enumerate()}
        if "log-monitor" not in running:
            logger.warning("log-monitor thread is dead — restarting now")
            t = threading.Thread(target=run_monitor, daemon=True, name="log-monitor")
            t.start()
            logger.info("log-monitor thread restarted by watchdog")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler — startup & shutdown hooks."""
    global _startup_time
    _startup_time = time.monotonic()

    # Initialise database tables / indexes
    init_db()
    logger.info("Database initialised via lifespan startup")

    # Launch the log monitor in a daemon thread so it dies with the process
    monitor_thread = threading.Thread(target=run_monitor, daemon=True, name="log-monitor")
    monitor_thread.start()
    logger.info("Log monitor thread started")

    # Watchdog thread — auto-restarts monitor if it crashes silently
    watchdog = threading.Thread(target=_monitor_watchdog, daemon=True, name="monitor-watchdog")
    watchdog.start()
    logger.info("Monitor watchdog thread started")

    yield  # Application is running

    # Cleanup on shutdown
    close_reader()
    logger.info("Application shutdown complete")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SOC Monitoring Platform API",
    description="Lightweight Network Intrusion Detection System REST API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the React dev server and any configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler — prevents raw tracebacks leaking to API clients."""
    logger.error(
        "Unhandled exception on %s: %s", request.url.path, exc, exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "path": str(request.url.path)},
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """Health probe — reports liveness of all subsystems."""
    thread_names = {t.name for t in threading.enumerate()}
    monitor_alive = "log-monitor" in thread_names
    if not monitor_alive:
        logger.warning("Health check: log-monitor thread is NOT running")

    uptime = time.monotonic() - _startup_time if _startup_time else 0.0
    try:
        alert_count = fetch_alert_count()
    except Exception:
        alert_count = -1

    return HealthResponse(
        monitor_alive=monitor_alive,
        geoip_loaded=is_geoip_loaded(),
        email_configured=is_email_configured(),
        alert_count=alert_count,
        uptime_seconds=round(uptime, 1),
    )


# ---------------------------------------------------------------------------
# Alert endpoints
# ---------------------------------------------------------------------------

@app.get("/alerts", response_model=AlertListResponse, tags=["Alerts"])
async def get_alerts(
    limit: int = Query(default=500, ge=1, le=5000, description="Max alerts to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
) -> AlertListResponse:
    """Return paginated alerts, newest first."""
    alerts = fetch_all_alerts(limit=limit, offset=offset)
    return AlertListResponse(count=len(alerts), alerts=alerts)


@app.get("/alerts/latest", response_model=AlertListResponse, tags=["Alerts"])
async def get_latest_alerts(
    count: int = Query(default=20, ge=1, le=100, description="Number of recent alerts"),
) -> AlertListResponse:
    """Return the most recent N alerts for the live-feed panel."""
    alerts = fetch_latest_alerts(count=count)
    return AlertListResponse(count=len(alerts), alerts=alerts)


@app.get("/alerts/severity/{level}", response_model=AlertListResponse, tags=["Alerts"])
async def get_alerts_by_severity(
    level: int = Path(ge=1, le=4, description="Suricata severity level (1-4)"),
    limit: int = Query(default=200, ge=1, le=2000),
) -> AlertListResponse:
    """Return alerts filtered by a specific severity level."""
    alerts = fetch_alerts_by_severity(level=level, limit=limit)
    return AlertListResponse(count=len(alerts), alerts=alerts)


@app.get("/alerts/after/{last_id}", response_model=AlertListResponse, tags=["Alerts"])
async def get_alerts_after(
    last_id: int = Path(ge=0, description="Return alerts with id greater than this value"),
    limit: int = Query(default=200, ge=1, le=2000),
) -> AlertListResponse:
    """Incremental fetch — return only alerts newer than last_id.

    The frontend tracks the highest alert id it has seen and sends it here
    to receive only new rows.  This dramatically reduces payload size and
    SQLite read pressure compared to re-fetching the full alert list.
    """
    alerts = fetch_alerts_after(last_id=last_id, limit=limit)
    return AlertListResponse(count=len(alerts), alerts=alerts)


# ---------------------------------------------------------------------------
# Analytics endpoints
# ---------------------------------------------------------------------------

@app.get("/alerts/stats", response_model=StatsResponse, tags=["Analytics"])
async def get_stats() -> StatsResponse:
    """Return aggregate statistics for dashboard metric cards (TTL-cached)."""
    try:
        stats = _cached("stats", fetch_stats)
        return StatsResponse(**stats)
    except Exception as exc:
        logger.error("fetch_stats failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve stats") from exc


@app.get("/alerts/top-ips", response_model=TopIPsResponse, tags=["Analytics"])
async def get_top_ips(
    limit: int = Query(default=10, ge=1, le=50),
) -> TopIPsResponse:
    """Return top N source IPs by alert frequency (TTL-cached)."""
    try:
        rows = _cached(f"top_ips_{limit}", fetch_top_ips, limit)
        return TopIPsResponse(top_ips=rows)
    except Exception as exc:
        logger.error("fetch_top_ips failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve top IPs") from exc


@app.get("/alerts/severity-distribution", response_model=SeverityDistributionResponse, tags=["Analytics"])
async def get_severity_distribution() -> SeverityDistributionResponse:
    """Return alert counts grouped by severity level (TTL-cached)."""
    try:
        rows = _cached("sev_dist", fetch_severity_distribution)
        return SeverityDistributionResponse(distribution=rows)
    except Exception as exc:
        logger.error("fetch_severity_distribution failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve severity distribution") from exc


@app.get("/alerts/timeline", response_model=TimelineResponse, tags=["Analytics"])
async def get_timeline(
    hours: int = Query(default=24, ge=1, le=168, description="Lookback window in hours"),
) -> TimelineResponse:
    """Return hourly alert counts for the timeline chart (TTL-cached)."""
    try:
        rows = _cached(f"timeline_{hours}", fetch_timeline, hours)
        return TimelineResponse(timeline=rows)
    except Exception as exc:
        logger.error("fetch_timeline failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve timeline") from exc


@app.get("/alerts/countries", response_model=CountryDistributionResponse, tags=["Analytics"])
async def get_countries(
    limit: int = Query(default=20, ge=1, le=100),
) -> CountryDistributionResponse:
    """Return alert counts grouped by attacker country (TTL-cached)."""
    try:
        rows = _cached(f"countries_{limit}", fetch_country_distribution, limit)
        return CountryDistributionResponse(countries=rows)
    except Exception as exc:
        logger.error("fetch_country_distribution failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve country distribution") from exc


@app.get("/alerts/top-signatures", response_model=TopSignaturesResponse, tags=["Analytics"])
async def get_top_signatures(
    limit: int = Query(default=10, ge=1, le=50),
) -> TopSignaturesResponse:
    """Return most frequently triggered alert signatures (TTL-cached)."""
    try:
        rows = _cached(f"top_sigs_{limit}", fetch_top_signatures, limit)
        return TopSignaturesResponse(signatures=rows)
    except Exception as exc:
        logger.error("fetch_top_signatures failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve top signatures") from exc


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
        log_level="info",
        workers=1,  # single worker — SQLite is single-writer
    )
