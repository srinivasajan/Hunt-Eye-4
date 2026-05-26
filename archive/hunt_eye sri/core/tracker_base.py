"""Base class for tracking workers in the HuntEye pipeline (Dev2 integration).

Tracking workers consume detections and produce tracks.

Expected SharedState contract:
- Reads: detections (List[Dict]), latest_frame (np.ndarray), telemetry (Dict)
- Writes: tracks (List[Dict])

Track format (suggested):
{
  "track_id": int,
  "bbox": [x1, y1, x2, y2],
  "confidence": float | None,
  ...
}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from core.logger import Logger
from core.worker_base import WorkerBase


class TrackerWorkerBase(WorkerBase):
    def __init__(
        self,
        name: str,
        state: Any,
        loop_interval: float = 0.0,
        restartable: bool = True,
    ):
        super().__init__(name=name, loop_interval=loop_interval, restartable=restartable)
        self.state = state
        self.logger = Logger

    def track(
        self,
        detections: List[Dict[str, Any]],
        frame: Optional[np.ndarray] = None,
        telemetry: Optional[Dict[str, Any]] = None,
        previous_tracks: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Compute updated tracks.

        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement track() method")

    def safe_run(self) -> None:
        while self.running:
            try:
                frame = self.state.get_latest_frame()

                with self.state.lock:
                    detections = list(getattr(self.state, "detections", []))
                    previous_tracks = list(getattr(self.state, "tracks", []))
                    telemetry = dict(getattr(self.state, "telemetry", {}))

                tracks = self.track(
                    detections=detections,
                    frame=frame,
                    telemetry=telemetry,
                    previous_tracks=previous_tracks,
                )

                with self.state.lock:
                    self.state.tracks = tracks

                self.heartbeat()

            except Exception as e:
                self.logger.error(f"Tracking error in {self.name}: {e}")
                self.failed = True
                self.error = str(e)
                self.sleep(1.0)

            self.sleep()
