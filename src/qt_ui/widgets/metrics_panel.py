import threading
import time
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QProgressBar, QFrame)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

_C_BG     = "#0d1117"
_C_CARD   = "#161b22"
_C_BORDER = "#30363d"
_C_TEXT   = "#c9d1d9"
_C_MUTED  = "#8b949e"

def _bar_color(pct):
    if pct >= 85: return "#f85149"
    if pct >= 60: return "#d29922"
    return "#3fb950"

def _bar_style(color):
    return f"""
        QProgressBar {{ background: #21262d; border-radius: 2px; border: none; }}
        QProgressBar::chunk {{ background: {color}; border-radius: 2px; }}
    """


class _MetricBar(QFrame):
    def __init__(self, label, unit="%", parent=None):
        super().__init__(parent)
        self._unit = unit
        self.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(3)

        self._name_lbl = QLabel(label)
        self._name_lbl.setStyleSheet(f"color: {_C_MUTED}; font-size: 11px;")
        layout.addWidget(self._name_lbl)

        self._val_lbl = QLabel("â€”")
        self._val_lbl.setStyleSheet(f"color: {_C_TEXT}; font-size: 13px; font-weight: bold;")
        self._val_lbl.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        layout.addWidget(self._val_lbl)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(5)
        self._bar.setStyleSheet(_bar_style("#3fb950"))
        layout.addWidget(self._bar)

    def set_value(self, value, max_val=100.0):
        pct = min(int(value / max_val * 100), 100)
        self._bar.setValue(pct)
        self._bar.setStyleSheet(_bar_style(_bar_color(pct)))
        if self._unit == "%":
            self._val_lbl.setText(f"{value:.1f}%")
        else:
            self._val_lbl.setText(f"{value:.0f} C")

    def set_na(self):
        self._val_lbl.setText("N/A")
        self._bar.setValue(0)


class MetricsCollector(threading.Thread):
    def __init__(self, callback, interval=1.0):
        super().__init__(daemon=True)
        self._callback = callback
        self._interval = interval
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            data = {"cpu_pct": 0.0, "ram_pct": 0.0, "gpu_pct": None, "gpu_temp": None}
            if _HAS_PSUTIL:
                data["cpu_pct"] = psutil.cpu_percent(interval=None)
                data["ram_pct"] = psutil.virtual_memory().percent
            self._callback(data)
            time.sleep(self._interval)

    def stop(self):
        self._stop_event.set()


class MetricsPanel(QWidget):
    _sig_update = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._collector = None
        self.setStyleSheet(f"background: {_C_BG};")
        self._sig_update.connect(self._apply_metrics)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        header = QLabel("System Metrics")
        header.setStyleSheet(f"color: {_C_TEXT}; font-size: 12px; font-weight: bold; background: transparent;")
        layout.addWidget(header)

        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background: {_C_CARD}; border: 1px solid {_C_BORDER}; border-radius: 8px; }}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 8, 12, 12)
        card_layout.setSpacing(6)

        self._cpu_bar = _MetricBar("CPU")
        self._ram_bar = _MetricBar("RAM")
        self._gpu_bar = _MetricBar("GPU")

        for bar in (self._cpu_bar, self._ram_bar, self._gpu_bar):
            card_layout.addWidget(bar)

        layout.addWidget(card)
        layout.addStretch()

    def start(self):
        if self._collector is None:
            self._collector = MetricsCollector(
                callback=lambda d: self._sig_update.emit(d)
            )
            self._collector.start()

    def stop(self):
        if self._collector:
            self._collector.stop()
            self._collector = None

    def update_metrics(self, data):
        self._sig_update.emit(data)

    def _apply_metrics(self, data):
        self._cpu_bar.set_value(data.get("cpu_pct", 0.0))
        self._ram_bar.set_value(data.get("ram_pct", 0.0))
        gpu = data.get("gpu_pct")
        if gpu is not None:
            self._gpu_bar.set_value(gpu)
        else:
            self._gpu_bar.set_na()

    def closeEvent(self, event):
        self.stop()
        super().closeEvent(event)
