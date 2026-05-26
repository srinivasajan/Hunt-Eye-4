"""Waypoint editor for HuntEye missions (Dev 1.2).

This operates on SharedState.mission['waypoints'].

Keys (when panel_mode=WAYPOINTS):
- '[' / ']' : select prev/next waypoint
- 'x'       : delete selected
- 'c'       : clear all waypoints
- 'h'/'l'   : x -/+ step
- 'j'/'k'   : y -/+ step
- 'u'/'i'   : z -/+ step

Adding a waypoint remains 'w' (existing behavior).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class WaypointEditor:
    selected_index: int = 0
    step: float = 1.0

    def _waypoints(self, state: Any) -> List[Dict[str, Any]]:
        return list(getattr(state, "mission", {}).get("waypoints", []))

    def clamp(self, count: int) -> None:
        if count <= 0:
            self.selected_index = 0
        else:
            self.selected_index = max(0, min(self.selected_index, count - 1))

    def handle_key(self, key: int, state: Any) -> str | None:
        with state.lock:
            waypoints = state.mission.get("waypoints", [])
            count = len(waypoints)
            self.clamp(count)

            if key == ord("["):
                self.selected_index -= 1
                self.clamp(count)
                return None
            if key == ord("]"):
                self.selected_index += 1
                self.clamp(count)
                return None

            if key in (ord("c"), ord("C")):
                state.mission["waypoints"] = []
                state.mission["active_waypoint"] = None
                state.mission["status"] = "IDLE"
                self.selected_index = 0
                return "cleared waypoints"

            if count == 0:
                return None

            if key in (ord("x"), ord("X")):
                del waypoints[self.selected_index]
                if not waypoints:
                    state.mission["active_waypoint"] = None
                    state.mission["status"] = "IDLE"
                    self.selected_index = 0
                else:
                    self.clamp(len(waypoints))
                    state.mission["status"] = "PLANNED"
                return "deleted waypoint"

            wp = waypoints[self.selected_index]
            if key in (ord("h"), ord("H")):
                wp["x"] = float(wp.get("x", 0.0)) - self.step
                return "updated x"
            if key in (ord("l"), ord("L")):
                wp["x"] = float(wp.get("x", 0.0)) + self.step
                return "updated x"
            if key in (ord("j"), ord("J")):
                wp["y"] = float(wp.get("y", 0.0)) - self.step
                return "updated y"
            if key in (ord("k"), ord("K")):
                wp["y"] = float(wp.get("y", 0.0)) + self.step
                return "updated y"
            if key in (ord("u"), ord("U")):
                wp["z"] = float(wp.get("z", 0.0)) - self.step
                return "updated z"
            if key in (ord("i"), ord("I")):
                wp["z"] = float(wp.get("z", 0.0)) + self.step
                return "updated z"

            state.mission["status"] = "PLANNED"

        return None
