import numpy as np
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont

_C_BG      = "#0d1117"
_C_OVERLAY = "#3fb950"
_C_TARGET  = "#f85149"
_C_BADGE   = "#1f3a1f"


class CameraView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._fps = 0.0
        self._mode = "SIM"
        self._detections = []
        self._active_target = None
        self.setStyleSheet(f"background: {_C_BG};")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(320, 240)

    def set_frame(self, frame, fps=0.0, detections=None, active_target=None, mode="SIM"):
        self._fps           = fps
        self._detections    = detections or []
        self._active_target = active_target
        self._mode          = mode
        self._pixmap        = self._bgr_to_pixmap(frame)
        self.update()

    def set_no_signal(self):
        self._pixmap = None
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        w, h = self.width(), self.height()

        if self._pixmap is None:
            p.fillRect(0, 0, w, h, QColor("#0d1117"))
            p.setPen(QColor("#30363d"))
            p.setFont(QFont("Consolas", 14))
            p.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "[ NO SIGNAL ]")
            p.end()
            return

        scaled = self._pixmap.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        ox = (w - scaled.width())  // 2
        oy = (h - scaled.height()) // 2
        p.drawPixmap(ox, oy, scaled)

        sx = scaled.width()  / self._pixmap.width()
        sy = scaled.height() / self._pixmap.height()

        for det in self._detections:
            bbox  = det.get("bbox", (0, 0, 0, 0))
            label = det.get("label", "obj")
            conf  = det.get("conf", 0.0)
            self._draw_bbox(p, bbox, label, conf, ox, oy, sx, sy, QColor(_C_OVERLAY))

        if self._active_target:
            bbox = self._active_target.get("bbox", (0, 0, 0, 0))
            self._draw_bbox(p, bbox, "TARGET", 1.0, ox, oy, sx, sy, QColor(_C_TARGET), thick=2)

        p.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        p.setPen(QColor(_C_OVERLAY))
        p.drawText(ox + 8, oy + 20, f"FPS {self._fps:.1f}")

        badge_w, badge_h = 50, 20
        badge_x = ox + scaled.width() - badge_w - 8
        badge_y = oy + 8
        p.fillRect(badge_x, badge_y, badge_w, badge_h, QColor(_C_BADGE))
        p.setPen(QColor(_C_OVERLAY))
        p.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        p.drawText(badge_x, badge_y, badge_w, badge_h, Qt.AlignmentFlag.AlignCenter, self._mode)
        p.end()

    @staticmethod
    def _bgr_to_pixmap(frame):
        if frame.ndim == 2:
            h, w = frame.shape
            img = QImage(frame.data, w, h, w, QImage.Format.Format_Grayscale8)
        else:
            rgb = frame[:, :, ::-1].copy()
            h, w, ch = rgb.shape
            img = QImage(rgb.data, w, h, w * ch, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(img)

    @staticmethod
    def _draw_bbox(painter, bbox, label, conf, ox, oy, sx, sy, color, thick=1):
        x, y, bw, bh = bbox
        rx = ox + int(x  * sx)
        ry = oy + int(y  * sy)
        rw = int(bw * sx)
        rh = int(bh * sy)
        painter.setPen(QPen(color, thick))
        painter.drawRect(rx, ry, rw, rh)
        painter.setFont(QFont("Consolas", 9))
        text = f"{label} {conf:.0%}"
        fm   = painter.fontMetrics()
        tw   = fm.horizontalAdvance(text) + 6
        th   = fm.height()
        painter.fillRect(rx, ry - th - 2, tw, th + 2, color)
        painter.setPen(QColor("#000000"))
        painter.drawText(rx + 3, ry - 3, text)
