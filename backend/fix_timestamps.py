"""
One-off utility: normalise legacy alert timestamps in the SQLite database.

Older versions of the log monitor stored Suricata's ISO-8601 timestamps
(e.g. "2026-01-01T12:00:00.123456+0000") verbatim.  SQLite's strftime()
cannot parse those, which caused NULL groups in the timeline query.

Run this script once against an existing database to back-fill the correct
"YYYY-MM-DD HH:MM:SS" format that the rest of the app expects:

    python fix_timestamps.py               # uses default DB path from config
    python fix_timestamps.py /path/to.db  # explicit path
"""

import sys
import sqlite3
import re
from pathlib import Path

# Default to the path defined in the monitor config so this script works
# out-of-the-box from any working directory and on any machine.
_DEFAULT_DB = Path(__file__).resolve().parent / "data" / "soc_alerts.db"
DB_PATH = sys.argv[1] if len(sys.argv) > 1 else str(_DEFAULT_DB)

# Regex for ISO format with T and microseconds/zone
def normalize_timestamp(ts):
    # Try to match ISO format
    m = re.match(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(\.\d+)?([+-]\d+)?", ts)
    if m:
        # Remove microseconds and timezone
        date = m.group(1)
        time = m.group(2)
        return f"{date} {time}"
    # Already correct format
    return ts

def fix_alert_timestamps():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, timestamp FROM alerts")
    updates = []
    for row in cur.fetchall():
        alert_id, ts = row
        new_ts = normalize_timestamp(ts)
        if new_ts != ts:
            updates.append((new_ts, alert_id))
    if updates:
        cur.executemany("UPDATE alerts SET timestamp=? WHERE id=?", updates)
        conn.commit()
        print(f"Updated {len(updates)} timestamps.")
    else:
        print("No timestamps needed updating.")
    conn.close()

if __name__ == "__main__":
    fix_alert_timestamps()
