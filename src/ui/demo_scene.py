"""demo_scene.py — Simulated target generator for DEMO / degraded mode.

Produces time-based fake detections and tracks in the same dict format
that real workers produce, so the HUD and dashboard behave identically
to a live session.

Usage (main.py):
    from ui.demo_scene import DemoScene
    demo = DemoScene(frame_w=640, frame_h=480)
    ...
    if shared_hal.degraded:
        fake = demo.update(time.time())
        snapshot = {**snapshot, **fake}
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List


class DemoScene:
    """Generates believable synthetic tracking data.

    Two targets orbit the frame on independent sinusoidal paths.
    Target-1 is reliably tracked; Target-2 appears intermittently
    to simulate the 'target acquired / lost' lifecycle.
    """

    def __init__(self, frame_w: int = 640, frame_h: int = 480) -> None:
        self.w = frame_w
        self.h = frame_h
        self._t0 = time.time()

        # Per-target state
        self._last_target1_bbox = None
        self._lock_start: float | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, now: float | None = None) -> Dict[str, Any]:
        """Return a snapshot patch with detections, tracks, and target_bbox."""
        if now is None:
            now = time.time()
        t = now - self._t0

        detections: List[Dict] = []
        tracks:     List[Dict] = []
        target_bbox = None

        # ── Target 1 — primary, reliably tracked ──────────────────────
        t1 = self._target1_position(t)
        t1_bbox = self._bbox_from_centre(*t1, w=90, h=110)
        conf1   = 0.82 + 0.10 * abs(math.sin(t * 0.7))

        detections.append({
            "bbox":       t1_bbox,
            "confidence": round(conf1, 2),
            "label":      "person",
            "track_id":   1,
        })
        tracks.append({
            "track_id": 1,
            "bbox":     t1_bbox,
            "tlwh":     t1_bbox,
            "score":    conf1,
        })

        # Set primary target after a 3-second acquisition warm-up
        if t > 3.0:
            target_bbox = t1_bbox
            if self._lock_start is None:
                self._lock_start = now

        # ── Target 2 — secondary, intermittent ────────────────────────
        # Visible for 8s on, 5s off  (period = 13s)
        cycle = t % 13.0
        if cycle < 8.0:
            t2 = self._target2_position(t)
            t2_bbox = self._bbox_from_centre(*t2, w=70, h=85)
            conf2   = 0.55 + 0.20 * abs(math.sin(t * 1.1))
            detections.append({
                "bbox":       t2_bbox,
                "confidence": round(conf2, 2),
                "label":      "person",
                "track_id":   2,
            })
            tracks.append({
                "track_id": 2,
                "bbox":     t2_bbox,
                "tlwh":     t2_bbox,
                "score":    conf2,
            })

        # ── Telemetry patch ────────────────────────────────────────────
        # Simulate slow drift in position
        telemetry = {
            "position": {
                "x": round(12.4 + 0.3 * math.sin(t * 0.2), 2),
                "y": round(-8.1 + 0.2 * math.cos(t * 0.15), 2),
                "z": round(-18.0 + 0.5 * math.sin(t * 0.1), 2),
            },
            "velocity": {
                "x": round(0.1 * math.cos(t * 0.2), 2),
                "y": round(0.1 * math.sin(t * 0.15), 2),
                "z": round(0.05 * math.cos(t * 0.1), 2),
            },
        }

        return {
            "detections":  detections,
            "tracks":      tracks,
            "target_bbox": target_bbox,
            "telemetry":   telemetry,
        }

    def lock_duration(self, now: float | None = None) -> float:
        """Seconds since target-1 was first locked. 0 if not yet locked."""
        if self._lock_start is None:
            return 0.0
        return (now or time.time()) - self._lock_start

    # ------------------------------------------------------------------
    # Target motion paths
    # ------------------------------------------------------------------

    def _target1_position(self, t: float):
        """Target 1 — wide ellipse, slow drift."""
        cx = self.w * 0.5 + self.w * 0.28 * math.sin(t * 0.35)
        cy = self.h * 0.48 + self.h * 0.18 * math.cos(t * 0.28)
        return int(cx), int(cy)

    def _target2_position(self, t: float):
        """Target 2 — tighter figure-8, faster."""
        cx = self.w * 0.35 + self.w * 0.18 * math.sin(t * 0.6)
        cy = self.h * 0.55 + self.h * 0.12 * math.sin(t * 1.2)
        return int(cx), int(cy)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _bbox_from_centre(self, cx: int, cy: int, w: int, h: int):
        """Return [x1, y1, x2, y2] bbox clamped to frame."""
        x1 = max(0, cx - w // 2)
        y1 = max(0, cy - h // 2)
        x2 = min(self.w, cx + w // 2)
        y2 = min(self.h, cy + h // 2)
        return [x1, y1, x2, y2]
