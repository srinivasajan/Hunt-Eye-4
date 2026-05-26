from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QLabel, QPushButton)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from qt_ui.widgets.diagnostics_panel import DiagnosticsPanel

_C_BG      = "#0d1117"
_C_SURFACE = "#161b22"
_C_BORDER  = "#30363d"
_C_TEXT    = "#c9d1d9"
_C_ACCENT  = "#3fb950"
_C_MUTED   = "#8b949e"

_STYLE = f"""
    QMainWindow, QWidget {{
        background: {_C_BG};
        color: {_C_TEXT};
        font-family: Consolas, monospace;
    }}
    QLabel {{ background: transparent; }}
"""


class DiagnosticsWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HuntEye â€” Diagnostics")
        self.setMinimumSize(700, 500)
        self.setStyleSheet(_STYLE)
        self._build_ui()
        self._demo_timer = None

    def log(self, level, message):
        self._panel.log(level, message)

    def update_workers(self, status_dict):
        self._panel.update_workers(status_dict)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        title_bar = QWidget()
        title_bar.setFixedHeight(44)
        title_bar.setStyleSheet(
            f"background: {_C_SURFACE}; border-bottom: 1px solid {_C_BORDER};"
        )
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(16, 0, 16, 0)

        title_lbl = QLabel("DIAGNOSTICS")
        title_lbl.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {_C_ACCENT};")
        tb_layout.addWidget(title_lbl)
        tb_layout.addStretch()

        clear_btn = QPushButton("Clear Logs")
        clear_btn.setFixedSize(80, 26)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_C_SURFACE};
                color: {_C_MUTED};
                border: 1px solid {_C_BORDER};
                border-radius: 4px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                color: {_C_TEXT};
                border-color: {_C_MUTED};
            }}
        """)
        clear_btn.clicked.connect(lambda: self._panel.log_viewer.clear())
        tb_layout.addWidget(clear_btn)
        root.addWidget(title_bar)

        self._panel = DiagnosticsPanel()
        self._panel.worker_restart_requested.connect(self._on_restart)
        root.addWidget(self._panel, stretch=1)

    def _on_restart(self, worker_name):
        self._panel.log("WARNING", f"{worker_name} restart signal sent")

    def start_demo_logs(self):
        import random
        levels   = ["INFO", "INFO", "WARNING", "ERROR", "DEBUG"]
        messages = [
            "Frame captured successfully",
            "SharedState updated",
            "Camera latency high: 45ms",
            "Worker heartbeat missed",
            "Detection threshold: 0.87",
            "MAVLink ping: 12ms",
        ]
        def _emit():
            self._panel.log(random.choice(levels), random.choice(messages))
        self._demo_timer = QTimer()
        self._demo_timer.setInterval(1500)
        self._demo_timer.timeout.connect(_emit)
        self._demo_timer.start()
        self._panel.log("INFO", "HuntEye Diagnostics started")
