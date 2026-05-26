from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QFrame, QScrollArea)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

_C_ALIVE   = "#3fb950"
_C_STALLED = "#d29922"
_C_DEAD    = "#f85149"
_C_BG      = "#0d1117"
_C_CARD    = "#161b22"
_C_BORDER  = "#30363d"
_C_TEXT    = "#c9d1d9"
_C_MUTED   = "#8b949e"


class WorkerRow(QFrame):
    STALL_THRESHOLD = 1.0

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"QFrame {{ background: {_C_CARD}; border: 1px solid {_C_BORDER}; border-radius: 6px; }}")
        self.setFixedHeight(44)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)

        self._dot = QLabel("â—")
        self._dot.setFixedWidth(16)
        self._dot.setFont(QFont("Arial", 10))
        layout.addWidget(self._dot)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"color: {_C_TEXT}; font-size: 13px; background: transparent; border: none;")
        name_lbl.setFont(QFont("Consolas", 11))
        layout.addWidget(name_lbl, stretch=1)

        self._update_lbl = QLabel("â€”")
        self._update_lbl.setStyleSheet(f"color: {_C_MUTED}; font-size: 11px; background: transparent; border: none;")
        self._update_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._update_lbl)

        self._badge = QLabel("UNKNOWN")
        self._badge.setFixedWidth(64)
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self._badge.setStyleSheet("border-radius: 4px; padding: 2px 4px; border: none;")
        layout.addWidget(self._badge)

        self._set_status("unknown", 0.0, False)

    def refresh(self, alive, last_update, failed):
        if failed:
            state = "dead"
        elif alive and last_update > self.STALL_THRESHOLD:
            state = "stalled"
        elif alive:
            state = "alive"
        else:
            state = "dead"
        self._set_status(state, last_update, failed)

    def _set_status(self, state, last_update, failed):
        colors = {
            "alive":   (_C_ALIVE,   "#0d2117", "ALIVE"),
            "stalled": (_C_STALLED, "#1f1800", "STALLED"),
            "dead":    (_C_DEAD,    "#1f0d0d", "DEAD"),
            "unknown": (_C_MUTED,   "#161b22", "â€”"),
        }
        fg, bg, label = colors.get(state, colors["unknown"])
        self._dot.setStyleSheet(f"color: {fg}; background: transparent; border: none;")
        self._badge.setStyleSheet(
            f"background: {bg}; color: {fg}; border-radius: 4px; "
            f"padding: 2px 4px; font-size: 9px; font-weight: bold; border: none;"
        )
        self._badge.setText(label)
        if last_update > 0:
            self._update_lbl.setText(f"{last_update:.2f}s ago")
        else:
            self._update_lbl.setText("â€”")


class WorkerPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_C_BG};")
        self._rows = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QLabel("Worker Health")
        header.setStyleSheet(
            f"color: {_C_TEXT}; font-size: 12px; font-weight: bold; "
            f"padding: 8px 0 4px 2px; background: transparent;"
        )
        root.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: {_C_BG}; }}"
            f"QScrollBar:vertical {{ width: 6px; background: {_C_BG}; }}"
            f"QScrollBar::handle:vertical {{ background: {_C_BORDER}; border-radius: 3px; }}"
        )

        self._container = QWidget()
        self._container.setStyleSheet(f"background: {_C_BG};")
        self._list_layout = QVBoxLayout(self._container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()

        scroll.setWidget(self._container)
        root.addWidget(scroll, stretch=1)

    def update_workers(self, status_dict):
        for name, info in status_dict.items():
            if name not in self._rows:
                row = WorkerRow(name)
                self._list_layout.insertWidget(self._list_layout.count() - 1, row)
                self._rows[name] = row
            self._rows[name].refresh(
                alive=info.get("alive", False),
                last_update=info.get("last_update", 0.0),
                failed=info.get("failed", False),
            )
