"""
Real-time Suricata eve.json log monitor.

Behaves like ``tail -f``:
  - Opens the log file, seeks to the END immediately.
  - Reads only *new* lines appended after startup.
  - Never re-reads the full file — safe for multi-gigabyte logs.
  - Handles log rotation (file truncation / inode change) gracefully.

Pipeline per new line:
  1. Parse JSON (skip malformed lines silently).
  2. Filter: only ``event_type == "alert"`` lines are processed.
  3. Enrich with GeoIP country lookup on ``src_ip``.
  4. Insert into SQLite.
  5. If severity <= threshold → send email alert.

Designed for a single-threaded asyncio loop so it can coexist with
FastAPI in the same process, OR be run as a standalone service.
"""

import json
import os
import time
import logging
from pathlib import Path
from typing import Optional, TextIO

from monitor.config import (
    EVE_JSON_PATH,
    MONITOR_POLL_INTERVAL,
    MONITOR_BATCH_SIZE,
)
from monitor.database import init_db, insert_alerts_batch
from monitor.geoip import lookup_country
from monitor.email_alert import should_send_email, send_alert_email

logger: logging.Logger = logging.getLogger("soc.log_monitor")


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_eve_line(line: str) -> Optional[dict]:
    """Parse a single eve.json line and extract alert fields.

    Returns a normalised alert dict, or None if the line should be skipped
    (non-alert event, malformed JSON, missing required fields).
    """
    try:
        event: dict = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        # Malformed JSON — silently skip; Suricata may write partial lines
        # during high-throughput bursts.
        logger.debug("Skipping malformed JSON line")
        return None

    # Only process alert events — ignore stats, dns, http, flow, etc.
    if event.get("event_type") != "alert":
        return None

    alert_block: Optional[dict] = event.get("alert")
    if alert_block is None:
        return None

    # Extract and normalise fields with safe defaults
    src_ip: str = event.get("src_ip", "0.0.0.0")
    dest_ip: str = event.get("dest_ip", "0.0.0.0")
    timestamp: str = event.get("timestamp", "")
    protocol: str = event.get("proto", "Unknown")

    signature: str = alert_block.get("signature", "Unknown Signature")
    severity: int = alert_block.get("severity", 4)
    category: str = alert_block.get("category", "Unknown")

    # GeoIP enrichment — resolve attacker country
    country: str = lookup_country(src_ip)

    return {
        "timestamp": timestamp,
        "src_ip": src_ip,
        "dest_ip": dest_ip,
        "signature": signature,
        "severity": severity,
        "category": category,
        "country": country,
        "protocol": protocol,
    }


# ---------------------------------------------------------------------------
# File‐following logic
# ---------------------------------------------------------------------------

class LogTailer:
    """Tail a log file efficiently, handling rotation and truncation."""

    def __init__(self, filepath: str) -> None:
        self.filepath: str = filepath
        self._fh: Optional[TextIO] = None
        self._inode: int = 0

    def open(self) -> None:
        """Open the file and seek to the end (skip historical data)."""
        try:
            self._fh = open(self.filepath, "r", encoding="utf-8", errors="replace")
            self._fh.seek(0, os.SEEK_END)
            stat = os.stat(self.filepath)
            self._inode = stat.st_ino
            logger.info(
                "Tailing %s from offset %d (inode %d)",
                self.filepath,
                self._fh.tell(),
                self._inode,
            )
        except FileNotFoundError:
            logger.error("Eve log not found: %s — will retry", self.filepath)
            self._fh = None

    def read_new_lines(self) -> list[str]:
        """Read any new complete lines appended since last call.

        Handles:
        - Normal appends
        - File truncation (Suricata log rotation with copytruncate)
        - File replacement (new inode after rotate + create)
        """
        if self._fh is None:
            self.open()
            if self._fh is None:
                return []

        # Detect truncation or inode change (log rotation)
        try:
            stat = os.stat(self.filepath)
        except FileNotFoundError:
            logger.warning("Eve log disappeared — will re-open on next cycle")
            self.close()
            return []

        if stat.st_ino != self._inode:
            # File was rotated (new file created) — reopen
            logger.info("Inode changed — log rotated, reopening")
            self.close()
            self.open()
            if self._fh is None:
                return []

        if stat.st_size < self._fh.tell():
            # File was truncated (copytruncate rotation) — seek to start
            logger.info("File truncated — seeking to beginning")
            self._fh.seek(0)

        lines: list[str] = []
        for raw_line in self._fh:
            stripped: str = raw_line.strip()
            if stripped:
                lines.append(stripped)
        return lines

    def close(self) -> None:
        """Close the file handle."""
        if self._fh is not None:
            self._fh.close()
            self._fh = None


