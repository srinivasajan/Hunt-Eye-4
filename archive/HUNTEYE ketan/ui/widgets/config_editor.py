from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QFrame,
                              QLineEdit, QSpinBox, QDoubleSpinBox,
                              QScrollArea)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont

_C_BG     = "#0d1117"
_C_CARD   = "#161b22"
_C_BORDER = "#30363d"
_C_TEXT   = "#c9d1d9"
_C_MUTED  = "#8b949e"
_C_GREEN  = "#3fb950"
_C_RED    = "#f85149"
_C_YELLOW = "#d29922"

DEFAULT_CONFIG = {
    "Camera": {
        "fps_target": 60,
        "resolution_w": 640,
        "resolution_h": 480,
        "exposure": 0.033,
    },
    "Detector": {
        "confidence_threshold": 0.75,
        "nms_threshold": 0.45,
        "max_detections": 10,
    },
    "Tracker": {
        "max_lost_frames": 5,
        "iou_threshold": 0.3,
    },
    "Control": {
        "max_speed": 5.0,
        "altitude": 10.0,
        "hover_time": 2.0,
    },
    "System": {
        "log_level": "INFO",
        "airsim_ip": "127.0.0.1",
        "airsim_port": 41451,
    },
}


class ConfigRow(QFrame):
    value_changed = pyqtSignal(str, str, object)

    def __init__(self, section, key, value, parent=None):
        super().__init__(parent)
        self._section = section
        self._key = key
        self.setFixedHeight(40)
        self.setStyleSheet(f"QFrame {{ background: {_C_CARD}; border: 1px solid {_C_BORDER}; border-radius: 4px; }}")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        key_lbl = QLabel(key)
        key_lbl.setFont(QFont("Consolas", 10))
        key_lbl.setFixedWidth(180)
        key_lbl.setStyleSheet(f"color: {_C_TEXT}; background: transparent; border: none;")
        layout.addWidget(key_lbl)
        self._input = self._make_input(value)
        layout.addWidget(self._input, stretch=1)

    def _make_input(self, value):
        if isinstance(value, int):
            spin = QSpinBox()
            spin.setRange(0, 99999)
            spin.setValue(value)
            spin.setFixedHeight(26)
            spin.setFont(QFont("Consolas", 10))
            spin.setStyleSheet(f"QSpinBox {{ background: {_C_BG}; color: {_C_TEXT}; border: 1px solid {_C_BORDER}; border-radius: 4px; padding: 2px; }}")
            spin.valueChanged.connect(lambda v: self.value_changed.emit(self._section, self._key, v))
            return spin
        elif isinstance(value, float):
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 9999.0)
            spin.setValue(value)
            spin.setDecimals(3)
            spin.setSingleStep(0.01)
            spin.setFixedHeight(26)
            spin.setFont(QFont("Consolas", 10))
            spin.setStyleSheet(f"QDoubleSpinBox {{ background: {_C_BG}; color: {_C_TEXT}; border: 1px solid {_C_BORDER}; border-radius: 4px; padding: 2px; }}")
            spin.valueChanged.connect(lambda v: self.value_changed.emit(self._section, self._key, v))
            return spin
        else:
            edit = QLineEdit(str(value))
            edit.setFixedHeight(26)
            edit.setFont(QFont("Consolas", 10))
            edit.setStyleSheet(f"QLineEdit {{ background: {_C_BG}; color: {_C_TEXT}; border: 1px solid {_C_BORDER}; border-radius: 4px; padding: 2px 6px; }}")
            edit.textChanged.connect(lambda v: self.value_changed.emit(self._section, self._key, v))
            return edit

    def get_value(self):
        if isinstance(self._input, (QSpinBox, QDoubleSpinBox)):
            return self._input.value()
        else:
            return self._input.text()


class ConfigEditor(QWidget):
    config_saved = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_C_BG};")
        self._config = {s: dict(v) for s, v in DEFAULT_CONFIG.items()}
        self._rows = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        title = QLabel("Config Editor")
        title.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_C_TEXT};")
        layout.addWidget(title)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {_C_BG}; }} QScrollBar:vertical {{ width: 6px; background: {_C_BG}; }} QScrollBar::handle:vertical {{ background: {_C_BORDER}; border-radius: 3px; }}")
        container = QWidget()
        container.setStyleSheet(f"background: {_C_BG};")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(12)
        for section, values in DEFAULT_CONFIG.items():
            self._rows[section] = {}
            sec_lbl = QLabel(section)
            sec_lbl.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
            sec_lbl.setStyleSheet(f"color: {_C_YELLOW}; padding: 4px 0;")
            container_layout.addWidget(sec_lbl)
            for key, value in values.items():
                row = ConfigRow(section, key, value)
                row.value_changed.connect(self._on_value_changed)
                container_layout.addWidget(row)
                self._rows[section][key] = row
        container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        save_btn = QPushButton("SAVE CONFIG")
        save_btn.setFixedHeight(38)
        save_btn.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        save_btn.setStyleSheet(f"QPushButton {{ background: #0d2117; color: {_C_GREEN}; border: 1px solid {_C_GREEN}; border-radius: 6px; }} QPushButton:hover {{ background: #1a3d2b; }}")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        reset_btn = QPushButton("RESET")
        reset_btn.setFixedHeight(38)
        reset_btn.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        reset_btn.setStyleSheet(f"QPushButton {{ background: #1f1800; color: {_C_YELLOW}; border: 1px solid {_C_YELLOW}; border-radius: 6px; }} QPushButton:hover {{ background: #2d2200; }}")
        reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(reset_btn)
        layout.addLayout(btn_row)

    def _on_value_changed(self, section, key, value):
        self._config[section][key] = value

    def _save(self):
        self.config_saved.emit(self._config)

    def _reset(self):
        self._config = {s: dict(v) for s, v in DEFAULT_CONFIG.items()}

    def get_config(self):
        return self._config
    