"""
SQLite database module for SOC alert storage.

Design decisions:
- WAL journal mode for concurrent-read / single-writer performance.
- Explicit indexes on severity, timestamp, and src_ip for fast dashboard queries.
- Batch insert support to reduce I/O overhead on 8 GB RAM systems.
- Connection pooling via a module-level singleton; safe for single-writer patterns.
"""

import sqlite3
import logging
import threading
from typing import Optional

from monitor.config import SQLITE_DB_PATH

logger: logging.Logger = logging.getLogger("soc.database")

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
CREATE_TABLE_SQL: str = """
CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    src_ip      TEXT    NOT NULL,
    dest_ip     TEXT    NOT NULL,
    signature   TEXT    NOT NULL,
    severity    INTEGER NOT NULL,
    category    TEXT    NOT NULL DEFAULT 'Unknown',
    country     TEXT    NOT NULL DEFAULT 'Unknown',
    protocol    TEXT    NOT NULL DEFAULT 'Unknown'
);
"""

CREATE_INDEXES_SQL: list[str] = [
    "CREATE INDEX IF NOT EXISTS idx_alerts_severity  ON alerts (severity);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts (timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_src_ip    ON alerts (src_ip);",
]

# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------
_connection: Optional[sqlite3.Connection] = None
_db_initialised: bool = False  # idempotency guard for init_db()
# Lock serialises all DB access across the monitor writer thread and
# the multiple FastAPI reader threads sharing the same connection.
_db_lock: threading.Lock = threading.Lock()


def get_connection() -> sqlite3.Connection:
    """Return a module-level SQLite connection (singleton, thread-safe).

    Uses WAL mode for better concurrent-read performance —
    critical when FastAPI reads while the monitor writes.
    All callers must hold _db_lock before using the returned connection.
    """
    global _connection
    if _connection is None:
        logger.info("Opening SQLite database at %s", SQLITE_DB_PATH)
        _connection = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        # WAL mode allows concurrent readers alongside a single writer.
        _connection.execute("PRAGMA journal_mode=WAL;")
        # Reduce fsync calls — acceptable tradeoff for a monitoring tool.
        _connection.execute("PRAGMA synchronous=NORMAL;")
        # Keep page cache small to stay within 8 GB RAM budget.
        _connection.execute("PRAGMA cache_size=-8000;")  # ~8 MB
        logger.info("SQLite WAL mode enabled, cache_size set to 8 MB")
    return _connection


def init_db() -> None:
    """Create the alerts table and indexes if they do not already exist.

    Thread-safe and idempotent — safe to call from both the lifespan
    handler and the monitor thread.  The guard flag avoids redundant
    schema DDL after the first successful call.
    """
    global _db_initialised
    if _db_initialised:
        logger.debug("init_db() skipped — already initialised")
        return
    with _db_lock:
        if _db_initialised:          # double-check after lock
            return
        conn = get_connection()
        conn.execute(CREATE_TABLE_SQL)
        for idx_sql in CREATE_INDEXES_SQL:
            conn.execute(idx_sql)
        conn.commit()
        _db_initialised = True
        logger.info("Database initialized — table and indexes ready")


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------
def insert_alert(alert: dict) -> int:
    """Insert a single alert dict and return its row id."""
    with _db_lock:
        conn = get_connection()
        cursor = conn.execute(
            """
            INSERT INTO alerts (timestamp, src_ip, dest_ip, signature,
                                severity, category, country, protocol)
            VALUES (:timestamp, :src_ip, :dest_ip, :signature,
                    :severity, :category, :country, :protocol)
            """,
            alert,
        )
        conn.commit()
        row_id: int = cursor.lastrowid  # type: ignore[assignment]
    return row_id


def insert_alerts_batch(alerts: list[dict]) -> int:
    """Insert a batch of alert dicts in a single transaction.

    Returns the number of rows inserted.
    """
    if not alerts:
        return 0
    with _db_lock:
        conn = get_connection()
        conn.executemany(
            """
            INSERT INTO alerts (timestamp, src_ip, dest_ip, signature,
                                severity, category, country, protocol)
            VALUES (:timestamp, :src_ip, :dest_ip, :signature,
                    :severity, :category, :country, :protocol)
            """,
            alerts,
        )
        conn.commit()
    logger.debug("Batch-inserted %d alerts", len(alerts))
    return len(alerts)


