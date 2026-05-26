from typing import Any, Dict, Optional
from core.logger import Logger
from core.restart_limiter import RestartLimiter
from core.worker_base import WorkerBase
from core.orchestrator import Orchestrator
from core.event_bus import EventBus


class Watchdog(WorkerBase):

    def __init__(
        self,
        orchestrator: Orchestrator,
        event_bus: EventBus,
        interval_seconds: float = 1.0,
        stale_after_seconds: float = 2.0,
        auto_restart: bool = False,
        max_restarts_per_minute: int = 5,
        restart_cooldown_seconds: float = 10.0,
    ) -> None:

        super().__init__("Watchdog", loop_interval=interval_seconds, restartable=False)

        self.orchestrator = orchestrator

        self.event_bus = event_bus

        self.stale_after_seconds = stale_after_seconds

        self.auto_restart = auto_restart

        self.restart_limiter = RestartLimiter(
            max_restarts_per_minute=max_restarts_per_minute,
            cooldown_seconds=restart_cooldown_seconds,
        )

    def safe_run(self) -> None:

        while self.running:

            self.heartbeat()

            for status in self.orchestrator.status():

                name = status["name"]

                if name == self.name:

                    continue

                unhealthy_reason = self._get_unhealthy_reason(status)

                if unhealthy_reason is None:

                    continue

                Logger.warning(
                    f"Worker unhealthy | name={name} | reason={unhealthy_reason}"
                )

                self.event_bus.emit(
                    "WORKER_UNHEALTHY",
                    {
                        "worker": name,
                        "reason": unhealthy_reason,
                        "status": status,
                    },
                )

                if self.auto_restart and status["restartable"]:

                    zone = status.get("isolation_zone")
                    decision = self.restart_limiter.can_restart(name, zone=zone)
                    if not decision.allow:
                        self.event_bus.emit(
                            "WORKER_RESTART_SUPPRESSED",
                            {
                                "worker": name,
                                "zone": zone,
                                "reason": decision.reason,
                                "retry_after_seconds": decision.retry_after_seconds,
                            },
                        )
                        Logger.warning(
                            f"Worker restart suppressed | name={name} | reason={decision.reason}"
                        )
                        continue

                    if self.orchestrator.restart_worker(name):
                        self.restart_limiter.record_restart(name)

            self.sleep()

    def _get_unhealthy_reason(self, status: Dict[str, Any]) -> Optional[str]:

        if status["failed"]:

            return "failed"

        if not status["alive"] and status["started_at"] is not None:

            return "dead"

        if status["last_update_age"] > self.stale_after_seconds:

            return "stale"

        return None

