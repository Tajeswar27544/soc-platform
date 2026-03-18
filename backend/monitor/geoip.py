"""
GeoIP enrichment module using MaxMind GeoLite2-City database.

Resolves source IP addresses to country names for SOC dashboard mapping.
Gracefully returns "Unknown" when lookup fails (private IPs, missing DB, etc.).
The reader is loaded once and reused — minimal memory footprint (~60 MB mapped).
"""

import logging
import os
import shutil
import tarfile
import tempfile
import threading
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Optional, Union

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


def download_geoip_db(
    target_path: Union[Path, str],
    *,
    license_key: Optional[str] = None,
    edition_id: str = "GeoLite2-City",
) -> bool:
    """Download and extract the GeoLite2 database.

    Uses the MAXMIND_LICENSE_KEY env var by default. Returns True on success.
    """
    path = Path(target_path)
    key = (license_key or os.getenv("MAXMIND_LICENSE_KEY", "")).strip()
    if not key:
        logger.warning(
            "GeoIP database missing and MAXMIND_LICENSE_KEY not set — cannot download automatically",
        )
        return False

    url = (
        "https://download.maxmind.com/app/geoip_download"
        f"?edition_id={edition_id}&license_key={key}&suffix=tar.gz"
    )

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            tgz_path = Path(tmpdir) / "geoip.tar.gz"
            logger.info("Downloading GeoIP database (%s) from MaxMind", edition_id)
            with urllib.request.urlopen(url, timeout=30) as resp, open(tgz_path, "wb") as fh:
                shutil.copyfileobj(resp, fh)

            with tarfile.open(tgz_path, "r:gz") as tar:
                member = next((m for m in tar.getmembers() if m.name.endswith(".mmdb")), None)
                if member is None:
                    raise RuntimeError("No .mmdb file found in GeoIP archive")
                with tar.extractfile(member) as src, open(path, "wb") as dst:
                    shutil.copyfileobj(src, dst)

        logger.info("GeoIP database downloaded to %s", path)
        return True
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            logger.error(
                "GeoIP download failed (HTTP %s) — check MAXMIND_LICENSE_KEY permissions",
                exc.code,
            )
        else:
            logger.error("GeoIP download failed (HTTP %s)", exc.code)
    except Exception as exc:  # pragma: no cover - defensive path
        logger.error("GeoIP download failed: %s", exc)
    return False


def _get_reader() -> Optional[geoip2.database.Reader]:
    """Lazy-load the GeoIP reader so startup doesn't fail if DB is missing.

    Thread-safe: double-checked locking ensures only one thread opens the DB.
    """
    global _reader
    if _reader is None:
        with _reader_lock:
            if _reader is None:  # re-check after acquiring lock
                db_path = Path(GEOIP_DB_PATH)
                if not db_path.exists():
                    logger.warning(
                        "GEOIP_DB_PATH does not exist: %s — attempting download",
                        db_path,
                    )
                    download_geoip_db(db_path)

                try:
                    _reader = geoip2.database.Reader(str(db_path))
                    logger.info("GeoIP database loaded from %s", db_path)
                except FileNotFoundError:
                    logger.warning(
                        "GeoIP database not found at %s — country lookups will return 'Unknown'",
                        db_path,
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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download the GeoLite2-City database to GEOIP_DB_PATH")
    parser.add_argument(
        "--license-key",
        dest="license_key",
        default=os.getenv("MAXMIND_LICENSE_KEY", ""),
        help="MaxMind license key (or set MAXMIND_LICENSE_KEY)",
    )
    parser.add_argument(
        "--output",
        dest="output",
        default=GEOIP_DB_PATH,
        help="Destination .mmdb path (default: GEOIP_DB_PATH)",
    )
    args = parser.parse_args()

    target = Path(args.output)
    success = download_geoip_db(target, license_key=args.license_key)
    raise SystemExit(0 if success else 1)
