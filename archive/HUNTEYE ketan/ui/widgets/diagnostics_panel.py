import time
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QFrame, QTextEdit, QPushButton)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor

_C_BG     = "#0d1117"
_C_CARD   = "#161b22"
_C_BORDER = "#30363d"
_C_TEXT   = "#c9d1d9"
_C_MUTED  = "#8b949e"
_C_GREEN  = "#3fb950"
_C_RED    = "#f85149"
_C_YELLOW = "#d29922"
_C_BLUE   = "#58a6ff"


class LogViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_C_BG};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel("System Logs")
        title.setStyleSheet(f"color: {_C_TEXT}; font-size: 12px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedSize(50, 22)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_C_CARD};
                color: {_C_MUTED};
                border: 1px solid {_C_BORDER};
                border-radius: 4px;
                font-size: 11px;
            }}
            QPushButton:hover {{ color: {_C_TEXT}; border-color: {_C_MUTED}; }}
        """)
        clear_btn.clicked.connect(self.clear)
        header.addWidget(clear_btn)
        layout.addLayout(header)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFont(QFont("Consolas", 10))
        self._log.setStyleSheet(f"""
            QTextEdit {{
                background: {_C_CARD};
                color: {_C_TEXT};
                border: 1px solid {_C_BORDER};
                border-radius: 6px;
                padding: 8px;
            }}
            QScrollBar:vertical {{ width: 6px; background: {_C_BG}; }}
            QScrollBar::handle:vertical {{ background: {_C_BORDER}; border-radius: 3px; }}
        """)
        layout.addWidget(self._log, stretch=1)

    def append(self, level, message):
        colors = {
            "INFO":    _C_GREEN,
            "WARNING": _C_YELLOW,
            "ERROR":   _C_RED,
            "DEBUG":   _C_BLUE,
        }
        color = colors.get(level.upper(), _C_MUTED)
        ts    = time.strftime("%H:%M:%S")
        html  = (
            f'<span style="color:{_C_MUTED};">[{ts}]</span> '
            f'<span style="color:{color};font-weight:bold;">[{level}]</span> '
            f'<span style="color:{_C_TEXT};">{message}</span>'
        )
        self._log.append(html)
        self._log.moveCursor(QTextCursor.MoveOperation.End)

    def clear(self):
        self._log.clear()


class WorkerControlRow(QFrame):
    restart_requested = pyqtSignal(str)

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.worker_name = name
        self.setFixedHeight(44)
        self.setStyleSheet(f"QFrame {{ background: {_C_CARD}; border: 1px solid {_C_BORDER}; border-radius: 6px; }}")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)

        self._dot = QLabel("●")
        self._dot.setFixedWidth(14)
        self._dot.setStyleSheet(f"color: {_C_MUTED}; background: transparent; border: none;")
        layout.addWidget(self._dot)

        name_lbl = QLabel(name)
        name_lbl.setFont(QFont("Consolas", 11))
        name_lbl.setStyleSheet(f"color: {_C_TEXT}; background: transparent; border: none;")
        layout.addWidget(name_lbl, stretch=1)

        self._status_lbl = QLabel("—")
        self._status_lbl.setStyleSheet(f"color: {_C_MUTED}; font-size: 11px; background: transparent; border: none;")
        layout.addWidget(self._status_lbl)

        restart_btn = QPushButton("Restart")
        restart_btn.setFixedSize(60, 24)
        restart_btn.setStyleSheet(f"""
            QPushButton {{
                background: #1f1800;
                color: {_C_YELLOW};
                border: 1px solid {_C_YELLOW};
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #2d2200; }}
        """)
        restart_btn.clicked.connect(lambda: self.restart_requested.emit(self.worker_name))
        layout.addWidget(restart_btn)

    def set_status(self, alive, failed):
        if failed:
            color, text = _C_RED, "FAILED"
        elif alive:
            color, text = _C_GREEN, "ALIVE"
        else:
            color, text = _C_RED, "DEAD"
        self._dot.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        self._status_lbl.setText(text)
        self._status_lbl.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent; border: none;")


class DiagnosticsPanel(QWidget):
    worker_restart_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_C_BG};")
        self._worker_rows = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        self.log_viewer = LogViewer()
        layout.addWidget(self.log_viewer, stretch=2)

        ctrl_hdr = QLabel("Worker Controls")
        ctrl_hdr.setStyleSheet(f"color: {_C_TEXT}; font-size: 12px; font-weight: bold;")
        layout.addWidget(ctrl_hdr)

        self._workers_layout = QVBoxLayout()
        self._workers_layout.setSpacing(4)
        layout.addLayout(self._workers_layout)

    def log(self, level, message):
        self.log_viewer.append(level, message)

    def update_workers(self, status_dict):
        for name, info in status_dict.items():
            if name not in self._worker_rows:
                row = WorkerControlRow(name)
                row.restart_requested.connect(self._on_restart)
                self._workers_layout.addWidget(row)
                self._worker_rows[name] = row
            self._worker_rows[name].set_status(
                alive=info.get("alive", False),
                failed=info.get("failed", False),
            )

    def _on_restart(self, worker_name):
        self.log("WARNING", f"Restart requested: {worker_name}")
        self.worker_restart_requested.emit(worker_name)