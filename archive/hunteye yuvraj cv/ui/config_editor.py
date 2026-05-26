"""Minimal config editor for HuntEye (Dev 1.2).

Constraints:
- Uses only scalar edits (bool/int/float/None). Strings are view-only.
- Writes config.yaml in a format compatible with config.loader._parse_simple_yaml.

Keys (expected):
- '[' / ']' : previous/next field
- space      : toggle bool
- '-' / '+'  : decrement/increment numeric
- 's'        : save config.yaml
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from core.logger import Logger
from config.writer import dump_simple_yaml


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (bool, int, float, str))


def _flatten(config: Dict[str, Any], prefix: str = "") -> List[Tuple[str, Any]]:
    items: List[Tuple[str, Any]] = []
    for key in sorted(config.keys()):
        value = config[key]
        dotted = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
        if isinstance(value, dict):
            items.extend(_flatten(value, dotted))
        else:
            if _is_scalar(value):
                items.append((dotted, value))
    return items


def _set_dotted(config: Dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    cur: Dict[str, Any] = config
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


@dataclass
class ConfigEditor:
    selected_index: int = 0
    scroll: int = 0

    def list_items(self, config: Dict[str, Any]) -> List[Tuple[str, Any]]:
        return _flatten(config)

    def clamp(self, items_count: int) -> None:
        if items_count <= 0:
            self.selected_index = 0
            self.scroll = 0
            return
        self.selected_index = max(0, min(self.selected_index, items_count - 1))
        self.scroll = max(0, min(self.scroll, max(0, items_count - 1)))

    def handle_key(self, key: int, config: Dict[str, Any]) -> str | None:
        items = self.list_items(config)
        self.clamp(len(items))
        if not items:
            return None

        if key in (ord("["),):
            self.selected_index -= 1
        elif key in (ord("]"),):
            self.selected_index += 1
        elif key == ord(" "):
            k, v = items[self.selected_index]
            if isinstance(v, bool):
                _set_dotted(config, k, not v)
                return f"toggled {k}"
        elif key in (ord("-"), ord("_"), ord("+"), ord("=")):
            k, v = items[self.selected_index]
            delta = 1
            if key in (ord("-"), ord("_")):
                delta = -1

            if isinstance(v, int) and not isinstance(v, bool):
                _set_dotted(config, k, int(v) + delta)
                return f"updated {k}"
            if isinstance(v, float):
                _set_dotted(config, k, float(v) + float(delta) * 0.1)
                return f"updated {k}"
        elif key in (ord("s"), ord("S")):
            try:
                yaml_text = dump_simple_yaml(config)
                with open("config.yaml", "w", encoding="utf-8") as f:
                    f.write(yaml_text)
                Logger.info("Config saved from UI")
                return "config saved (restart to apply)"
            except Exception as e:
                Logger.warning(f"Config save failed | error={e}")
                return "config save failed"

        self.clamp(len(items))
        # Keep the selected item in view (basic, panel height-dependent)
        self.scroll = max(0, self.selected_index - 4)
        return None
