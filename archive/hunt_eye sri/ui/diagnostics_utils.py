"""Diagnostics helpers for HuntEye dashboard (Dev 1.2)."""

from __future__ import annotations

import time
from typing import Any, Dict, List


def summarize_events(events: List[Dict[str, Any]], limit: int = 12) -> List[str]:
    lines: List[str] = []
    for event in events[-limit:]:
        age = time.time() - float(event.get("time", time.time()))
        level = str(event.get("level", "INFO"))
        msg = str(event.get("message", ""))
        lines.append(f"{age:4.1f}s {level}: {msg}")
    return lines


def summarize_workers(worker_statuses: List[Dict[str, Any]], limit: int = 12) -> List[str]:
    lines: List[str] = []
    for st in worker_statuses[:limit]:
        name = st.get("name")
        alive = st.get("alive")
        failed = st.get("failed")
        age = st.get("last_update_age")
        zone = st.get("isolation_zone")
        label = "OK" if alive and not failed else "BAD"
        zone_txt = f" zone={zone}" if zone else ""
        lines.append(f"{name}: {label} {age:.2f}s{zone_txt}")
    return lines
