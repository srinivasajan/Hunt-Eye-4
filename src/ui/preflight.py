"""preflight.py — Operator-readable startup splash renderer for HuntEye.

Renders staged startup screens into an existing OpenCV window.
Each stage maps to a human-readable action, not an engineering log label.
Used exclusively by main.py during the startup sequence.
"""

from __future__ import annotations

from typing import Optional
import time

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Stage definitions (operator language — not engineering language)
# ---------------------------------------------------------------------------

STAGES = [
    "Loading your settings...",
    "Starting subsystems...",
    "Connecting to camera source...",
    "Activating tracking engine...",
    "System ready.",
]

# Colours (BGR — matching dashboard dark theme)
_C_BG         = (17, 22, 13)    # #0d1611 near-black with green tint
_C_ACCENT     = (54, 134, 35)   # #238636 green
_C_TITLE      = (227, 237, 230) # #e6ede3 near-white
_C_TEXT       = (185, 195, 200) # body text
_C_MUTED      = (100, 110, 108) # muted
_C_WARN       = (34, 153, 210)  # amber (BGR)
_C_DONE       = (80, 185, 63)   # green check
_C_PENDING    = (70, 75, 80)    # grey pending
_C_PROGRESS   = (54, 134, 35)   # progress fill


def render_startup(
    window_name: str,
    step: int,
    total: int = len(STAGES),
    degraded: bool = False,
    degraded_reason: str = "",
    source: str = "SIMULATOR",
) -> None:
    """Render a single startup splash frame.

    Args:
        window_name:    OpenCV window name (reused across stages for seamless transition)
        step:           1-based current step index
        total:          total number of steps
        degraded:       True if HAL fell back to NullBackend
        degraded_reason: Short description of why degraded
        source:         "SIMULATOR" | "WEBCAM" | "DEMO"
    """
    W, H = 1024, 576
    frame = np.full((H, W, 3), _C_BG, dtype="uint8")

    # ── Accent bar (top) ──────────────────────────────────────────────
    cv2.rectangle(frame, (0, 0), (W, 4), _C_ACCENT, -1)

    # ── Logo / identity ───────────────────────────────────────────────
    _put(frame, "HUNT", (W // 2 - 130, H // 2 - 110),
         scale=1.8, color=_C_TITLE, thickness=3)
    _put(frame, "EYE",  (W // 2 + 4,  H // 2 - 110),
         scale=1.8, color=_C_ACCENT, thickness=3)

    _put(frame, "Autonomous Drone Tracking System",
         (W // 2 - 168, H // 2 - 70),
         scale=0.42, color=_C_MUTED)

    # ── Mode badge ────────────────────────────────────────────────────
    if degraded:
        badge_text = "NO CONNECTION — DEMO MODE"
        badge_color = _C_WARN
    else:
        badge_map = {
            "SIMULATOR": "SIMULATOR MODE",
            "WEBCAM":    "WEBCAM MODE",
            "DEMO":      "DEMO MODE",
        }
        badge_text  = badge_map.get(source, source + " MODE")
        badge_color = _C_DONE

    badge_x = W // 2 - 100
    badge_y = H // 2 - 44
    cv2.rectangle(frame,
                  (badge_x - 10, badge_y - 16),
                  (badge_x + 210, badge_y + 6),
                  _darken(badge_color), -1)
    _put(frame, badge_text, (badge_x, badge_y),
         scale=0.38, color=badge_color)

    # ── Stage list ────────────────────────────────────────────────────
    list_x  = W // 2 - 200
    list_y0 = H // 2 + 4
    line_h  = 26

    for i, label in enumerate(STAGES):
        stage_num = i + 1
        y = list_y0 + i * line_h

        if stage_num < step:
            # Completed
            dot   = "+"
            color = _C_DONE
        elif stage_num == step:
            # Current — pulse the dot slightly
            pulse = int(40 * abs(np.sin(time.time() * 3)))
            color = tuple(min(255, c + pulse) for c in _C_ACCENT)
            dot   = ">"
        else:
            # Pending
            dot   = "o"
            color = _C_PENDING

        _put(frame, f" {dot}  {label}", (list_x, y),
             scale=0.44, color=color)

    # ── Progress bar ──────────────────────────────────────────────────
    bar_x = W // 2 - 200
    bar_y = list_y0 + len(STAGES) * line_h + 16
    bar_w = 400
    bar_h = 5

    cv2.rectangle(frame,
                  (bar_x, bar_y),
                  (bar_x + bar_w, bar_y + bar_h),
                  (40, 45, 50), -1)
    filled = int(bar_w * (step / total))
    if filled > 0:
        cv2.rectangle(frame,
                      (bar_x, bar_y),
                      (bar_x + filled, bar_y + bar_h),
                      _C_PROGRESS, -1)

    # ── Degraded explanation ──────────────────────────────────────────
    if degraded:
        msg_y = bar_y + 28
        _put(frame, "No simulator or camera detected.",
             (bar_x, msg_y), scale=0.40, color=_C_WARN)
        _put(frame, "Running in Demo Mode — synthetic feed active.",
             (bar_x, msg_y + 20), scale=0.40, color=_C_MUTED)

    cv2.imshow(window_name, frame)
    cv2.waitKey(1)


def render_ready(
    window_name: str,
    degraded: bool,
    degraded_reason: str,
    source: str,
    ai_available: bool,
    depth_available: bool,
) -> None:
    """Render the READY state frame — shown before the operator starts a mission."""
    W, H = 1024, 576
    frame = np.full((H, W, 3), _C_BG, dtype="uint8")

    cv2.rectangle(frame, (0, 0), (W, 4), _C_ACCENT, -1)

    # Title
    if degraded:
        _put(frame, "DEMO MODE ACTIVE", (W // 2 - 148, 80),
             scale=1.0, color=_C_WARN, thickness=2)
        _put(frame, "No live input connected.",
             (W // 2 - 148, 116), scale=0.46, color=_C_MUTED)
    else:
        _put(frame, "SYSTEM READY", (W // 2 - 130, 80),
             scale=1.0, color=_C_DONE, thickness=2)
        src_label = {"SIMULATOR": "Simulator connected",
                     "WEBCAM":    "Camera connected",
                     "DEMO":      "Demo mode"}.get(source, source)
        _put(frame, src_label, (W // 2 - 130, 116),
             scale=0.46, color=_C_MUTED)

    # ── Capability summary ────────────────────────────────────────────
    cap_x = W // 2 - 200
    cap_y = 160

    _section_line(frame, cap_x, cap_y - 10, 400, _C_MUTED)
    _put(frame, "CAPABILITIES", (cap_x, cap_y + 6),
         scale=0.38, color=_C_MUTED)

    capabilities = [
        ("Live Camera Feed",    not degraded),
        ("AI Object Detection", ai_available),
        ("Depth Estimation",    depth_available),
        ("Waypoint Planning",   True),
        ("Session Recording",   True),
        ("Drone Control",       not degraded),
    ]

    col_w   = 200
    row_h   = 26
    for idx, (label, avail) in enumerate(capabilities):
        col = idx % 2
        row = idx // 2
        x   = cap_x + col * col_w
        y   = cap_y + 28 + row * row_h
        dot = "+" if avail else "-"
        col_color = _C_DONE if avail else _C_MUTED
        _put(frame, f" {dot}  {label}", (x, y),
             scale=0.42, color=col_color)

    # ── CTA ───────────────────────────────────────────────────────────
    cta_y = H // 2 + 90
    _section_line(frame, cap_x, cta_y - 16, 400, _C_MUTED)

    _put(frame, "Press  SPACE  to begin tracking",
         (cap_x, cta_y + 8), scale=0.56, color=_C_TITLE, thickness=1)

    _put(frame, "Press  Q  at any time to quit",
         (cap_x, cta_y + 36), scale=0.40, color=_C_MUTED)

    if degraded:
        _put(frame,
             "Demo mode: feed is synthetic. Control commands are disabled.",
             (cap_x, cta_y + 60), scale=0.38, color=_C_WARN)

    # ── Key hint strip ────────────────────────────────────────────────
    cv2.rectangle(frame, (0, H - 32), (W, H), (10, 14, 10), -1)
    _put(frame, "[SPACE] Start Mission    [D] Diagnostics    [Q] Quit",
         (24, H - 10), scale=0.38, color=_C_MUTED)

    cv2.imshow(window_name, frame)
    cv2.waitKey(1)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _put(img, text: str, origin, scale: float = 0.48,
         color=_C_TEXT, thickness: int = 1) -> None:
    cv2.putText(img, str(text), origin,
                cv2.FONT_HERSHEY_SIMPLEX, scale, color,
                thickness, cv2.LINE_AA)


def _section_line(img, x: int, y: int, w: int, color) -> None:
    cv2.line(img, (x, y), (x + w, y), _darken(color), 1)


def _darken(color, factor: float = 0.35):
    if isinstance(color, (list, tuple)):
        return tuple(max(0, int(c * factor)) for c in color)
    return color
