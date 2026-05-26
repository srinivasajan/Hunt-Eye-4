"""Restart limiting / backoff utilities (Dev 1.1 reliability hardening)."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional


@dataclass
class RestartDecision:
    allow: bool
    reason: str
    retry_after_seconds: float | None = None


class RestartLimiter:
    """Limit restart churn per worker and optionally per isolation zone.

    This is intentionally simple: track restarts in a rolling time window,
    and apply a cooldown after exceeding the limit.
    """

    def __init__(
        self,
        max_restarts_per_minute: int = 5,
        cooldown_seconds: float = 10.0,
    ):
        self.max_restarts_per_minute = int(max_restarts_per_minute)
        self.cooldown_seconds = float(cooldown_seconds)

        self._worker_restarts: Dict[str, Deque[float]] = {}
        self._zone_quarantine_until: Dict[str, float] = {}

    def quarantine_zone(self, zone: str, seconds: float | None = None) -> None:
        until = time.time() + (self.cooldown_seconds if seconds is None else float(seconds))
        self._zone_quarantine_until[zone] = max(until, self._zone_quarantine_until.get(zone, 0.0))

    def can_restart(self, worker_name: str, zone: str | None = None) -> RestartDecision:
        now = time.time()

        if zone:
            quarantine_until = self._zone_quarantine_until.get(zone, 0.0)
            if quarantine_until > now:
                return RestartDecision(
                    allow=False,
                    reason=f"zone_quarantined:{zone}",
                    retry_after_seconds=quarantine_until - now,
                )

        history = self._worker_restarts.setdefault(worker_name, deque())

        # Trim older than 60s
        cutoff = now - 60.0
        while history and history[0] < cutoff:
            history.popleft()

        if self.max_restarts_per_minute <= 0:
            return RestartDecision(allow=True, reason="unlimited")

        if len(history) >= self.max_restarts_per_minute:
            # Quarantine the zone when we exceed limit (if provided)
            if zone:
                self.quarantine_zone(zone)
                quarantine_until = self._zone_quarantine_until.get(zone, 0.0)
                return RestartDecision(
                    allow=False,
                    reason=f"restart_limit_exceeded_zone_quarantined:{zone}",
                    retry_after_seconds=max(0.0, quarantine_until - now),
                )

            # Otherwise just impose a cooldown for this worker
            retry_after = self.cooldown_seconds
            return RestartDecision(
                allow=False,
                reason="restart_limit_exceeded",
                retry_after_seconds=retry_after,
            )

        return RestartDecision(allow=True, reason="ok")

    def record_restart(self, worker_name: str) -> None:
        now = time.time()
        history = self._worker_restarts.setdefault(worker_name, deque())
        history.append(now)
