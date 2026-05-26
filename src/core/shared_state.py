import threading
import time
from typing import Any, Dict, List, Optional

from core.event_bus import EventBus
from core.profiler import LatencyProfiler


class SharedState:

    def __init__(self) -> None:

        self.lock = threading.RLock()

        self.event_bus = EventBus()

        self.profiler = LatencyProfiler()

        self.latest_frame: Optional[Any] = None

        self.last_frame_time: Optional[float] = None

        self.detections: List[Dict[str, Any]] = []

        self.tracks: List[Dict[str, Any]] = []

        self.active_target_id: int = -1

        self.target_bbox: Optional[List[float]] = None

        self.active_target: Optional[Dict[str, Any]] = None

        self.depth_map: Optional[Any] = None

        self.cost_map: Optional[Any] = None

        self.planned_path: List[Dict[str, float]] = []

        self.uav_position: Optional[Dict[str, float]] = None

        self.control_command: Dict[str, float] = {
            "vx": 0.0,
            "vy": 0.0,
            "vz": 0.0,
        }

        self.safety: Dict[str, Any] = {
            "safe": True,
            "reason": "OK",
        }

        self.telemetry: Dict[str, Any] = {}

        self.worker_health: Dict[str, Dict[str, Any]] = {}

        self.events: List[Dict[str, Any]] = []

        self.telemetry_history: List[Dict[str, Any]] = []

        self.mission: Dict[str, Any] = {
            "name": "Default",
            "status": "IDLE",
            "waypoints": [],
            "active_waypoint": None,
        }

        self.operator: Dict[str, Any] = {
            "paused": False,
            "recording": False,
            "last_command": None,
        }

        self.recording: Dict[str, Any] = {
            "active": False,
            "path": None,
            "frames": 0,
        }

        self.system_mode: str = "IDLE"

    def set_latest_frame(self, frame: Any) -> None:

        with self.lock:

            self.latest_frame = frame

            self.last_frame_time = time.time()

    def get_latest_frame(self) -> Optional[Any]:

        with self.lock:

            return self.latest_frame

    def update_worker_health(self, worker_name: str, status: Dict[str, Any]) -> None:

        with self.lock:

            self.worker_health[worker_name] = status

    def snapshot(self) -> Dict[str, Any]:

        with self.lock:

            return {
                "has_frame": self.latest_frame is not None,
                "last_frame_time": self.last_frame_time,
                "detections": list(self.detections),
                "tracks": list(self.tracks),
                "active_target_id": self.active_target_id,
                "target_bbox": self.target_bbox,
                "planned_path": list(self.planned_path),
                "uav_position": dict(self.uav_position) if self.uav_position else None,
                "control_command": dict(self.control_command),
                "safety": dict(self.safety),
                "system_mode": self.system_mode,
                "telemetry": dict(self.telemetry),
                "worker_health": dict(self.worker_health),
                "events": list(self.events),
                "telemetry_history": list(self.telemetry_history),
                "mission": dict(self.mission),
                "operator": dict(self.operator),
                "recording": dict(self.recording),
                "latency": self.profiler.summary(),
            }
