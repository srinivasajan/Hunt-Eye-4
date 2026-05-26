from collections import deque
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath


class FPSGraph(QWidget):
    HISTORY_LEN = 120
    WARN_FPS    = 30
    CRIT_FPS    = 15
    TARGET_FPS  = 60

    def __init__(self, parent=None):
        super().__init__(parent)
        self._samples = deque([0.0] * self.HISTORY_LEN, maxlen=self.HISTORY_LEN)
        self._current_fps = 0.0
        self.setMinimumSize(260, 120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def update_fps(self, fps):
        self._current_fps = fps
        self._samples.append(fps)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pad  = 8

        p.fillRect(0, 0, w, h, QColor("#0d1117"))

        grid_pen = QPen(QColor("#1e2530"), 1, Qt.PenStyle.DashLine)
        p.setPen(grid_pen)
        for ratio in (0.25, 0.5, 0.75):
            y = pad + int((h - 2 * pad) * ratio)
            p.drawLine(pad, y, w - pad, y)

        target_y = self._fps_to_y(self.TARGET_FPS, h, pad)
        p.setPen(QPen(QColor("#2ea043"), 1, Qt.PenStyle.DashLine))
        p.drawLine(pad, target_y, w - pad, target_y)

        samples = list(self._samples)
        n       = len(samples)
        step_x  = (w - 2 * pad) / max(n - 1, 1)

        path = QPainterPath()
        started = False
        for i, fps in enumerate(samples):
            x = pad + i * step_x
            y = self._fps_to_y(fps, h, pad)
            if not started:
                path.moveTo(x, y)
                started = True
            else:
                path.lineTo(x, y)

        if self._current_fps < self.CRIT_FPS:
            line_color = QColor("#f85149")
        elif self._current_fps < self.WARN_FPS:
            line_color = QColor("#d29922")
        else:
            line_color = QColor("#3fb950")

        pen = QPen(line_color, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawPath(path)

        p.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        p.setPen(line_color)
        p.drawText(w - 72, pad + 16, f"{self._current_fps:.1f} fps")

        p.setFont(QFont("Consolas", 9))
        p.setPen(QColor("#2ea043"))
        p.drawText(pad + 4, target_y - 4, "60 fps")
        p.end()

    def _fps_to_y(self, fps, h, pad):
        max_fps = 80.0
        ratio   = 1.0 - min(fps / max_fps, 1.0)
        return int(pad + ratio * (h - 2 * pad))