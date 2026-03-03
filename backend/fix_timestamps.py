import sqlite3
import re
from datetime import datetime

DB_PATH = "/media/ttr/Backup/NIDS_v1/soc-platform/backend/data/soc_alerts.db"

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
