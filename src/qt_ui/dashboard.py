from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QFrame, QStatusBar, QSplitter
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import time

from qt_ui.widgets.fps_graph import FPSGraph
from qt_ui.widgets.worker_panel import WorkerPanel
from qt_ui.widgets.metrics_panel import MetricsPanel
from qt_ui.widgets.cam_view import CameraView

_C_BG      = "#0d1117"
_C_SURFACE = "#161b22"
_C_BORDER  = "#30363d"
_C_TEXT    = "#c9d1d9"
_C_ACCENT  = "#3fb950"
_C_MUTED   = "#8b949e"

_BASE_STYLE = f"""
    QMainWindow, QWidget {{
        background: {_C_BG};
        color: {_C_TEXT};
        font-family: Consolas, monospace;
    }}
    QSplitter::handle {{
        background: {_C_BORDER};
        width: 1px;
        height: 1px;
    }}
    QStatusBar {{
        background: {_C_SURFACE};
        color: {_C_MUTED};
        font-size: 11px;
        border-top: 1px solid {_C_BORDER};
    }}
    QLabel {{ background: transparent; }}
"""


class _TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(f"QWidget {{ background: {_C_SURFACE}; border-bottom: 1px solid {_C_BORDER}; }}")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        logo = QLabel("HUNT EYE")
        logo.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        logo.setStyleSheet(f"color: {_C_ACCENT}; background: transparent;")
        layout.addWidget(logo)
        layout.addStretch()

        self._mode_badge = QLabel("SIM")
        self._mode_badge.setFixedSize(52, 22)
        self._mode_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._mode_badge.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self._mode_badge.setStyleSheet(
            f"background: #0d2117; color: {_C_ACCENT}; border: 1px solid {_C_ACCENT}; border-radius: 4px;"
        )
        layout.addWidget(self._mode_badge)

        self._uptime_lbl = QLabel("00:00:00")
        self._uptime_lbl.setFont(QFont("Consolas", 11))
        self._uptime_lbl.setStyleSheet(f"color: {_C_MUTED}; background: transparent;")
        layout.addWidget(self._uptime_lbl)
        self._start_time = time.time()

    def set_mode(self, mode):
        self._mode_badge.setText(mode)

    def tick_uptime(self):
        e = int(time.time() - self._start_time)
        h, r = divmod(e, 3600)
        m, s = divmod(r, 60)
        self._uptime_lbl.setText(f"{h:02d}:{m:02d}:{s:02d}")


class _SidePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_C_BG};")
        self.setMinimumWidth(260)
        self.setMaximumWidth(340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        fps_hdr = QLabel("FPS")
        fps_hdr.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        fps_hdr.setStyleSheet(f"color: {_C_TEXT};")
        layout.addWidget(fps_hdr)

        self.fps_graph = FPSGraph()
        self.fps_graph.setFixedHeight(120)
        layout.addWidget(self.fps_graph)

        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet(f"background: {_C_BORDER};")
        line1.setFixedHeight(1)
        layout.addWidget(line1)

        self.worker_panel = WorkerPanel()
        self.worker_panel.setFixedHeight(200)
        layout.addWidget(self.worker_panel)

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet(f"background: {_C_BORDER};")
        line2.setFixedHeight(1)
        layout.addWidget(line2)

        self.metrics_panel = MetricsPanel()
        layout.addWidget(self.metrics_panel)
        layout.addStretch()


class HuntEyeDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HuntEye â€” Operator Dashboard")
        self.setMinimumSize(920, 600)
        self.setStyleSheet(_BASE_STYLE)
        self._build_ui()

    def update_camera(self, frame, fps=0.0, detections=None, active_target=None, mode="SIM"):
        self._cam_view.set_frame(frame, fps, detections, active_target, mode)
        self._title_bar.set_mode(mode)

    def update_fps(self, fps):
        self._side.fps_graph.update_fps(fps)
        self._title_bar.tick_uptime()
        self.statusBar().showMessage(
            f"FPS: {fps:.1f}  |  HuntEye Dev 1.2  |  {time.strftime('%H:%M:%S')}"
        )

    def update_workers(self, status_dict):
        self._side.worker_panel.update_workers(status_dict)

    def update_metrics(self, data):
        self._side.metrics_panel.update_metrics(data)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._title_bar = _TitleBar()
        root.addWidget(self._title_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        self._cam_view = CameraView()
        splitter.addWidget(self._cam_view)

        self._side = _SidePanel()
        splitter.addWidget(self._side)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, stretch=1)

        self.setStatusBar(QStatusBar())
        self._side.metrics_panel.start()

    def closeEvent(self, event):
        self._side.metrics_panel.stop()
        super().closeEvent(event)