# ---------------------------------------------------------------------------
# Main monitoring loop (blocking — run in a thread or standalone)
# ---------------------------------------------------------------------------

def run_monitor() -> None:
    """Start the blocking log monitoring loop.

    Initialises the database, then enters an infinite poll loop reading
    new lines from eve.json, enriching, storing, and alerting.
    """
    logger.info("=== SOC Log Monitor starting ===")
    init_db()

    tailer = LogTailer(EVE_JSON_PATH)
    tailer.open()

    batch: list[dict] = []

    # Track recently emailed (signature, src_ip) pairs to suppress duplicates.
    # Key: (signature, src_ip) → last email timestamp (monotonic).
    # Alerts with the same key are suppressed for EMAIL_DEDUP_WINDOW seconds.
    EMAIL_DEDUP_WINDOW: float = 300.0  # 5 minutes
    _email_sent_at: dict[tuple, float] = {}

    def _should_email_now(alert: dict) -> bool:
        """Rate-limit emails: same (signature, src_ip) only once per 5 min."""
        if not should_send_email(alert["severity"]):
            return False
        key = (alert["signature"], alert["src_ip"])
        now = time.monotonic()
        last = _email_sent_at.get(key, 0.0)
        if now - last >= EMAIL_DEDUP_WINDOW:
            _email_sent_at[key] = now
            # Prune old entries to prevent unbounded growth
            if len(_email_sent_at) > 500:
                cutoff = now - EMAIL_DEDUP_WINDOW
                keys_to_drop = [k for k, ts in _email_sent_at.items() if ts < cutoff]
                for k in keys_to_drop:
                    del _email_sent_at[k]
            return True
        return False

    try:
        while True:
            new_lines: list[str] = tailer.read_new_lines()

            for line in new_lines:
                alert = _parse_eve_line(line)
                if alert is None:
                    continue
                batch.append(alert)

                # Flush batch when it reaches configured size
                if len(batch) >= MONITOR_BATCH_SIZE:
                    inserted: int = insert_alerts_batch(batch)
                    logger.info("Flushed batch of %d alerts to database", inserted)
                    # Send emails AFTER successful DB commit so data is persisted first
                    for a in batch:
                        if _should_email_now(a):
                            send_alert_email(a)
                    batch.clear()

            # Flush any remaining alerts after processing all new lines
            if batch:
                inserted = insert_alerts_batch(batch)
                if inserted:
                    logger.info("Flushed remaining %d alerts to database", inserted)
                for a in batch:
                    if _should_email_now(a):
                        send_alert_email(a)
                batch.clear()

            # Sleep to avoid busy-waiting — configurable via MONITOR_POLL_INTERVAL
            time.sleep(MONITOR_POLL_INTERVAL)

    except KeyboardInterrupt:
        logger.info("Monitor stopped by user (Ctrl+C)")
    finally:
        # Flush any pending alerts on shutdown
        if batch:
            insert_alerts_batch(batch)
            logger.info("Final flush: %d alerts written", len(batch))
        tailer.close()
        logger.info("=== SOC Log Monitor stopped ===")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run_monitor()
