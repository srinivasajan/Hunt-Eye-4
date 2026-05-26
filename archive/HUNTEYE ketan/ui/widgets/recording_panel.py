import os
import time
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QFrame, QFileDialog)
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtGui import QFont

_C_BG     = "#0d1117"
_C_CARD   = "#161b22"
_C_BORDER = "#30363d"
_C_TEXT   = "#c9d1d9"
_C_MUTED  = "#8b949e"
_C_GREEN  = "#3fb950"
_C_RED    = "#f85149"


class RecordingPanel(QWidget):
    recording_started = pyqtSignal(str)
    recording_stopped = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_C_BG};")
        self._recording = False
        self._start_time = None
        self._save_path = "recordings"
        self._elapsed_timer = QTimer()
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._update_elapsed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        title = QLabel("Recording System")
        title.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_C_TEXT};")
        layout.addWidget(title)

        status_card = QFrame()
        status_card.setStyleSheet(f"QFrame {{ background: {_C_CARD}; border: 1px solid {_C_BORDER}; border-radius: 8px; }}")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(12, 12, 12, 12)
        status_layout.setSpacing(8)

        status_row = QHBoxLayout()
        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet(f"color: {_C_MUTED}; background: transparent; border: none;")
        self._status_dot.setFont(QFont("Arial", 14))
        status_row.addWidget(self._status_dot)

        self._status_lbl = QLabel("NOT RECORDING")
        self._status_lbl.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self._status_lbl.setStyleSheet(f"color: {_C_MUTED}; background: transparent; border: none;")
        status_row.addWidget(self._status_lbl)
        status_row.addStretch()

        self._elapsed_lbl = QLabel("00:00:00")
        self._elapsed_lbl.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        self._elapsed_lbl.setStyleSheet(f"color: {_C_MUTED}; background: transparent; border: none;")
        status_row.addWidget(self._elapsed_lbl)
        status_layout.addLayout(status_row)

        path_row = QHBoxLayout()
        path_lbl = QLabel("Save to:")
        path_lbl.setStyleSheet(f"color: {_C_MUTED}; font-size: 11px; background: transparent; border: none;")
        path_row.addWidget(path_lbl)

        self._path_lbl = QLabel(self._save_path)
        self._path_lbl.setStyleSheet(f"color: {_C_TEXT}; font-size: 11px; background: transparent; border: none;")
        path_row.addWidget(self._path_lbl, stretch=1)

        browse_btn = QPushButton("Browse")
        browse_btn.setFixedSize(55, 22)
        browse_btn.setStyleSheet(f"QPushButton {{ background: {_C_CARD}; color: {_C_MUTED}; border: 1px solid {_C_BORDER}; border-radius: 4px; font-size: 10px; }} QPushButton:hover {{ color: {_C_TEXT}; }}")
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(browse_btn)
        status_layout.addLayout(path_row)
        layout.addWidget(status_card)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._rec_btn = QPushButton("⏺  START RECORDING")
        self._rec_btn.setFixedHeight(40)
        self._rec_btn.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self._rec_btn.setStyleSheet(f"QPushButton {{ background: #0d2117; color: {_C_GREEN}; border: 1px solid {_C_GREEN}; border-radius: 6px; }} QPushButton:hover {{ background: #1a3d2b; }}")
        self._rec_btn.clicked.connect(self._start_recording)
        btn_row.addWidget(self._rec_btn)

        self._stop_btn = QPushButton("⏹  STOP")
        self._stop_btn.setFixedHeight(40)
        self._stop_btn.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet(f"QPushButton {{ background: #1f0d0d; color: {_C_RED}; border: 1px solid {_C_RED}; border-radius: 6px; }} QPushButton:hover {{ background: #2d1515; }} QPushButton:disabled {{ color: {_C_MUTED}; border-color: {_C_BORDER}; background: {_C_CARD}; }}")
        self._stop_btn.clicked.connect(self._stop_recording)
        btn_row.addWidget(self._stop_btn)
        layout.addLayout(btn_row)

        list_hdr = QLabel("Saved Recordings")
        list_hdr.setStyleSheet(f"color: {_C_TEXT}; font-size: 12px; font-weight: bold;")
        layout.addWidget(list_hdr)

        self._recordings_layout = QVBoxLayout()
        self._recordings_layout.setSpacing(4)
        layout.addLayout(self._recordings_layout)
        layout.addStretch()

    def add_recording_entry(self, filename, duration, size):
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background: {_C_CARD}; border: 1px solid {_C_BORDER}; border-radius: 6px; }}")
        card.setFixedHeight(44)
        row = QHBoxLayout(card)
        row.setContentsMargins(10, 0, 10, 0)

        name_lbl = QLabel(filename)
        name_lbl.setFont(QFont("Consolas", 10))
        name_lbl.setStyleSheet(f"color: {_C_TEXT}; background: transparent; border: none;")
        row.addWidget(name_lbl, stretch=1)

        dur_lbl = QLabel(duration)
        dur_lbl.setStyleSheet(f"color: {_C_MUTED}; font-size: 10px; background: transparent; border: none;")
        row.addWidget(dur_lbl)

        play_btn = QPushButton("▶ Play")
        play_btn.setFixedSize(55, 24)
        play_btn.setStyleSheet(f"QPushButton {{ background: #0d2117; color: {_C_GREEN}; border: 1px solid {_C_GREEN}; border-radius: 4px; font-size: 10px; }} QPushButton:hover {{ background: #1a3d2b; }}")
        row.addWidget(play_btn)
        self._recordings_layout.addWidget(card)

    def _start_recording(self):
        self._recording = True
        self._start_time = time.time()
        self._status_dot.setStyleSheet(f"color: {_C_RED}; background: transparent; border: none;")
        self._status_lbl.setText("RECORDING")
        self._status_lbl.setStyleSheet(f"color: {_C_RED}; font-weight: bold; background: transparent; border: none;")
        self._rec_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._elapsed_timer.start()
        filename = f"rec_{time.strftime('%Y%m%d_%H%M%S')}"
        self.recording_started.emit(os.path.join(self._save_path, filename))

    def _stop_recording(self):
        self._recording = False
        self._elapsed_timer.stop()
        elapsed = int(time.time() - self._start_time) if self._start_time else 0
        h, r = divmod(elapsed, 3600)
        m, s = divmod(r, 60)
        duration = f"{h:02d}:{m:02d}:{s:02d}"
        filename = f"rec_{time.strftime('%Y%m%d_%H%M%S')}.npy"
        self._status_dot.setStyleSheet(f"color: {_C_MUTED}; background: transparent; border: none;")
        self._status_lbl.setText("NOT RECORDING")
        self._status_lbl.setStyleSheet(f"color: {_C_MUTED}; font-weight: bold; background: transparent; border: none;")
        self._elapsed_lbl.setText("00:00:00")
        self._rec_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self.add_recording_entry(filename, duration, "—")
        self.recording_stopped.emit()

    def _update_elapsed(self):
        if self._start_time:
            elapsed = int(time.time() - self._start_time)
            h, r = divmod(elapsed, 3600)
            m, s = divmod(r, 60)
            self._elapsed_lbl.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select Save Folder")
        if path:
            self._save_path = path
            self._path_lbl.setText(path)