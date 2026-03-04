#!/usr/bin/env python3
"""Append a test alert JSON line to backend/sample_eve.json.
Usage: python backend/tools/generate_alert.py [count]
"""
import sys
from datetime import datetime
import random
import json
from pathlib import Path

COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 1
# Resolve output file relative to this script (backend/sample_eve.json)
BASE = Path(__file__).resolve().parent.parent
OUT = BASE / 'sample_eve.json'

for _ in range(COUNT):
    alert = {
        "event_type": "alert",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "src_ip": f"{random.randint(1,254)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "dest_ip": "10.0.0.1",
        "proto": "TCP",
        "alert": {
            "signature": "Generated test alert",
            "severity": 2,
            "category": "Test"
        }
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(alert, separators=(',', ':')) + "\n")
print(f"Wrote {COUNT} alerts to {OUT}")