def fetch_all_alerts(limit: int = 500, offset: int = 0) -> list[dict]:
    """Return alerts ordered by newest first."""
    with _db_lock:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM alerts ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_latest_alerts(count: int = 20) -> list[dict]:
    """Return the most recent N alerts."""
    with _db_lock:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM alerts ORDER BY id DESC LIMIT ?",
            (count,),
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_alerts_by_severity(level: int, limit: int = 200) -> list[dict]:
    """Return alerts filtered by a specific severity level."""
    with _db_lock:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM alerts WHERE severity = ? ORDER BY id DESC LIMIT ?",
            (level, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_stats() -> dict:
    """Aggregate statistics for the dashboard metric cards.

    Single query using conditional COUNT for efficiency.
    """
    with _db_lock:
        conn = get_connection()
        row = conn.execute(
            """
            SELECT
                COUNT(*)                                         AS total_alerts,
                COUNT(CASE WHEN severity <= 2 THEN 1 END)        AS high_severity_alerts,
                COUNT(CASE WHEN timestamp >= datetime('now', '-1 hour') THEN 1 END)
                                                                 AS alerts_last_hour
            FROM alerts
            """
        ).fetchone()
    return {
        "total_alerts": row["total_alerts"],
        "high_severity_alerts": row["high_severity_alerts"],
        "alerts_last_hour": row["alerts_last_hour"],
    }


def fetch_top_ips(limit: int = 10) -> list[dict]:
    """Return top N source IPs by alert count."""
    with _db_lock:
        conn = get_connection()
        rows = conn.execute(
            """SELECT src_ip, COUNT(*) AS count
               FROM alerts GROUP BY src_ip
               ORDER BY count DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_severity_distribution() -> list[dict]:
    """Return alert count grouped by severity level."""
    with _db_lock:
        conn = get_connection()
        rows = conn.execute(
            """SELECT severity, COUNT(*) AS count
               FROM alerts GROUP BY severity
               ORDER BY severity"""
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_timeline(hours: int = 24) -> list[dict]:
    """Return alert counts grouped by hour for the last N hours.

    NOTE: SQLite strftime uses single %-prefixed codes (%Y, %m, etc.).
    Double %% was a bug — it is a plain Python string, NOT an f-string.
    HAVING clause guards against NULL hour values produced when a stored
    timestamp cannot be parsed by strftime (e.g. malformed rows).
    """
    with _db_lock:
        conn = get_connection()
        rows = conn.execute(
            """SELECT strftime('%Y-%m-%d %H:00', timestamp) AS hour,
                      COUNT(*) AS count
               FROM alerts
               WHERE timestamp >= datetime('now', ? || ' hours')
               GROUP BY hour
               HAVING hour IS NOT NULL
               ORDER BY hour""",
            (f"-{hours}",),
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_country_distribution(limit: int = 20) -> list[dict]:
    """Return alert counts grouped by country."""
    with _db_lock:
        conn = get_connection()
        rows = conn.execute(
            """SELECT country, COUNT(*) AS count
               FROM alerts GROUP BY country
               ORDER BY count DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_top_signatures(limit: int = 10) -> list[dict]:
    """Return most frequently triggered alert signatures."""
    with _db_lock:
        conn = get_connection()
        rows = conn.execute(
            """SELECT signature, COUNT(*) AS count
               FROM alerts GROUP BY signature
               ORDER BY count DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_alerts_after(last_id: int, limit: int = 200) -> list[dict]:
    """Return alerts with id > last_id (incremental sync).

    The frontend sends the highest alert id it already has;
    this returns only the rows inserted since then — eliminating
    redundant data transfer and reducing SQLite read pressure.
    """
    with _db_lock:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM alerts WHERE id > ? ORDER BY id DESC LIMIT ?",
            (last_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_alert_count() -> int:
    """Return total number of alerts in the database."""
    with _db_lock:
        conn = get_connection()
        row = conn.execute("SELECT COUNT(*) AS cnt FROM alerts").fetchone()
    return row["cnt"]
