from __future__ import annotations

import time
from typing import Any

from core.worker_base import WorkerBase


class PerceptionWorker(WorkerBase):
    def __init__(self, state=None, config=None, **kwargs):
        super().__init__("PerceptionWorker", loop_interval=0.03, restartable=True)

        self.state = state
        self.config = config or {}

    def safe_run(self):
        while self.running:
            self.heartbeat()

            snapshot = {
                "detections": [],
                "tracks": [],
                "timestamp": time.time(),
            }

            if self.state and hasattr(self.state, "update_snapshot"):
                self.state.update_snapshot(snapshot)

            self.sleep()