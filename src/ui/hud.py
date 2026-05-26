"""hud.py — State-aware tactical HUD for HuntEye live feed.

Draws cinematic overlays directly onto the camera/AirSim frame.
All drawing is time-based for animation and runs in the main render loop.

Public API:
    draw_live_hud(frame, snapshot, ui_state, fps, degraded=False) -> np.ndarray
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Colour palette  (all BGR)
# ---------------------------------------------------------------------------
_C_BG_STRIP   = (10, 13, 11)     # near-black strip backgrounds
_C_GREEN      = (55, 200, 65)    # healthy / tracking
_C_GREEN_DIM  = (22, 70, 28)     # inactive green
_C_AMBER      = (28, 160, 215)   # warning / detected
_C_RED        = (45, 45, 210)    # emergency / lost
_C_WHITE      = (220, 228, 222)  # primary text
_C_MUTED      = (80, 95, 85)     # secondary text
_C_CORNER     = (50, 130, 60)    # default bracket green
_C_TARGET     = (30, 210, 255)   # primary target (amber-white)
_C_DETECT     = (55, 180, 255)   # secondary detection
_C_TRACK_DIM  = (35, 110, 40)    # dim track outline
_C_REC        = (40, 40, 210)    # recording red

# Module-level start time for continuous animation
_T0 = time.time()

# Tracking state constants
SEARCHING        = "SEARCHING"
TARGET_DETECTED  = "TARGET DETECTED"
TRACKING         = "TRACKING"
TARGET_LOST      = "TARGET LOST"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def draw_live_hud(
    frame: np.ndarray,
    snapshot: Dict[str, Any],
    ui_state: Any,
    fps: float,
    degraded: bool = False,
) -> np.ndarray:
    """Draw full tactical HUD on a copy of the frame.

    Args:
        frame:      Raw camera / AirSim / NullBackend frame.
        snapshot:   State snapshot dict from SharedState.snapshot().
        ui_state:   UIState dataclass instance.
        fps:        Current render FPS.
        degraded:   True when running in demo/NullBackend mode.

    Returns:
        A new frame with HUD overlays applied.
    """
    out = frame.copy()
    h, w = out.shape[:2]
    t    = time.time() - _T0

    # ── Derive tracking state ───────────────────────────────────────────────
    target_bbox  = snapshot.get("target_bbox")
    detections   = snapshot.get("detections", [])
    tracks       = snapshot.get("tracks", [])
    system_mode  = snapshot.get("system_mode", "IDLE")
    recording    = snapshot.get("recording", {}).get("active", False)
    operator     = snapshot.get("operator", {})
    paused       = operator.get("paused", False)

    tracking_state = _resolve_tracking_state(
        target_bbox, detections, system_mode,
        getattr(ui_state, "tracking_state", SEARCHING),
    )

    # Persist state back so dashboard panel can read it
    try:
        ui_state.tracking_state = tracking_state
    except Exception:
        pass

    # ── Layer 1 — detection bounding boxes ──────────────────────────────────
    _draw_detections(out, detections, tracks, target_bbox, t)

    # ── Layer 2 — target lock-on overlay ────────────────────────────────────
    if target_bbox is not None:
        _draw_lock_on(out, target_bbox, tracking_state, t)

    # ── Layer 3 — corner brackets (frame edge) ───────────────────────────────
    _draw_frame_corners(out, w, h, tracking_state, t)

    # ── Layer 4 — status strip (top) ────────────────────────────────────────
    _draw_top_strip(out, w, tracking_state, system_mode, fps, recording, paused, t, degraded)

    # ── Layer 5 — info strip (bottom) ────────────────────────────────────────
    _draw_bottom_strip(out, w, h, snapshot, detections, tracks, recording, t)

    return out


# ---------------------------------------------------------------------------
# Layer 1 — Detection bounding boxes
# ---------------------------------------------------------------------------

def _draw_detections(
    img: np.ndarray,
    detections: List[Dict],
    tracks: List[Dict],
    target_bbox,
    t: float,
) -> None:
    """Draw cinematic corner-bracket boxes for detections and tracks."""

    # Map track_id → track for lookup
    track_map = {tr.get("track_id"): tr for tr in tracks}

    drawn_ids: set = set()

    # Primary target (highest priority — drawn last so it appears on top)
    if target_bbox is not None:
        pulse = int(200 + 40 * abs(math.sin(t * 2.0)))
        col   = (0, pulse, int(pulse * 0.6))
        _draw_bracket_box(img, target_bbox, col, arm=14, thickness=2)
        # "TARGET" label above box
        x1, y1 = int(target_bbox[0]), int(target_bbox[1])
        _put(img, "TARGET", (x1, max(16, y1 - 8)), scale=0.40, color=col, thickness=1)

    # Secondary detections
    for det in detections:
        bbox    = det.get("bbox")
        conf    = det.get("confidence", 0.0)
        tid     = det.get("track_id")
        if bbox is None:
            continue
        # Skip if this is the primary target (already drawn)
        if target_bbox is not None and _bbox_approx_equal(bbox, target_bbox):
            continue
        drawn_ids.add(tid)
        _draw_bracket_box(img, bbox, _C_DETECT, arm=10, thickness=1)
        x1, y1 = int(bbox[0]), int(bbox[1])
        label = f"{conf:.0%}" if conf else ""
        if tid is not None:
            label = f"ID {tid}  {label}"
        _put(img, label, (x1, max(16, y1 - 6)), scale=0.36, color=_C_MUTED)

    # Tracks without detections (lost-but-remembered)
    for tr in tracks:
        tid  = tr.get("track_id")
        bbox = tr.get("bbox") or tr.get("tlwh")
        if bbox is None or tid in drawn_ids:
            continue
        if target_bbox is not None and _bbox_approx_equal(bbox, target_bbox):
            continue
        _draw_bracket_box(img, bbox, _C_TRACK_DIM, arm=8, thickness=1)


def _draw_bracket_box(
    img: np.ndarray,
    bbox,
    color: Tuple,
    arm: int = 12,
    thickness: int = 2,
) -> None:
    """Draw 4 corner L-brackets instead of a plain rectangle."""
    try:
        x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
    except (TypeError, IndexError, ValueError):
        return

    # Clamp to image bounds
    ih, iw = img.shape[:2]
    x1 = max(0, min(x1, iw - 1))
    y1 = max(0, min(y1, ih - 1))
    x2 = max(0, min(x2, iw - 1))
    y2 = max(0, min(y2, ih - 1))
    if x2 <= x1 or y2 <= y1:
        return

    a = min(arm, (x2 - x1) // 3, (y2 - y1) // 3)

    corners = [
        # (corner x, corner y, x-dir, y-dir)
        (x1, y1, +1, +1),
        (x2, y1, -1, +1),
        (x1, y2, +1, -1),
        (x2, y2, -1, -1),
    ]
    for (cx, cy, dx, dy) in corners:
        cv2.line(img, (cx, cy), (cx + dx * a, cy), color, thickness, cv2.LINE_AA)
        cv2.line(img, (cx, cy), (cx, cy + dy * a), color, thickness, cv2.LINE_AA)


# ---------------------------------------------------------------------------
# Layer 2 — Target lock-on overlay
# ---------------------------------------------------------------------------

def _draw_lock_on(
    img: np.ndarray,
    bbox,
    tracking_state: str,
    t: float,
) -> None:
    """Animated reticle centred on the primary target."""
    try:
        x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
    except Exception:
        return

    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    bw = x2 - x1
    bh = y2 - y1

    # Reticle size tied to target size
    arm   = max(10, min(bw, bh) // 4)
    gap   = arm + 4

    # Pulse speed/colour depends on state
    if tracking_state == TRACKING:
        speed  = 2.2
        pulse  = int(180 + 70 * abs(math.sin(t * speed)))
        col    = (0, pulse, int(pulse * 0.5))
        # Tighten effect: gap shrinks slightly during lock
        gap   -= int(3 * abs(math.sin(t * 1.5)))
    elif tracking_state == TARGET_DETECTED:
        speed = 1.2
        pulse = int(140 + 60 * abs(math.sin(t * speed)))
        col   = (0, int(pulse * 0.5), pulse)  # amber
    else:
        col   = _C_GREEN_DIM

    # Four arms of the reticle
    cv2.line(img, (cx - gap - arm, cy), (cx - gap, cy), col, 1, cv2.LINE_AA)
    cv2.line(img, (cx + gap,       cy), (cx + gap + arm, cy), col, 1, cv2.LINE_AA)
    cv2.line(img, (cx, cy - gap - arm), (cx, cy - gap), col, 1, cv2.LINE_AA)
    cv2.line(img, (cx, cy + gap),       (cx, cy + gap + arm), col, 1, cv2.LINE_AA)

    # Centre pip
    cv2.circle(img, (cx, cy), 2, col, -1, cv2.LINE_AA)

    # "LOCKED" label below target when fully tracking
    if tracking_state == TRACKING:
        lx = cx - 24
        ly = y2 + 14
        _put(img, "LOCKED", (lx, ly), scale=0.36, color=col)


# ---------------------------------------------------------------------------
# Layer 3 — Frame-edge corner brackets
# ---------------------------------------------------------------------------

def _draw_frame_corners(
    img: np.ndarray,
    w: int,
    h: int,
    tracking_state: str,
    t: float,
) -> None:
    arm = 20
    pad = 12
    thk = 2

    state_colours = {
        SEARCHING:       _C_GREEN_DIM,
        TARGET_DETECTED: (28, 140, 200),   # amber
        TRACKING:        _C_GREEN,
        TARGET_LOST:     (40, 40, 160),    # dim red
    }
    base_col = state_colours.get(tracking_state, _C_GREEN_DIM)

    if tracking_state == TRACKING:
        pulse = int(80 + 50 * abs(math.sin(t * 1.8)))
        col   = tuple(min(255, c + pulse // 4) for c in base_col)
    else:
        col = base_col

    corners = [
        (pad,     pad,     +1, +1),
        (w - pad, pad,     -1, +1),
        (pad,     h - pad, +1, -1),
        (w - pad, h - pad, -1, -1),
    ]
    for (cx, cy, sdx, sdy) in corners:
        cv2.line(img, (cx, cy), (cx + sdx * arm, cy), col, thk, cv2.LINE_AA)
        cv2.line(img, (cx, cy), (cx, cy + sdy * arm), col, thk, cv2.LINE_AA)


# ---------------------------------------------------------------------------
# Layer 4 — Top status strip
# ---------------------------------------------------------------------------

def _draw_top_strip(
    img: np.ndarray,
    w: int,
    tracking_state: str,
    system_mode: str,
    fps: float,
    recording: bool,
    paused: bool,
    t: float,
    degraded: bool,
) -> None:
    """Single-line status strip at the very top of the frame."""

    # Tracking-state colour
    state_col = {
        SEARCHING:       _C_GREEN_DIM,
        TARGET_DETECTED: (28, 145, 210),
        TRACKING:        _C_GREEN,
        TARGET_LOST:     (40, 40, 170),
    }.get(tracking_state, _C_MUTED)

    # Pulsing status dot (top-left)
    if tracking_state == TRACKING:
        pulse = int(160 + 80 * abs(math.sin(t * 2.0)))
        dot_col = tuple(min(255, int(c * pulse / 200)) for c in _C_GREEN)
    elif tracking_state == TARGET_DETECTED:
        pulse   = int(120 + 80 * abs(math.sin(t * 1.4)))
        dot_col = (0, int(pulse * 0.6), pulse)
    elif tracking_state == TARGET_LOST:
        pulse   = int(80 + 60 * abs(math.sin(t * 2.5)))
        dot_col = (0, 0, pulse)
    else:
        dot_col = _C_GREEN_DIM

    cv2.circle(img, (14, 14), 5, dot_col, -1, cv2.LINE_AA)

    # Tracking state label
    _put(img, tracking_state, (26, 19), scale=0.38, color=state_col)

    # DEMO badge (if degraded)
    if degraded:
        _put(img, "DEMO", (w // 2 - 18, 19), scale=0.36, color=_C_MUTED)

    # FPS — right side
    fps_str = f"{fps:.0f} fps"
    fps_x   = w - len(fps_str) * 8 - 12
    _put(img, fps_str, (fps_x, 19), scale=0.36, color=_C_MUTED)

    # Recording indicator — blinking red dot + REC label
    if recording:
        blink = abs(math.sin(t * 2.0)) > 0.5
        rec_x = w - 90
        if blink:
            cv2.circle(img, (rec_x, 14), 5, _C_REC, -1, cv2.LINE_AA)
        _put(img, "REC", (rec_x + 10, 19), scale=0.36, color=_C_REC)

    # PAUSED badge
    if paused:
        _put(img, "PAUSED", (w // 2 - 30, 19), scale=0.36, color=_C_AMBER)


# ---------------------------------------------------------------------------
# Layer 5 — Bottom info strip
# ---------------------------------------------------------------------------

def _draw_bottom_strip(
    img: np.ndarray,
    w: int,
    h: int,
    snapshot: Dict[str, Any],
    detections: List[Dict],
    tracks: List[Dict],
    recording: bool,
    t: float,
) -> None:
    """Bottom-of-frame info: target count, mission timer, signal indicator."""
    y = h - 10

    # Target count (left)
    n_det = len(detections)
    if n_det == 0:
        count_col = _C_MUTED
        count_str = "No targets"
    elif n_det == 1:
        count_col = _C_GREEN
        count_str = "1 target"
    else:
        count_col = _C_AMBER
        count_str = f"{n_det} targets"
    _put(img, count_str, (14, y), scale=0.36, color=count_col)

    # Mission timer (centre) — only if mission started
    mission = snapshot.get("mission", {})
    started = mission.get("started_at")
    if started is not None:
        elapsed = time.time() - started
        mins    = int(elapsed) // 60
        secs    = int(elapsed) % 60
        clock   = f"{mins:02d}:{secs:02d}"
        cx      = w // 2 - len(clock) * 5
        _put(img, clock, (cx, y), scale=0.38, color=_C_MUTED)

    # Signal indicator (right) — green=live, amber=degraded
    sig_x = w - 14
    sig_y = h - 14
    telemetry = snapshot.get("telemetry", {})
    is_live   = telemetry.get("airsim_connected") or telemetry.get("camera_connected")
    degraded  = telemetry.get("degraded") or telemetry.get("airsim_connected") is False

    if is_live:
        sig_col = _C_GREEN
    elif degraded:
        sig_col = _C_AMBER
    else:
        sig_col = _C_GREEN_DIM

    cv2.circle(img, (sig_x, sig_y), 4, sig_col, -1, cv2.LINE_AA)


# ---------------------------------------------------------------------------
# Tracking state resolver
# ---------------------------------------------------------------------------

def _resolve_tracking_state(
    target_bbox,
    detections: List[Dict],
    system_mode: str,
    current_state: str,
) -> str:
    """Determine the current tracking state from snapshot data."""
    if system_mode == "EMERGENCY":
        return TARGET_LOST

    if target_bbox is not None and system_mode == "TRACKING":
        return TRACKING

    if detections:
        return TARGET_DETECTED

    # Hysteresis — show TARGET LOST briefly after TRACKING
    if current_state in (TRACKING, TARGET_DETECTED):
        return TARGET_LOST

    return SEARCHING


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _put(
    img: np.ndarray,
    text: str,
    origin: Tuple[int, int],
    scale: float = 0.40,
    color: Tuple = _C_WHITE,
    thickness: int = 1,
) -> None:
    cv2.putText(
        img, str(text), origin,
        cv2.FONT_HERSHEY_SIMPLEX, scale, color,
        thickness, cv2.LINE_AA,
    )


def _bbox_approx_equal(a, b, tol: int = 8) -> bool:
    """Return True if two bboxes are approximately the same."""
    try:
        return all(abs(int(a[i]) - int(b[i])) < tol for i in range(4))
    except Exception:
        return False
