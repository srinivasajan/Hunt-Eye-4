from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "system": {
        "mode": "sim",
        "debug": True,
    },
    "camera": {
        "name": "0",
        "sleep_seconds": 0.01,
        "width": 1280,
        "height": 720,
        "target_fps": 30,
    },
    "window": {
        "name": "HuntEye",
    },
    "dashboard": {
        "enabled": True,
        "panel_width": 430,
        "show_latency": True,
        "show_worker_health": True,
        "show_target_overlay": True,
        "show_event_log": True,
        "show_mission": True,
        "show_controls": True,
        "max_events": 6,
        "min_height": 720,
    },
    "recording": {
        "enabled": True,
        "folder": "recordings",
        "fps": 20,
        "codec": "mp4v",
    },
    "session": {
        "export_folder": "sessions",
    },
    "airsim": {
        "ip": "127.0.0.1",
    },
    "monitor": {
        "interval_seconds": 2.0,
        "stale_after_seconds": 2.0,
    },
    "safety": {
        "max_velocity": 5.0,
        "max_altitude": 30.0,
        "geofence_radius": 100.0,
    },
    "watchdog": {
        "enabled": True,
        "interval_seconds": 1.0,
        "auto_restart": False,
        "max_restarts_per_minute": 5,
        "restart_cooldown_seconds": 10.0,
    },
    "ipc": {
        "enabled": False,
        "host": "127.0.0.1",
        "port": 8765,
        # Optional shared token; set to null/None to disable auth.
        "token": None,
    },
    "telemetry_stream": {
        "enabled": False,
        "host": "127.0.0.1",
        "port": 8787,
        "interval_seconds": 0.5,
        "token": None,
    },
    "plugins": {
        "enabled": False,
        # Directory, .py file, or import path.
        "path": "plugins",
    },
    "logging": {
        "level": "INFO",
        "folder": "core/logs",
    },
    "hal": {
        "backend": "airsim",
    },
    "real": {
        "serial_port": "/dev/ttyUSB0",
        "baud_rate": 57600,
        "mavlink_connection": "udp:127.0.0.1:14550",
        "mavlink_timeout_seconds": 5.0,
        "require_mavlink": False,
        "camera_index": 0,
        "camera_api": "auto",
        "camera_width": 1280,
        "camera_height": 720,
        "camera_fps": 30,
        "require_camera": True,
    },
}


def load_config(path: str | Path = "config.yaml") -> dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)
    config_path = Path(path)

    if config_path.exists():
        loaded = _parse_simple_yaml(config_path.read_text(encoding="utf-8"))
        _deep_update(config, loaded)

    _validate_config(config)
    return config


def get_config_value(config: dict[str, Any], dotted_key: str, default: Any = None) -> Any:
    current: Any = config

    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]

    return current


def _deep_update(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].rstrip()

        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if ":" not in stripped:
            raise ValueError(f"Invalid config line {line_no}: {raw_line}")

        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]

        if raw_value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_scalar(raw_value)

    return root


def _parse_scalar(raw_value: str) -> Any:
    value = raw_value.strip()

    if value.startswith(("'", '"')) and value.endswith(("'", '"')):
        return value[1:-1]

    lowered = value.lower()

    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None

    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item.strip()) for item in inner.split(",")]

    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _validate_config(config: dict[str, Any]) -> None:
    mode = get_config_value(config, "system.mode")
    backend = get_config_value(config, "hal.backend")
    camera_api = get_config_value(config, "real.camera_api")
    ipc_port = get_config_value(config, "ipc.port")
    telemetry_port = get_config_value(config, "telemetry_stream.port")

    if mode not in {"sim", "real"}:
        raise ValueError("system.mode must be 'sim' or 'real'")

    if backend not in {"airsim", "real"}:
        raise ValueError("hal.backend must be 'airsim' or 'real'")

    if camera_api not in {"auto", "dshow", "msmf"}:
        raise ValueError("real.camera_api must be 'auto', 'dshow', or 'msmf'")

    if ipc_port is not None:
        try:
            ipc_port_int = int(ipc_port)
        except Exception as e:
            raise ValueError("ipc.port must be an integer") from e
        if ipc_port_int < 1 or ipc_port_int > 65535:
            raise ValueError("ipc.port must be between 1 and 65535")

    if telemetry_port is not None:
        try:
            telemetry_port_int = int(telemetry_port)
        except Exception as e:
            raise ValueError("telemetry_stream.port must be an integer") from e
        if telemetry_port_int < 1 or telemetry_port_int > 65535:
            raise ValueError("telemetry_stream.port must be between 1 and 65535")
