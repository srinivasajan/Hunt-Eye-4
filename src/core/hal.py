from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod

import cv2
import numpy as np

from core.logger import Logger


class HardwareBackend(ABC):

    @abstractmethod
    def connect(self):

        raise NotImplementedError

    @abstractmethod
    def get_frame(self):

        raise NotImplementedError

    def close(self):

        return None

    def get_telemetry(self):

        return {}

    def send_velocity(self, vx, vy, vz, yaw_rate=0.0):

        raise NotImplementedError("Velocity control is not supported by this backend")


# ---------------------------------------------------------------------------
# NullBackend — safe degraded fallback when no hardware is reachable
# ---------------------------------------------------------------------------

class NullBackend(HardwareBackend):
    """Returns synthetic black frames and empty telemetry.

    Used automatically when AirSim is unreachable or any other backend
    fails to connect.  The runtime stays alive in degraded mode so the
    operator can still see the dashboard and status panels.
    """

    _FRAME_W = 640
    _FRAME_H = 480

    def __init__(self, reason: str = "no hardware") -> None:
        self._reason = reason
        self._t0 = time.time()

    def connect(self) -> None:
        pass  # Nothing to connect

    def get_frame(self):
        """Return a tactical SIMULATION STANDBY frame for demo/degraded mode."""
        h, w = self._FRAME_H, self._FRAME_W
        t = time.time() - self._t0

        # ── Base ─────────────────────────────────────────────────────────────
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:] = (10, 13, 11)   # Very dark green-tinted black

        # ── Dot grid — subtle spatial reference ──────────────────────────────
        grid_spacing = 40
        dot_color = (22, 30, 22)
        for gy in range(grid_spacing, h, grid_spacing):
            for gx in range(grid_spacing, w, grid_spacing):
                cv2.circle(frame, (gx, gy), 1, dot_color, -1)

        # ── Subtle scanline effect (every other row slightly lighter) ─────────
        scan_phase = int(t * 30) % h   # slow rolling scan band
        for sy in range(scan_phase, min(scan_phase + 4, h)):
            frame[sy, :] = np.clip(frame[sy, :].astype(np.int16) + 6, 0, 255).astype(np.uint8)

        # ── Corner bracket markers ────────────────────────────────────────────
        blen = 24          # bracket arm length
        bthk = 2           # bracket thickness
        bcol = (40, 70, 45)  # muted green
        corners = [
            ((14, 14),     (1, 1)),    # top-left
            ((w - 15, 14), (-1, 1)),   # top-right
            ((14, h - 15), (1, -1)),   # bottom-left
            ((w - 15, h - 15), (-1, -1)),  # bottom-right
        ]
        for (cx, cy), (dx, dy) in corners:
            cv2.line(frame, (cx, cy), (cx + dx * blen, cy), bcol, bthk)
            cv2.line(frame, (cx, cy), (cx, cy + dy * blen), bcol, bthk)

        # ── Animated connection pulse ring (centre) ───────────────────────────
        cx, cy = w // 2, h // 2
        # Outer pulsing ring
        pulse_r  = int(28 + 8 * abs(np.sin(t * 1.4)))
        pulse_a  = int(55 + 35 * abs(np.sin(t * 1.4)))
        cv2.circle(frame, (cx, cy), pulse_r, (0, pulse_a, 0), 1, cv2.LINE_AA)
        # Inner static ring
        cv2.circle(frame, (cx, cy), 14, (30, 55, 32), 1, cv2.LINE_AA)
        # Centre dot — slow pulse between dim and bright
        dot_bright = int(40 + 60 * abs(np.sin(t * 0.8)))
        cv2.circle(frame, (cx, cy), 3, (0, dot_bright, 0), -1, cv2.LINE_AA)

        # ── Horizontal centre cross-hairs (very faint) ────────────────────────
        ch_col = (18, 28, 20)
        cv2.line(frame, (cx - 60, cy), (cx - 20, cy), ch_col, 1)
        cv2.line(frame, (cx + 20, cy), (cx + 60, cy), ch_col, 1)
        cv2.line(frame, (cx, cy - 60), (cx, cy - 20), ch_col, 1)
        cv2.line(frame, (cx, cy + 20), (cx, cy + 60), ch_col, 1)

        # ── Status badge ─────────────────────────────────────────────────────
        badge_y = cy - 68
        badge_text = "SIMULATION STANDBY"
        badge_x = cx - 92
        cv2.putText(
            frame, badge_text,
            (badge_x, badge_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.44, (50, 110, 55), 1, cv2.LINE_AA,
        )

        # ── Sub-label ────────────────────────────────────────────────────────
        cv2.putText(
            frame, "No live input — demo mode active",
            (cx - 120, cy + 58),
            cv2.FONT_HERSHEY_SIMPLEX, 0.36, (35, 60, 38), 1, cv2.LINE_AA,
        )

        # ── Top-left mode tag ─────────────────────────────────────────────────
        cv2.putText(
            frame, "DEMO",
            (20, 28),
            cv2.FONT_HERSHEY_SIMPLEX, 0.38, (40, 80, 44), 1, cv2.LINE_AA,
        )

        # ── Animated 'acquiring' dots bottom-right ────────────────────────────
        dot_count = 3
        active_dot = int(t * 1.2) % dot_count
        for di in range(dot_count):
            dx2 = w - 30 - di * 10
            d_bright2 = 90 if di == active_dot else 30
            cv2.circle(frame, (dx2, h - 20), 3, (0, d_bright2, 0), -1, cv2.LINE_AA)

        return frame

    def get_telemetry(self):
        return {"degraded": True, "reason": self._reason}

    def send_velocity(self, vx, vy, vz, yaw_rate=0.0):
        pass  # Silently swallow — no hardware to command


class AirSimBackend(HardwareBackend):

    def __init__(self, config):

        self.config = config

        self.client = None

        self._connect_lock = threading.Lock()

        # Circuit-breaker: once True, no further AirSim calls are made.
        # Set permanently after any connect failure.
        self._dead: bool = False

    def connect(self):
        """Connect to AirSim, respecting the timeout from config.

        Raises RuntimeError if the connection cannot be established within
        the timeout so callers can fall back gracefully.
        On failure, sets self._dead = True so no future calls are attempted.
        """
        with self._connect_lock:

            if self._dead:
                raise RuntimeError("AirSim backend is permanently offline")

            if self.client is not None:
                return

            try:
                import airsim
            except ImportError as exc:
                self._dead = True
                raise RuntimeError("airsim package is not installed") from exc

            ip = self.config["airsim"]["ip"]
            timeout = float(self.config.get("airsim", {}).get("connect_timeout_seconds", 5.0))

            # Run confirmConnection in a thread so we can enforce the timeout
            # without hanging the main thread indefinitely.
            result: list = []
            error: list = []

            def _try_connect():
                try:
                    client = airsim.MultirotorClient(ip=ip)
                    client.confirmConnection()
                    result.append(client)
                except Exception as exc:
                    error.append(exc)

            t = threading.Thread(target=_try_connect, daemon=True)
            t.start()
            t.join(timeout=timeout)

            if t.is_alive():
                # Thread is still blocked — AirSim is not responding
                self._dead = True
                raise RuntimeError(
                    f"AirSim connection timed out after {timeout}s "
                    f"(is AirSim running at {ip}?)"
                )

            if error:
                self._dead = True
                raise RuntimeError(f"AirSim connection failed: {error[0]}") from error[0]

            self.client = result[0]
            Logger.info(f"AirSim connected | ip={ip}")

    def get_frame(self):
        # Circuit-breaker: never retry after failure
        if self._dead:
            return None

        import airsim

        try:
            self.connect()
            camera_name = self.config["camera"]["name"]
            response = self.client.simGetImage(
                camera_name,
                airsim.ImageType.Scene
            )
        except Exception as exc:
            self._dead = True
            Logger.error(f"AirSim get_frame failed | circuit-breaker tripped | error={exc}")
            return None

        if response is None:
            return None

        img1d = np.frombuffer(response, dtype=np.uint8)

        return cv2.imdecode(
            img1d,
            cv2.IMREAD_COLOR
        )

    def get_telemetry(self):
        # Circuit-breaker: never retry after failure
        if self._dead or self.client is None:
            return {"airsim_connected": False, "degraded": True}

        try:
            state = self.client.getMultirotorState()
        except Exception:
            self._dead = True
            return {"airsim_connected": False, "degraded": True}

        position = state.kinematics_estimated.position

        velocity = state.kinematics_estimated.linear_velocity

        return {
            "position": {
                "x": position.x_val,
                "y": position.y_val,
                "z": position.z_val,
            },
            "velocity": {
                "x": velocity.x_val,
                "y": velocity.y_val,
                "z": velocity.z_val,
            },
            "landed_state": str(state.landed_state),
        }

    def send_velocity(self, vx, vy, vz, yaw_rate=0.0):
        # Circuit-breaker: never retry after failure
        if self._dead or self.client is None:
            return None

        import airsim

        try:
            return self.client.moveByVelocityAsync(
                vx,
                vy,
                vz,
                duration=0.1,
                yaw_mode=airsim.YawMode(is_rate=True, yaw_or_rate=yaw_rate * 57.2958) # Convert rad/s to deg/s
            )
        except Exception as exc:
            self._dead = True
            Logger.error(f"AirSim send_velocity failed | circuit-breaker tripped | error={exc}")
            return None


class RealBackend(HardwareBackend):

    def __init__(self, config):

        self.config = config

        self.capture = None

        self.mavlink = None
        self.mavlink_available = False
        self._dead = False

    def connect(self):
        if self._dead:
            raise RuntimeError("Real backend is permanently offline")
        self._connect_camera()
        self._connect_mavlink()

    def get_frame(self):
        if self._dead:
            return None

        try:
            self._connect_camera()
            ok, frame = self.capture.read()
            if not ok:
                if self.config["real"]["require_camera"]:
                    self._dead = True
                    Logger.error("Real camera frame capture failed")
                return None
            return frame
        except Exception as exc:
            self._dead = True
            Logger.error(f"Real camera get_frame failed | circuit-breaker tripped | error={exc}")
            return None

    def get_telemetry(self):

        if self.mavlink is None:

            return {
                "mavlink_connected": False,
                "camera_connected": self.capture is not None and self.capture.isOpened(),
            }

        message = self.mavlink.recv_match(blocking=False)

        telemetry = {
            "mavlink_connected": True,
            "camera_connected": self.capture is not None and self.capture.isOpened(),
        }

        if message is not None:

            telemetry["last_message_type"] = message.get_type()

        return telemetry

    def send_velocity(self, vx, vy, vz, yaw_rate=0.0):

        self._connect_mavlink()

        if self.mavlink is None:

            raise RuntimeError("MAVLink is not connected")

        # Body-frame velocity command. Dev 3 safety/control will call this after validation.
        self.mavlink.mav.set_position_target_local_ned_send(
            0,
            self.mavlink.target_system,
            self.mavlink.target_component,
            8,
            0b0000111111000111,
            0,
            0,
            0,
            vx,
            vy,
            vz,
            0,
            0,
            0,
            0,
            yaw_rate,
        )

    def close(self):

        if self.capture is not None:

            self.capture.release()

            self.capture = None

        self.mavlink = None

    def _connect_camera(self):

        if self.capture is not None and self.capture.isOpened():

            return

        real_config = self.config["real"]

        camera_index = real_config["camera_index"]

        api = self._get_camera_api(real_config["camera_api"])

        self.capture = cv2.VideoCapture(camera_index, api)

        if real_config["camera_width"]:

            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, real_config["camera_width"])

        if real_config["camera_height"]:

            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, real_config["camera_height"])

        if real_config["camera_fps"]:

            self.capture.set(cv2.CAP_PROP_FPS, real_config["camera_fps"])

        if not self.capture.isOpened():
            message = f"Real camera could not open | index={camera_index}"
            if real_config["require_camera"]:
                self._dead = True
                raise RuntimeError(message)
            Logger.warning(message)

    def _connect_mavlink(self):

        real_config = self.config["real"]

        if self.mavlink is not None:

            return

        try:

            from pymavlink import mavutil

        except ImportError:

            message = "pymavlink is not installed; real MAVLink connection disabled"

            if real_config["require_mavlink"]:

                raise RuntimeError(message)

            Logger.warning(message)

            return

        connection = real_config["mavlink_connection"] or real_config["serial_port"]

        self.mavlink = mavutil.mavlink_connection(
            connection,
            baud=real_config["baud_rate"]
        )

        self.mavlink.wait_heartbeat(
            timeout=real_config["mavlink_timeout_seconds"]
        )

        Logger.info(f"MAVLink connected | connection={connection}")

    def _get_camera_api(self, api_name):

        if api_name == "dshow":

            return cv2.CAP_DSHOW

        if api_name == "msmf":

            return cv2.CAP_MSMF

        return cv2.CAP_ANY


