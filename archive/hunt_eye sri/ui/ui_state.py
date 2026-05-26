"""UI state for HuntEye dashboard (Dev 1.2 usability + editors).

This keeps interactive dashboard state separate from SharedState.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class UIState:
    panel_mode: str = "OPS"  # OPS | DIAG | CONFIG | WAYPOINTS

    # Debug visualizer overlays
    show_depth_overlay: bool = False
    show_cost_overlay: bool = False
    show_path_overlay: bool = True

    # Editors
    config_selected_index: int = 0
    config_scroll: int = 0

    waypoint_selected_index: int = 0
    theme: str = "DARK"
    
    # Ordered list of panel sections for the OPS dashboard
    panel_order: list[str] = None

    def __post_init__(self):
        if self.panel_order is None:
            self.panel_order = ["latency", "workers", "mission", "events"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "panel_mode": self.panel_mode,
            "show_depth_overlay": self.show_depth_overlay,
            "show_cost_overlay": self.show_cost_overlay,
            "show_path_overlay": self.show_path_overlay,
            "config_selected_index": self.config_selected_index,
            "config_scroll": self.config_scroll,
            "waypoint_selected_index": self.waypoint_selected_index,
            "theme": self.theme,
            "panel_order": self.panel_order,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | None) -> "UIState":
        if not isinstance(data, dict):
            return cls()

        state = cls()
        state.panel_mode = str(data.get("panel_mode", state.panel_mode)).upper()
        state.show_depth_overlay = bool(data.get("show_depth_overlay", state.show_depth_overlay))
        state.show_cost_overlay = bool(data.get("show_cost_overlay", state.show_cost_overlay))
        state.show_path_overlay = bool(data.get("show_path_overlay", state.show_path_overlay))
        state.config_selected_index = int(data.get("config_selected_index", state.config_selected_index) or 0)
        state.config_scroll = int(data.get("config_scroll", state.config_scroll) or 0)
        state.waypoint_selected_index = int(data.get("waypoint_selected_index", state.waypoint_selected_index) or 0)
        state.theme = str(data.get("theme", state.theme)).upper()
        state.panel_order = data.get("panel_order", ["latency", "workers", "mission", "events"])
        return state
