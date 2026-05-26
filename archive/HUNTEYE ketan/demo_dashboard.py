import sys
import time
import math
import random
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ui.dashboard import HuntEyeDashboard
from ui.diagnostics_window import DiagnosticsWindow
from ui.widgets.recording_panel import RecordingPanel
from ui.recording_manager import RecordingManager
from ui.widgets.mission_planner import MissionPlanner
from ui.widgets.config_editor import ConfigEditor


class FakeState:
    def __init__(self):
        self._data = {
            "fps": 0.0,
            "latest_frame": None,
            "detections": [],
            "active_target": None,
            "system_mode": "SIM",
            "worker_status": {
                "CameraWorker":   {"alive": True,  "last_update": 0.02, "failed": False},
                "DetectorWorker": {"alive": False, "last_update": 0.00, "failed": False},
                "TrackerWorker":  {"alive": False, "last_update": 0.00, "failed": False},
                "ControlWorker":  {"alive": False, "last_update": 0.00, "failed": False},
            },
        }
        self._t0 = time.time()

    def get(self, key, default=None):
        return self._data.get(key, default)

    def tick(self):
        t = time.time() - self._t0
        h, w = 480, 640
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        for row in range(h // 2):
            v = int(20 + row * 0.15)
            frame[row, :] = [v + 10, v + 5, v]
        frame[h // 2:, :] = [10, 25, 10]
        tx = int(w // 2 + 120 * math.sin(t * 0.5))
        ty = int(h // 2 + 80 * math.cos(t * 0.4))
        frame[max(0, ty-30):ty+30, max(0, tx-20):tx+20] = [50, 180, 50]
        noise = np.random.randint(0, 12, (h, w, 3), dtype=np.uint8)
        frame = np.clip(frame.astype(np.int16) + noise - 6, 0, 255).astype(np.uint8)
        self._data["latest_frame"] = frame
        self._data["fps"] = 55 + 8 * math.sin(t * 0.7) + random.uniform(-1, 1)
        ws = self._data["worker_status"]
        if t > 3:
            ws["DetectorWorker"]["alive"] = True
            ws["DetectorWorker"]["last_update"] = abs(math.sin(t * 2)) * 0.3
        if t > 6:
            ws["TrackerWorker"]["alive"] = True
            ws["TrackerWorker"]["last_update"] = 0.1
        if t > 9:
            ws["ControlWorker"]["alive"] = True
            ws["ControlWorker"]["last_update"] = 0.01
        cx = int(320 + 120 * math.sin(t * 0.5))
        cy = int(240 + 80 * math.cos(t * 0.4))
        self._data["detections"] = [
            {"bbox": (cx-40, cy-60, 80, 120), "label": "person", "conf": 0.87}
        ]
        self._data["active_target"] = {"bbox": (cx-40, cy-60, 80, 120)}


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("HuntEye Dev 1.2")

    state   = FakeState()
    manager = RecordingManager()

    dashboard = HuntEyeDashboard()
    diag      = DiagnosticsWindow()
    rec_panel = RecordingPanel()
    mission   = MissionPlanner()
    config    = ConfigEditor()

    rec_panel.recording_started.connect(lambda path: manager.start(path))
    rec_panel.recording_stopped.connect(lambda: manager.stop())
    mission.mission_started.connect(lambda wps: diag.log("INFO", f"Mission started: {len(wps)} waypoints"))
    mission.mission_cleared.connect(lambda: diag.log("WARNING", "Mission cleared"))
    config.config_saved.connect(lambda cfg: diag.log("INFO", f"Config saved: {len(cfg)} sections"))

    dashboard.show()
    diag.show()

    rec_panel.setWindowTitle("HuntEye — Recording")
    rec_panel.resize(500, 400)
    rec_panel.show()

    mission.setWindowTitle("HuntEye — Mission Planner")
    mission.resize(500, 600)
    mission.show()

    config.setWindowTitle("HuntEye — Config Editor")
    config.resize(480, 600)
    config.show()

    diag.start_demo_logs()

    def tick():
        state.tick()
        frame = state.get("latest_frame")
        fps   = state.get("fps", 0.0)
        dets  = state.get("detections", [])
        tgt   = state.get("active_target")
        ws    = state.get("worker_status", {})
        t     = time.time() - state._t0

        dashboard.update_camera(frame, fps, dets, tgt, "SIM")
        dashboard.update_fps(fps)
        dashboard.update_workers(ws)
        diag.update_workers(ws)

        nx = 0.5 + 0.3 * math.sin(t * 0.3)
        ny = 0.5 + 0.2 * math.cos(t * 0.3)
        mission.update_drone_pos(nx, ny)

        if manager.is_recording and frame is not None:
            manager.add_frame(frame, {"fps": fps})

    timer = QTimer()
    timer.setInterval(33)
    timer.timeout.connect(tick)
    timer.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()