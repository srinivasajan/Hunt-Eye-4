import json
import os
import time
from pathlib import Path

import cv2


class EventLog:

    def __init__(self, max_events=100):

        self.max_events = max_events

    def append(self, state, level, message, payload=None):

        event = {
            "time": time.time(),
            "level": level,
            "message": message,
            "payload": payload or {},
        }

        with state.lock:

            state.events.append(event)

            if len(state.events) > self.max_events:

                del state.events[:-self.max_events]

        return event


class TelemetryHistory:

    def __init__(self, max_samples=300):

        self.max_samples = max_samples

    def append(self, state, telemetry):

        sample = {
            "time": time.time(),
            "telemetry": telemetry,
        }

        with state.lock:

            state.telemetry_history.append(sample)

            if len(state.telemetry_history) > self.max_samples:

                del state.telemetry_history[:-self.max_samples]

        return sample


class MissionState:

    def add_waypoint(self, state, waypoint):

        with state.lock:

            state.mission["waypoints"].append(waypoint)

            if state.mission["active_waypoint"] is None:

                state.mission["active_waypoint"] = 0

            state.mission["status"] = "PLANNED"

    def clear(self, state):

        with state.lock:

            state.mission["waypoints"] = []

            state.mission["active_waypoint"] = None

            state.mission["status"] = "IDLE"


class OperatorControls:

    def set_mode(self, state, mode):

        with state.lock:

            state.system_mode = mode

            state.operator["last_command"] = f"mode:{mode}"

    def toggle_pause(self, state):

        with state.lock:

            state.operator["paused"] = not state.operator["paused"]

            state.operator["last_command"] = "pause" if state.operator["paused"] else "resume"

            return state.operator["paused"]


class SessionRecorder:

    def __init__(self, config):

        self.config = config

        self.writer = None

        self.path = None

    def toggle(self, state, frame_shape):

        if self.writer is None:

            return self.start(state, frame_shape)

        self.stop(state)

        return False

    def start(self, state, frame_shape):

        if not self.config["recording"]["enabled"]:

            return False

        folder = Path(self.config["recording"]["folder"])

        folder.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        self.path = folder / f"hunteye_{timestamp}.mp4"

        height, width = frame_shape[:2]

        codec = self.config["recording"]["codec"]

        fourcc = cv2.VideoWriter_fourcc(*codec)

        self.writer = cv2.VideoWriter(
            str(self.path),
            fourcc,
            self.config["recording"]["fps"],
            (width, height),
        )

        if not self.writer.isOpened():

            self.writer = None

            self.path = None

            return False

        with state.lock:

            state.recording["active"] = True

            state.recording["path"] = str(self.path)

            state.recording["frames"] = 0

            state.operator["recording"] = True

        return True

    def write(self, state, frame):

        if self.writer is None:

            return

        self.writer.write(frame)

        with state.lock:

            state.recording["frames"] += 1

    def stop(self, state):

        if self.writer is not None:

            self.writer.release()

        self.writer = None

        with state.lock:

            state.recording["active"] = False

            state.operator["recording"] = False


class SessionExporter:

    def __init__(self, config):

        self.folder = Path(config["session"]["export_folder"])

    def export_snapshot(self, snapshot):

        self.folder.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        path = self.folder / f"snapshot_{timestamp}.json"

        with path.open("w", encoding="utf-8") as handle:

            json.dump(_json_safe(snapshot), handle, indent=2)

        return str(path)


def _json_safe(value):

    if isinstance(value, dict):

        return {key: _json_safe(item) for key, item in value.items()}

    if isinstance(value, list):

        return [_json_safe(item) for item in value]

    if isinstance(value, tuple):

        return [_json_safe(item) for item in value]

    if hasattr(value, "item"):

        return value.item()

    return value
