import time
import numpy as np
import math
from core.worker_base import WorkerBase
from core.logger import Logger

def sanitize_value(v):
    if math.isnan(v) or math.isinf(v):
        return 0.0
    return v

# Throttle interval for repeated per-loop error messages (seconds)
_ERR_THROTTLE_S = 30.0


class ControlWorker(WorkerBase):
    def __init__(self, state, hal, config, pid, planner, safety):
        super().__init__(name="control", loop_interval=0.05)
        self.state = state
        self.hal = hal
        self.config = config
        self.pid = pid
        self.planner = planner
        self.safety = safety
        
        self.vx_filtered = 0.0
        self.vy_filtered = 0.0
        self.vz_filtered = 0.0
        self.yaw_filtered = 0.0

        # Throttle timestamps to prevent log spam on sustained failures
        self._last_telemetry_err_t: float = 0.0
        self._last_velocity_err_t: float = 0.0

    def safe_run(self):
        while self.running:
            self.heartbeat()

            # 1. Fetch live telemetry without blocking UI thread
            try:
                telemetry = self.hal.get_telemetry()
                with self.state.lock:
                    self.state.telemetry = telemetry
                    self.state.telemetry_history.append(telemetry)
                    # Limit history size to prevent memory leak
                    if len(self.state.telemetry_history) > 1000:
                        self.state.telemetry_history.pop(0)
            except Exception as e:
                now = time.time()
                if now - self._last_telemetry_err_t >= _ERR_THROTTLE_S:
                    Logger.warning(f"Telemetry update failed | error={e}")
                    self._last_telemetry_err_t = now
                telemetry = {}

            # 2. Extract perception and telemetry state
            current_time = time.time()
            with self.state.lock:
                target_bbox = self.state.target_bbox
                mode = self.state.system_mode
                cost_map = self.state.cost_map
                depth_frame = getattr(self.state, 'depth_frame', None)
                last_frame_time = self.state.last_frame_time or 0.0
            
            # Watchdog emergency hover on dead camera feed
            stale_frames = (current_time - last_frame_time) > 1.0
            if stale_frames:
                target_bbox = None

            # 3. Calculate Path & Avoidance if cost_map exists
            path = []
            obstacle_yaw_modifier = 0.0
            if cost_map is not None:
                try:
                    self.planner.cost_map = cost_map
                    h, w = cost_map.shape[:2]
                    # Dynamic replanning check (simple logic based on center density)
                    center_cost = cost_map[h//2 - 2:h//2 + 2, w//2 - 2:w//2 + 2].mean()
                    if center_cost > 60.0:
                        # Obstacle straight ahead, steer away from density
                        left_cost = cost_map[:, :w//2].mean()
                        right_cost = cost_map[:, w//2:].mean()
                        obstacle_yaw_modifier = 0.5 if left_cost > right_cost else -0.5

                    # Generate visualization path
                    path = self.planner.find_path((0, 0), (h - 1, w - 1)) or []
                except Exception:
                    path = []

            # 4. Calculate Control Command
            vx = vy = vz = yaw_rate = 0.0
            if target_bbox:
                # _normalize_bbox functionality
                x1, y1, x2, y2 = target_bbox
                w, h = x2 - x1, y2 - y1
                target_cx = x1 + (w / 2.0)
                target_cy = y1 + (h / 2.0)
                box_area = w * h
                
                # Assume static frame size of 1280x720 for now, or fetch from camera config
                base_vx, base_vy, base_vz, base_yaw = self.pid.calculate(
                    target_cx, target_cy, box_area, frame_w=1280, frame_h=720
                )
                
                vx = base_vx
                vy = base_vy
                vz = base_vz
                yaw_rate = base_yaw + obstacle_yaw_modifier
            else:
                # No target, initiate search sweep or stabilize
                yaw_rate = 0.0

            # 5. Low-pass filter for command smoothing
            alpha = 0.2
            self.vx_filtered = (alpha * vx) + ((1 - alpha) * self.vx_filtered)
            self.vy_filtered = (alpha * vy) + ((1 - alpha) * self.vy_filtered)
            self.vz_filtered = (alpha * vz) + ((1 - alpha) * self.vz_filtered)
            self.yaw_filtered = (alpha * yaw_rate) + ((1 - alpha) * self.yaw_filtered)

            # 6. Apply Safety Limits
            position = telemetry.get("position", {})
            altitude = float(position.get("z", telemetry.get("altitude", 0.0)) or 0.0)
            distance = float(telemetry.get("distance_from_home", 0.0) or 0.0)
            
            # Sanitize NaNs
            self.vx_filtered = sanitize_value(self.vx_filtered)
            self.vy_filtered = sanitize_value(self.vy_filtered)
            self.vz_filtered = sanitize_value(self.vz_filtered)
            self.yaw_filtered = sanitize_value(self.yaw_filtered)

            safe_vx, safe_vy, safe_vz, safe, reason = self.safety.enforce_command(
                self.vx_filtered, self.vy_filtered, self.vz_filtered, altitude, distance, mode
            )

            with self.state.lock:
                self.state.control_command = {"vx": safe_vx, "vy": safe_vy, "vz": safe_vz, "yaw_rate": self.yaw_filtered}
                self.state.safety = {"safe": safe, "reason": reason}
                if path:
                    self.state.planned_path = [{"x": float(x), "y": float(y), "z": 0.0} for x, y in path]

            # 7. Physical Dispatch
            if safe and (abs(safe_vx) > 0.01 or abs(safe_vy) > 0.01 or abs(safe_vz) > 0.01 or abs(self.yaw_filtered) > 0.01):
                try:
                    self.hal.send_velocity(safe_vx, safe_vy, safe_vz, yaw_rate=self.yaw_filtered)
                except Exception as e:
                    now = time.time()
                    if now - self._last_velocity_err_t >= _ERR_THROTTLE_S:
                        Logger.error(f"HAL send_velocity failed: {e}")
                        self._last_velocity_err_t = now

            self.sleep()