class HAL:

    def __init__(self, config):

        self.config = config
        self.degraded = False
        self.degraded_reason: str = ""

        self.backend = self._build_backend(config)

    def connect(self):

        self.backend.connect()

    def get_frame(self):

        return self.backend.get_frame()

    def get_telemetry(self):

        return self.backend.get_telemetry()

    def send_velocity(self, vx, vy, vz, yaw_rate=0.0):

        return self.backend.send_velocity(vx, vy, vz, yaw_rate)

    def close(self):

        self.backend.close()

    def _build_backend(self, config):

        backend_name = config["hal"]["backend"]

        if backend_name == "airsim":
            try:
                backend = AirSimBackend(config)
                # Probe the connection immediately so we know early whether
                # AirSim is reachable.  This will raise if it isn't.
                backend.connect()
                return backend
            except Exception as exc:
                reason = str(exc)
                Logger.warning(
                    f"AirSim unavailable — falling back to degraded mode | reason={reason}"
                )
                self.degraded = True
                self.degraded_reason = reason
                return NullBackend(reason="AirSim unavailable")

        if backend_name == "real":
            try:
                backend = RealBackend(config)
                backend.connect()
                return backend
            except Exception as exc:
                reason = str(exc)
                Logger.warning(
                    f"Webcam unavailable — falling back to demo mode | reason={reason}"
                )
                self.degraded = True
                self.degraded_reason = reason
                return NullBackend(reason="Webcam unavailable")

        raise ValueError(f"Unsupported HAL backend: {backend_name}")
