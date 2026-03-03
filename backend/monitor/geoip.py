"""
GeoIP enrichment module using MaxMind GeoLite2-City database.

Resolves source IP addresses to country names for SOC dashboard mapping.
Gracefully returns "Unknown" when lookup fails (private IPs, missing DB, etc.).
The reader is loaded once and reused — minimal memory footprint (~60 MB mapped).
"""

import logging
import threading
from functools import lru_cache
from typing import Optional

import geoip2.database           # type: ignore[import-untyped]
import geoip2.errors             # type: ignore[import-untyped]

from monitor.config import GEOIP_DB_PATH

logger: logging.Logger = logging.getLogger("soc.geoip")

# ---------------------------------------------------------------------------
# Module-level reader (loaded once, thread-safe for reads)
# ---------------------------------------------------------------------------
_reader: Optional[geoip2.database.Reader] = None
# Lock protects the _reader initialisation race condition.
# geoip2.Reader itself is thread-safe for concurrent reads once opened.
_reader_lock: threading.Lock = threading.Lock()


def _get_reader() -> Optional[geoip2.database.Reader]:
    """Lazy-load the GeoIP reader so startup doesn't fail if DB is missing.

    Thread-safe: double-checked locking ensures only one thread opens the DB.
    """
    global _reader
    if _reader is None:
        with _reader_lock:
            if _reader is None:  # re-check after acquiring lock
                try:
                    _reader = geoip2.database.Reader(GEOIP_DB_PATH)
                    logger.info("GeoIP database loaded from %s", GEOIP_DB_PATH)
                except FileNotFoundError:
                    logger.warning(
                        "GeoIP database not found at %s — country lookups will return 'Unknown'",
                        GEOIP_DB_PATH,
                    )
                except Exception as exc:
                    logger.error("Failed to open GeoIP database: %s", exc)
    return _reader


@lru_cache(maxsize=4096)
def lookup_country(ip: str) -> str:
    """Resolve an IP address to a country name.

    Results are cached in an LRU cache (4096 entries) so repeated lookups
    for the same attacker IP — common in scan scenarios — hit RAM not disk.

    Returns:
        Country name string, or "Unknown" on any failure (private IP,
        database miss, corrupted record, etc.).
    """
    reader = _get_reader()
    if reader is None:
        return "Unknown"
    try:
        response = reader.city(ip)
        country: Optional[str] = response.country.name
        return country if country else "Unknown"
    except geoip2.errors.AddressNotFoundError:
        # Private / loopback addresses won't be in the DB — expected.
        logger.debug("IP %s not found in GeoIP database", ip)
        return "Unknown"
    except ValueError:
        # Malformed IP string
        logger.warning("Invalid IP address for GeoIP lookup: %s", ip)
        return "Unknown"
    except Exception as exc:
        logger.error("GeoIP lookup error for %s: %s", ip, exc)
        return "Unknown"


def close_reader() -> None:
    """Cleanly close the GeoIP reader (call on shutdown)."""
    global _reader
    if _reader is not None:
        _reader.close()
        _reader = None
        logger.info("GeoIP reader closed")


def is_geoip_loaded() -> bool:
    """Return True if the GeoIP database is loaded and usable."""
    return _get_reader() is not None
