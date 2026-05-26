import math
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QFrame,
                              QScrollArea, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QPointF
from PyQt6.QtGui import (QPainter, QColor, QPen, QFont,
                          QBrush, QPainterPath)

_C_BG     = "#0d1117"
_C_CARD   = "#161b22"
_C_BORDER = "#30363d"
_C_TEXT   = "#c9d1d9"
_C_MUTED  = "#8b949e"
_C_GREEN  = "#3fb950"
_C_RED    = "#f85149"
_C_YELLOW = "#d29922"
_C_BLUE   = "#58a6ff"


class WaypointMap(QWidget):
    waypoint_added = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._waypoints = []
        self._drone_pos = (0.5, 0.5)
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background: {_C_CARD}; border: 1px solid {_C_BORDER}; border-radius: 8px;")
        self.setToolTip("Click to add waypoints")

    def set_drone_pos(self, nx, ny):
        self._drone_pos = (nx, ny)
        self.update()

    def clear_waypoints(self):
        self._waypoints.clear()
        self.update()

    def get_waypoints(self):
        return list(self._waypoints)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            nx = event.position().x() / self.width()
            ny = event.position().y() / self.height()
            self._waypoints.append((nx, ny))
            self.waypoint_added.emit(nx, ny)
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        p.fillRect(0, 0, w, h, QColor(_C_CARD))

        # Grid
        p.setPen(QPen(QColor(_C_BORDER), 1, Qt.PenStyle.DashLine))
        for i in range(1, 5):
            x = int(w * i / 5)
            y = int(h * i / 5)
            p.drawLine(x, 0, x, h)
            p.drawLine(0, y, w, y)

        # Path lines
        if len(self._waypoints) > 1:
            path_pen = QPen(QColor(_C_BLUE), 2, Qt.PenStyle.DashLine)
            p.setPen(path_pen)
            for i in range(len(self._waypoints) - 1):
                x1 = int(self._waypoints[i][0] * w)
                y1 = int(self._waypoints[i][1] * h)
                x2 = int(self._waypoints[i+1][0] * w)
                y2 = int(self._waypoints[i+1][1] * h)
                p.drawLine(x1, y1, x2, y2)

        # Waypoints
        for i, (nx, ny) in enumerate(self._waypoints):
            x = int(nx * w)
            y = int(ny * h)
            p.setBrush(QBrush(QColor(_C_BLUE)))
            p.setPen(QPen(QColor("#ffffff"), 1))
            p.drawEllipse(x - 10, y - 10, 20, 20)
            p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            p.setPen(QColor("#ffffff"))
            p.drawText(x - 4, y + 4, str(i + 1))

        # Drone
        dx = int(self._drone_pos[0] * w)
        dy = int(self._drone_pos[1] * h)
        p.setBrush(QBrush(QColor(_C_GREEN)))
        p.setPen(QPen(QColor(_C_GREEN), 2))
        p.drawEllipse(dx - 8, dy - 8, 16, 16)
        p.setFont(QFont("Consolas", 8))
        p.setPen(QColor(_C_GREEN))
        p.drawText(dx + 10, dy + 4, "DRONE")
        p.end()


class MissionPlanner(QWidget):
    mission_started  = pyqtSignal(list)
    mission_cleared  = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_C_BG};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Title
        title = QLabel("Mission Planner")
        title.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_C_TEXT};")
        layout.addWidget(title)

        hint = QLabel("Click on map to add waypoints")
        hint.setStyleSheet(f"color: {_C_MUTED}; font-size: 11px;")
        layout.addWidget(hint)

        # Map
        self._map = WaypointMap()
        self._map.waypoint_added.connect(self._on_waypoint_added)
        layout.addWidget(self._map, stretch=1)

        # Waypoint count
        self._count_lbl = QLabel("Waypoints: 0")
        self._count_lbl.setStyleSheet(f"color: {_C_MUTED}; font-size: 11px;")
        layout.addWidget(self._count_lbl)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._start_btn = QPushButton("â–¶  START MISSION")
        self._start_btn.setFixedHeight(38)
        self._start_btn.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self._start_btn.setStyleSheet(f"""
            QPushButton {{
                background: #0d2117;
                color: {_C_GREEN};
                border: 1px solid {_C_GREEN};
                border-radius: 6px;
            }}
            QPushButton:hover {{ background: #1a3d2b; }}
            QPushButton:disabled {{ color: {_C_MUTED}; border-color: {_C_BORDER}; background: {_C_CARD}; }}
        """)
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._start_mission)
        btn_row.addWidget(self._start_btn)

        clear_btn = QPushButton("âœ•  CLEAR")
        clear_btn.setFixedHeight(38)
        clear_btn.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: #1f0d0d;
                color: {_C_RED};
                border: 1px solid {_C_RED};
                border-radius: 6px;
            }}
            QPushButton:hover {{ background: #2d1515; }}
        """)
        clear_btn.clicked.connect(self._clear)
        btn_row.addWidget(clear_btn)
        layout.addLayout(btn_row)

        # Waypoint list
        list_hdr = QLabel("Waypoint List")
        list_hdr.setStyleSheet(f"color: {_C_TEXT}; font-size: 12px; font-weight: bold;")
        layout.addWidget(list_hdr)

        self._wp_list_layout = QVBoxLayout()
        self._wp_list_layout.setSpacing(3)
        layout.addLayout(self._wp_list_layout)
        layout.addStretch()

    def update_drone_pos(self, nx, ny):
        self._map.set_drone_pos(nx, ny)

    def _on_waypoint_added(self, nx, ny):
        count = len(self._map.get_waypoints())
        self._count_lbl.setText(f"Waypoints: {count}")
        self._start_btn.setEnabled(count > 0)

        card = QFrame()
        card.setFixedHeight(32)
        card.setStyleSheet(f"QFrame {{ background: {_C_CARD}; border: 1px solid {_C_BORDER}; border-radius: 4px; }}")
        row = QHBoxLayout(card)
        row.setContentsMargins(8, 0, 8, 0)

        lbl = QLabel(f"WP {count}  â†’  x:{nx:.2f}  y:{ny:.2f}")
        lbl.setFont(QFont("Consolas", 10))
        lbl.setStyleSheet(f"color: {_C_TEXT}; background: transparent; border: none;")
        row.addWidget(lbl)
        self._wp_list_layout.addWidget(card)

    def _start_mission(self):
        wps = self._map.get_waypoints()
        self.mission_started.emit(wps)
        self._start_btn.setEnabled(False)
        self._start_btn.setText("â–¶  MISSION RUNNING")

    def _clear(self):
        self._map.clear_waypoints()
        self._count_lbl.setText("Waypoints: 0")
        self._start_btn.setEnabled(False)
        self._start_btn.setText("â–¶  START MISSION")
        while self._wp_list_layout.count():
            item = self._wp_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.mission_cleared.emit()
