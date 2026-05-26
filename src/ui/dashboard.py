import time

import cv2
import numpy as np


class OperationsDashboard:

    def __init__(self, config):

        self.config = config

        self.panel_width = config["dashboard"]["panel_width"]

        self.show_latency = config["dashboard"]["show_latency"]

        self.show_worker_health = config["dashboard"]["show_worker_health"]

        self.show_target_overlay = config["dashboard"]["show_target_overlay"]

        self.show_event_log = config["dashboard"]["show_event_log"]

        self.show_mission = config["dashboard"]["show_mission"]

        self.show_controls = config["dashboard"]["show_controls"]

        self.max_events = config["dashboard"]["max_events"]

        self.min_height = config["dashboard"]["min_height"]

    def _get_colors(self, ui_state):
        theme = getattr(ui_state, "theme", "DARK") if ui_state is not None else "DARK"
        if theme == "LIGHT":
            return {
                "bg": (240, 245, 250),
                "title": (10, 15, 20),
                "text": (30, 40, 50),
                "muted": (100, 110, 120),
                "highlight": (10, 15, 20),
                "error": (50, 50, 200),
                "warn": (30, 120, 200)
            }
        else:
            return {
                "bg": (18, 22, 26),
                "title": (245, 245, 245),
                "text": (210, 220, 225),
                "muted": (120, 130, 140),
                "highlight": (245, 245, 245),
                "error": (80, 80, 230),
                "warn": (70, 180, 255)
            }

    def render(self, frame, snapshot, worker_statuses, fps, ui_state=None, config_for_editor=None):

        frame_view = self._scale_frame(frame)

        if ui_state is not None:
            self._apply_debug_overlays(frame_view, snapshot, ui_state)

        if self.show_target_overlay:

            self._draw_target_overlay(frame_view, snapshot)

        mode = getattr(ui_state, "panel_mode", "OPS") if ui_state is not None else "OPS"

        if mode == "DIAG":
            panel = self._build_diagnostics_panel(frame_view.shape[0], snapshot, worker_statuses, ui_state)
        elif mode == "CONFIG":
            panel = self._build_config_panel(frame_view.shape[0], config_for_editor or {}, ui_state)
        elif mode == "WAYPOINTS":
            panel = self._build_waypoints_panel(frame_view.shape[0], snapshot, ui_state)
        else:
            panel = self._build_panel(frame_view.shape[0], snapshot, worker_statuses, fps, ui_state)

        return np.hstack([frame_view, panel])

    def _apply_debug_overlays(self, frame, snapshot, ui_state):

        try:
            if getattr(ui_state, "show_depth_overlay", False) and snapshot.get("depth_map") is not None:
                depth = snapshot.get("depth_map")
                overlay = self._normalize_to_colormap(depth, (frame.shape[1], frame.shape[0]))
                frame[:] = cv2.addWeighted(frame, 0.65, overlay, 0.35, 0)

            if getattr(ui_state, "show_cost_overlay", False) and snapshot.get("cost_map") is not None:
                cost = snapshot.get("cost_map")
                overlay = self._normalize_to_colormap(cost, (frame.shape[1], frame.shape[0]))
                frame[:] = cv2.addWeighted(frame, 0.65, overlay, 0.35, 0)

            if getattr(ui_state, "show_path_overlay", True):
                path = snapshot.get("planned_path", [])
                if path:
                    pts = [(int(p.get("x", 0)), int(p.get("y", 0))) for p in path if isinstance(p, dict)]
                    if len(pts) >= 2:
                        cv2.polylines(frame, [np.array(pts, dtype=np.int32)], False, (70, 180, 255), 2)
        except Exception:
            # Never let debug overlays break the frame render
            return

    def _normalize_to_colormap(self, mat, target_size):

        arr = np.array(mat)
        if arr.ndim == 3 and arr.shape[2] in (3, 4):
            arr = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)

        arr = arr.astype(np.float32)
        mn = float(np.nanmin(arr)) if arr.size else 0.0
        mx = float(np.nanmax(arr)) if arr.size else 1.0
        if mx <= mn:
            mx = mn + 1.0
        norm = (arr - mn) / (mx - mn)
        norm = np.clip(norm * 255.0, 0, 255).astype(np.uint8)
        colored = cv2.applyColorMap(norm, cv2.COLORMAP_TURBO)
        return cv2.resize(colored, target_size, interpolation=cv2.INTER_LINEAR)

    def _build_diagnostics_panel(self, height, snapshot, worker_statuses, ui_state):

        from ui.diagnostics_utils import summarize_events, summarize_workers
        
        colors = self._get_colors(ui_state)

        panel = np.zeros((height, self.panel_width, 3), dtype=np.uint8)
        panel[:] = colors["bg"]

        y = 30
        self._text(panel, "Diagnostics", (18, y), scale=0.72, color=colors["title"], thickness=2)
        y += 34

        self._section(panel, "Workers", y, color=colors["muted"])
        y += 26
        for line in summarize_workers(worker_statuses, limit=10):
            self._text(panel, line, (18, y), scale=0.42, color=colors["text"])
            y += 20

        y += 12
        self._section(panel, "Recent Events", y, color=colors["muted"])
        y += 26
        for line in summarize_events(snapshot.get("events", []), limit=12):
            color = colors["text"]
            if "ERROR" in line:
                color = colors["error"]
            elif "WARN" in line:
                color = colors["warn"]
            self._text(panel, line, (18, y), scale=0.42, color=color)
            y += 20
            if y > height - 40:
                break

        self._text(panel, "o ops | d diag | g config | y waypoints | m theme | v layout", (18, height - 18), scale=0.38, color=colors["muted"])
        return panel

    def _build_config_panel(self, height, config_for_editor, ui_state):

        colors = self._get_colors(ui_state)
        panel = np.zeros((height, self.panel_width, 3), dtype=np.uint8)
        panel[:] = colors["bg"]

        y = 30
        self._text(panel, "Config Editor", (18, y), scale=0.72, color=colors["title"], thickness=2)
        y += 34

        try:
            from ui.config_editor import ConfigEditor
            editor = ConfigEditor(
                selected_index=int(getattr(ui_state, "config_selected_index", 0) or 0),
                scroll=int(getattr(ui_state, "config_scroll", 0) or 0),
            )
            items = editor.list_items(config_for_editor)
            editor.clamp(len(items))
        except Exception:
            editor = None
            items = []

        if not items:
            self._text(panel, "No config loaded", (18, y), color=colors["muted"])
            y += 22
        else:
            visible_rows = max(1, int((height - y - 70) / 20))
            scroll = int(getattr(editor, "scroll", 0) or 0) if editor is not None else 0
            selected = int(getattr(editor, "selected_index", 0) or 0) if editor is not None else 0

            scroll = max(0, min(scroll, max(0, len(items) - visible_rows)))
            start = scroll
            end = min(len(items), start + visible_rows)

            for idx in range(start, end):
                dotted, val = items[idx]
                is_sel = idx == selected
                color = colors["highlight"] if is_sel else colors["text"]
                prefix = "> " if is_sel else "  "
                self._text(panel, f"{prefix}{dotted}: {val}", (18, y), scale=0.42, color=color)
                y += 20

        self._text(panel, "[ / ] select | space toggle | +/- change | s save", (18, height - 36), scale=0.38, color=colors["muted"])
        self._text(panel, "o ops | d diag | g config | y waypoints | m theme | v layout", (18, height - 18), scale=0.38, color=colors["muted"])
        return panel

    def _build_waypoints_panel(self, height, snapshot, ui_state):

        colors = self._get_colors(ui_state)
        panel = np.zeros((height, self.panel_width, 3), dtype=np.uint8)
        panel[:] = colors["bg"]

        y = 30
        self._text(panel, "Waypoint Editor", (18, y), scale=0.72, color=colors["title"], thickness=2)
        y += 34

        mission = snapshot.get("mission", {})
        waypoints = mission.get("waypoints", [])
        self._text(panel, f"Waypoints: {len(waypoints)}", (18, y), scale=0.5, color=colors["muted"])
        y += 26

        selected = int(getattr(ui_state, "waypoint_selected_index", 0) or 0) if ui_state is not None else 0

        if not waypoints:
            self._text(panel, "Press 'w' to add current waypoint", (18, y), color=colors["muted"])
            y += 22
        else:
            selected = max(0, min(selected, len(waypoints) - 1))
            for i, wp in enumerate(waypoints[:10]):
                is_sel = i == selected
                color = colors["highlight"] if is_sel else colors["text"]
                prefix = "> " if is_sel else "  "
                self._text(panel, f"{prefix}{i}: x={wp.get('x', 0):.1f} y={wp.get('y', 0):.1f} z={wp.get('z', 0):.1f}", (18, y), scale=0.42, color=color)
                y += 20
                if y > height - 160:
                    break

        # Draw a simple 2D map of waypoints
        map_y = y + 20
        map_h = height - map_y - 60
        map_w = self.panel_width - 36
        if waypoints and map_h > 50:
            # Draw map background
            cv2.rectangle(panel, (18, map_y), (18 + map_w, map_y + map_h), colors["bg"], -1)
            cv2.rectangle(panel, (18, map_y), (18 + map_w, map_y + map_h), colors["muted"], 1)
            
            # Find bounds
            xs = [wp.get('x', 0) for wp in waypoints]
            ys = [wp.get('y', 0) for wp in waypoints]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
            # Add padding
            padding = max(1.0, max(max_x - min_x, max_y - min_y) * 0.1)
            min_x -= padding; max_x += padding
            min_y -= padding; max_y += padding
            
            range_x = max(0.1, max_x - min_x)
            range_y = max(0.1, max_y - min_y)
            
            for i, wp in enumerate(waypoints):
                wx = wp.get('x', 0)
                wy = wp.get('y', 0)
                
                # Map coordinates to pixel space
                px = 18 + int((wx - min_x) / range_x * map_w)
                py = map_y + int((wy - min_y) / range_y * map_h)
                
                color = colors["highlight"] if i == selected else colors["muted"]
                radius = 4 if i == selected else 2
                
                cv2.circle(panel, (px, py), radius, color, -1)
                
                # Draw lines between waypoints
                if i > 0:
                    prev_wp = waypoints[i-1]
                    prev_px = 18 + int((prev_wp.get('x', 0) - min_x) / range_x * map_w)
                    prev_py = map_y + int((prev_wp.get('y', 0) - min_y) / range_y * map_h)
                    cv2.line(panel, (prev_px, prev_py), (px, py), colors["muted"], 1)

        self._text(panel, "[ / ] select | x delete | c clear | h/l x | j/k y | u/i z", (18, height - 36), scale=0.38, color=colors["muted"])
        self._text(panel, "o ops | d diag | g config | y waypoints | m theme | v layout", (18, height - 18), scale=0.38, color=colors["muted"])
        return panel

    def _draw_target_overlay(self, frame, snapshot):

        target_bbox = snapshot.get("target_bbox")

        if target_bbox is not None:

            self._draw_bbox(frame, target_bbox, (0, 220, 255), "TARGET")

        for index, detection in enumerate(snapshot.get("detections", []), start=1):

            bbox = detection.get("bbox")

            confidence = detection.get("confidence")

            label = f"DET {index}"

            if confidence is not None:

                label = f"{label} {confidence:.2f}"

            self._draw_bbox(frame, bbox, (70, 180, 255), label)

        for track in snapshot.get("tracks", []):

            bbox = track.get("bbox") or track.get("tlwh")

            track_id = track.get("track_id", "?")

            self._draw_bbox(frame, bbox, (80, 220, 120), f"ID {track_id}")

    def _build_panel(self, height, snapshot, worker_statuses, fps, ui_state):

        colors = self._get_colors(ui_state)
        panel = np.zeros((height, self.panel_width, 3), dtype=np.uint8)

        panel[:] = colors["bg"]

        y = 30

        self._text(panel, "HuntEye Ops", (18, y), scale=0.72, color=colors["title"], thickness=2)

        y += 34

        system_mode = snapshot.get("system_mode", "UNKNOWN")

        color_mode = colors["highlight"]

        if system_mode == "TRACKING":

            color_mode = colors["warn"]

        elif system_mode == "EMERGENCY":

            color_mode = colors["error"]

        self._text(panel, f"MODE: {system_mode}", (18, y), scale=0.5, color=color_mode)

        y += 24

        panel_order = getattr(ui_state, "panel_order", ["latency", "workers", "mission", "events"])

        for section_name in panel_order:
            if section_name == "latency" and self.show_latency:
                latency = snapshot.get("latency", {})
                y += 8
                self._section(panel, "Latency (avg ms)", y, color=colors["muted"])
                y += 26
                for name, stats in list(latency.items())[:6]:
                    avg = stats.get("avg", 0)
                    self._text(panel, f"{name}: {avg:.1f}ms", (18, y), scale=0.42, color=colors["text"])
                    y += 20

            elif section_name == "workers" and self.show_worker_health:
                y += 8
                self._section(panel, "Workers", y, color=colors["muted"])
                y += 26
                for status in worker_statuses[:6]:
                    c = colors["text"] if status.get("status") == "ok" else colors["error"]
                    self._text(panel, f"{status['name']}: {status.get('status', 'unknown')}", (18, y), scale=0.42, color=c)
                    y += 20

            elif section_name == "mission" and self.show_mission:
                y += 8
                self._section(panel, "Mission", y, color=colors["muted"])
                y += 26
                mission = snapshot.get("mission", {})
                wps = mission.get("waypoints", [])
                self._text(panel, f"Status: {mission.get('status', 'IDLE')}", (18, y), scale=0.42, color=colors["text"])
                y += 20
                self._text(panel, f"Waypoints: {len(wps)}", (18, y), scale=0.42, color=colors["text"])
                y += 20

            elif section_name == "events" and self.show_event_log:
                y += 8
                self._section(panel, "Event Log", y, color=colors["muted"])
                y += 26
                for ev in snapshot.get("events", [])[-self.max_events:]:
                    lvl = ev.get("level", "INFO")
                    c = colors["text"]
                    if lvl == "ERROR":
                        c = colors["error"]
                    elif lvl == "WARN":
                        c = colors["warn"]
                    msg = ev.get("message", "")[:40]
                    self._text(panel, f"{lvl}: {msg}", (18, y), scale=0.38, color=c)
                    y += 20

        y = height - 40

        self._text(panel, f"FPS: {fps:.1f}", (18, y), scale=0.45, color=colors["title"])

        if self.show_controls:

            self._text(panel, "o ops | d diag | g config | y waypoints | m theme | v layout", (18, height - 18), scale=0.38, color=colors["muted"])

        return panel

    def _scale_frame(self, frame):

        height, width = frame.shape[:2]

        if height >= self.min_height:

            return frame.copy()

        scale = self.min_height / height

        new_width = int(width * scale)

        return cv2.resize(frame, (new_width, self.min_height), interpolation=cv2.INTER_LINEAR)

    def _draw_telemetry(self, panel, telemetry, y):

        position = telemetry.get("position")

        velocity = telemetry.get("velocity")

        if position:

            self._text(
                panel,
                f"Pos x={position['x']:.2f} y={position['y']:.2f} z={position['z']:.2f}",
                (18, y),
                color=(210, 220, 225)
            )

            y += 22

        if velocity:

            self._text(
                panel,
                f"Vel x={velocity['x']:.2f} y={velocity['y']:.2f} z={velocity['z']:.2f}",
                (18, y),
                color=(210, 220, 225)
            )

            y += 22

        for key, value in telemetry.items():

            if key in {"position", "velocity"}:

                continue

            self._text(panel, f"{key}: {value}", (18, y), color=(190, 200, 210))

            y += 22

            if y > panel.shape[0] - 30:

                break

        return y

    def _draw_controls(self, panel, snapshot, y):

        operator = snapshot.get("operator", {})

        recording = snapshot.get("recording", {})

        paused = "YES" if operator.get("paused") else "NO"

        recording_state = "ON" if recording.get("active") else "OFF"

        self._text(panel, f"Paused: {paused}", (18, y), color=(210, 220, 225))

        y += 22

        self._text(panel, f"Recording: {recording_state}", (18, y), color=(210, 220, 225))

        y += 22

        self._text(
            panel,
            f"Last: {operator.get('last_command') or 'none'}",
            (18, y),
            color=(180, 195, 205)
        )

        y += 22

        if recording.get("path"):

            self._text(
                panel,
                f"Frames: {recording.get('frames', 0)}",
                (18, y),
                color=(180, 195, 205)
            )

            y += 22

        return y

    def _draw_mission(self, panel, mission, y):

        waypoints = mission.get("waypoints", [])

        self._text(
            panel,
            f"{mission.get('name', 'Mission')} | {mission.get('status', 'IDLE')}",
            (18, y),
            color=(210, 220, 225)
        )

        y += 22

        self._text(
            panel,
            f"Waypoints: {len(waypoints)} | Active: {mission.get('active_waypoint')}",
            (18, y),
            color=(180, 195, 205)
        )

        y += 22

        for index, waypoint in enumerate(waypoints[:3]):

            self._text(
                panel,
                f"{index}: x={waypoint.get('x', 0):.1f} y={waypoint.get('y', 0):.1f} z={waypoint.get('z', 0):.1f}",
                (18, y),
                color=(160, 175, 185)
            )

            y += 20

        return y

    def _draw_events(self, panel, events, y):

        if not events:

            self._text(panel, "No events yet", (18, y), color=(150, 160, 170))

            return y + 22

        for event in events[-self.max_events:]:

            age = time.time() - event.get("time", time.time())

            level = event.get("level", "INFO")

            message = event.get("message", "")

            color = self._event_color(level)

            self._text(panel, f"{age:4.1f}s {level}: {message}", (18, y), scale=0.42, color=color)

            y += 20

            if y > panel.shape[0] - 30:

                break

        return y

    def _draw_workers(self, panel, worker_statuses, y):

        if not worker_statuses:

            self._text(panel, "No workers registered", (18, y), color=(150, 160, 170))

            return y + 22

        for status in worker_statuses:

            alive = status["alive"]

            failed = status["failed"]

            color = (70, 210, 120) if alive and not failed else (80, 80, 230)

            label = "OK" if alive and not failed else "BAD"

            age = status["last_update_age"]

            self._text(
                panel,
                f"{status['name']}: {label} {age:.2f}s",
                (18, y),
                color=color
            )

            y += 22

            if y > panel.shape[0] - 30:

                break

        return y

    def _draw_latency(self, panel, latency, y):

        if not latency:

            self._text(panel, "No samples yet", (18, y), color=(150, 160, 170))

            return y + 22

        for name, stats in latency.items():

            self._text(
                panel,
                f"{name}: {stats['avg_ms']:.1f} ms avg",
                (18, y),
                color=(210, 220, 225)
            )

            y += 22

            if y > panel.shape[0] - 30:

                break

        return y

    def _draw_bbox(self, frame, bbox, color, label):

        if bbox is None:

            return

        x1, y1, x2, y2 = self._normalize_bbox(bbox)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        cv2.putText(
            frame,
            label,
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA
        )

    def _normalize_bbox(self, bbox):

        if len(bbox) != 4:

            return 0, 0, 0, 0

        x1, y1, x2, y2 = [int(value) for value in bbox]

        if x2 <= x1 or y2 <= y1:

            x2 = x1 + max(1, x2)

            y2 = y1 + max(1, y2)

        return x1, y1, x2, y2

    def _section(self, panel, title, y):

        cv2.line(panel, (18, y - 12), (self.panel_width - 18, y - 12), (55, 65, 75), 1)

        self._text(panel, title, (18, y), scale=0.52, color=(240, 240, 240), thickness=1)

    def _metric(self, panel, label, value, y, color):

        self._text(panel, label, (18, y), scale=0.5, color=(150, 160, 170))

        self._text(panel, str(value), (145, y), scale=0.5, color=color, thickness=1)

    def _text(self, panel, text, origin, scale=0.48, color=(220, 225, 230), thickness=1):

        cv2.putText(
            panel,
            str(text),
            origin,
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            color,
            thickness,
            cv2.LINE_AA
        )

    def _frame_age(self, snapshot):

        last_frame_time = snapshot.get("last_frame_time")

        if last_frame_time is None:

            return "none"

        return f"{time.time() - last_frame_time:.2f}s"

    def _mode_color(self, mode):

        if mode in {"SIM", "TRACKING"}:

            return (80, 220, 120)

        if mode in {"REACQUIRING", "RETURNING"}:

            return (70, 180, 255)

        if mode == "EMERGENCY":

            return (80, 80, 230)

        return (180, 190, 200)

    def _event_color(self, level):

        if level == "ERROR":

            return (80, 80, 230)

        if level == "WARN":

            return (70, 180, 255)

        return (190, 205, 215)
