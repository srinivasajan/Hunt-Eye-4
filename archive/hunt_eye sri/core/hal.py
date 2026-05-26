from __future__ import annotations

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


class AirSimBackend(HardwareBackend):

    def __init__(self, config):

        self.config = config

        self.client = None

    def connect(self):

        import airsim

        if self.client is not None:

            return

        ip = self.config["airsim"]["ip"]

        self.client = airsim.MultirotorClient(ip=ip)

        self.client.confirmConnection()

    def get_frame(self):

        import airsim

        self.connect()

        camera_name = self.config["camera"]["name"]

        response = self.client.simGetImage(
            camera_name,
            airsim.ImageType.Scene
        )

        if response is None:

            return None

        img1d = np.frombuffer(response, dtype=np.uint8)

        return cv2.imdecode(
            img1d,
            cv2.IMREAD_COLOR
        )

    def get_telemetry(self):

        self.connect()

        state = self.client.getMultirotorState()

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

        self.connect()

        return self.client.moveByVelocityAsync(
            vx,
            vy,
            vz,
            duration=0.1,
            yaw_mode=None
        )


class RealBackend(HardwareBackend):

    def __init__(self, config):

        self.config = config

        self.capture = None

        self.mavlink = None

        self.mavlink_available = False

    def connect(self):

        self._connect_camera()

        self._connect_mavlink()

    def get_frame(self):

        self._connect_camera()

        ok, frame = self.capture.read()

        if not ok:

            if self.config["real"]["require_camera"]:

                raise RuntimeError("Real camera frame capture failed")

            return None

        return frame

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

            return AirSimBackend(config)

        if backend_name == "real":

            return RealBackend(config)

        raise ValueError(f"Unsupported HAL backend: {backend_name}")
