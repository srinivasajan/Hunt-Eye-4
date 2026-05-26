from __future__ import annotations

import math
import random
import sys
import os

sys.path.insert(0, os.path.abspath('src'))
import time

import numpy as np
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from qt_ui.dashboard import HuntEyeDashboard


class PreviewFeed:
    def __init__(self) -> None:
        self.started_at = time.time()

    def frame(self):
        t = time.time() - self.started_at
        height, width = 480, 640
        image = np.zeros((height, width, 3), dtype=np.uint8)
        image[: height // 2, :] = [28, 36, 42]
        image[height // 2 :, :] = [18, 48, 28]

        x = int(width // 2 + 130 * math.sin(t * 0.7))
        y = int(height // 2 + 70 * math.cos(t * 0.5))
        image[max(0, y - 34) : min(height, y + 34), max(0, x - 24) : min(width, x + 24)] = [
            50,
            190,
            70,
        ]

        noise = np.random.randint(0, 10, (height, width, 3), dtype=np.uint8)
        image = np.clip(image.astype(np.int16) + noise - 5, 0, 255).astype(np.uint8)

        detection = {
            "bbox": (x - 42, y - 58, 84, 116),
            "label": "target",
            "conf": 0.86,
        }
        fps = 54 + 5 * math.sin(t) + random.uniform(-1, 1)
        workers = {
            "Camera": {"alive": True, "last_update": 0.04, "failed": False},
            "Detector": {"alive": True, "last_update": 0.08, "failed": False},
            "Tracker": {"alive": True, "last_update": 0.06, "failed": False},
            "Safety": {"alive": True, "last_update": 0.03, "failed": False},
        }
        return image, fps, [detection], detection, workers


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("HuntEye Preview")

    feed = PreviewFeed()
    dashboard = HuntEyeDashboard()
    dashboard.setWindowTitle("HuntEye Preview")
    dashboard.show()

    def tick() -> None:
        frame, fps, detections, target, workers = feed.frame()
        dashboard.update_camera(frame, fps, detections, target, "PREVIEW")
        dashboard.update_fps(fps)
        dashboard.update_workers(workers)

    timer = QTimer()
    timer.setInterval(33)
    timer.timeout.connect(tick)
    timer.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
