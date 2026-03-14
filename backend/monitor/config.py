"""
Configuration module for SOC Platform backend.

Centralizes all configuration values with environment variable overrides.
Follows the 12-factor app methodology — no secrets in code.
"""

import os
import logging
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the backend directory (no-op if file does not exist)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent.parent          # backend/
DATA_DIR: Path = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_path(path_value: str) -> str:
    """Resolve env path values relative to backend BASE_DIR.

    This avoids startup-directory-dependent behavior when users provide
    relative paths (e.g. ./sample_eve.json) in .env.
    """
    p = Path(path_value)
    if p.is_absolute():
        return str(p)
    return str((BASE_DIR / p).resolve())

# Suricata eve.json — override with ENV var for custom locations
EVE_JSON_PATH: str = os.getenv(
    "EVE_JSON_PATH",
    "/var/log/suricata/eve.json",
)
EVE_JSON_PATH = _resolve_path(EVE_JSON_PATH)

# GeoLite2-City MMDB — override with ENV var
GEOIP_DB_PATH: str = os.getenv(
    "GEOIP_DB_PATH",
    str(BASE_DIR / "GeoLite2-City.mmdb"),
)
GEOIP_DB_PATH = _resolve_path(GEOIP_DB_PATH)

# SQLite database path
SQLITE_DB_PATH: str = os.getenv(
    "SQLITE_DB_PATH",
    str(DATA_DIR / "soc_alerts.db"),
)
SQLITE_DB_PATH = _resolve_path(SQLITE_DB_PATH)

# ---------------------------------------------------------------------------
# Email / SMTP  (Gmail SSL)
# ---------------------------------------------------------------------------
SMTP_EMAIL: str = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "465"))
ALERT_RECIPIENT: str = os.getenv("ALERT_RECIPIENT", SMTP_EMAIL)

# Severity threshold: alerts with severity <= this value trigger email
EMAIL_SEVERITY_THRESHOLD: int = int(os.getenv("EMAIL_SEVERITY_THRESHOLD", "2"))

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))

# CORS — comma-separated origins
CORS_ORIGINS: list[str] = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
).split(",")

# ---------------------------------------------------------------------------
# Monitor tuning (lightweight optimizations for 8 GB RAM)
# ---------------------------------------------------------------------------
# How often the log monitor checks for new lines (seconds)
MONITOR_POLL_INTERVAL: float = float(os.getenv("MONITOR_POLL_INTERVAL", "1.0"))

# Maximum alerts to keep in memory buffer before flushing
MONITOR_BATCH_SIZE: int = int(os.getenv("MONITOR_BATCH_SIZE", "50"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)-22s | %(message)s"

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger: logging.Logger = logging.getLogger("soc.config")

logger.info("Configuration loaded successfully")
logger.info("EVE_JSON_PATH  = %s", EVE_JSON_PATH)
logger.info("GEOIP_DB_PATH  = %s", GEOIP_DB_PATH)
logger.info("SQLITE_DB_PATH = %s", SQLITE_DB_PATH)
logger.info("SMTP configured = %s", bool(SMTP_EMAIL))

# Startup validation — warn about missing resources early
if not Path(EVE_JSON_PATH).exists():
    logger.warning(
        "EVE_JSON_PATH does not exist: %s — monitor will retry on startup",
        EVE_JSON_PATH,
    )
if not Path(GEOIP_DB_PATH).exists():
    logger.warning(
        "GEOIP_DB_PATH does not exist: %s — country lookups will return 'Unknown'",
        GEOIP_DB_PATH,
    )
