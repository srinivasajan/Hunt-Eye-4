# HuntEye Configuration Guide (Dev 1.1)

HuntEye uses a structured YAML configuration system (`config.yaml`) that is validated and deep-merged with internal defaults at runtime.

## Core Settings

- `system.mode`: Starting system mode (`IDLE`, `TRACKING`, `EMERGENCY`).
- `system.backend`: Hardware backend to use (`AIRSIM` or `REAL`).

## Dashboard / UI

- `dashboard.panel_width`: Width of the side operations panel in pixels (default: 380).
- `dashboard.min_height`: Minimum height of the UI window in pixels (default: 600).
- `dashboard.show_latency`: Display rolling latency metrics in the UI (default: true).
- `dashboard.show_worker_health`: Display worker thread health statuses (default: true).
- `dashboard.show_target_overlay`: Render target bounding boxes on the camera feed (default: true).
- `dashboard.show_event_log`: Display recent system events (default: true).
- `dashboard.show_mission`: Display mission/waypoint status (default: true).
- `dashboard.show_controls`: Display keyboard control hints (default: true).
- `dashboard.max_events`: Number of recent events to keep in the UI buffer (default: 8).

## Hardware Abstraction Layer (HAL)

- `hal.sim.camera_api`: The API to use for AirSim frame retrieval (`simGetImage` or `simGetImages`).

## Reliability & Watchdog

- `watchdog.enabled`: Enable the system watchdog thread (default: true).
- `watchdog.interval_seconds`: How often the watchdog checks worker health (default: 2.0).
- `watchdog.auto_restart`: Automatically restart failed or stale workers (default: true).
- `watchdog.max_restarts_per_minute`: Restart limit to prevent infinite crash loops (default: 5).
- `watchdog.restart_cooldown_seconds`: Cooldown period before restarting a worker (default: 3.0).

- `monitor.interval_seconds`: How often to print diagnostic status to the console (default: 10.0).
- `monitor.stale_after_seconds`: Time before a worker without heartbeats is considered stale (default: 5.0).

## IPC & Telemetry

- `ipc.enabled`: Enable the IPC JSON server for cross-process communication (default: false).
- `ipc.host`: IP to bind the IPC server (default: `127.0.0.1`).
- `ipc.port`: Port to bind the IPC server (default: 5050).

- `telemetry_stream.enabled`: Enable remote telemetry streaming (default: false).
- `telemetry_stream.host`: IP to bind the telemetry stream server (default: `0.0.0.0`).
- `telemetry_stream.port`: Port to bind the telemetry stream server (default: 5051).
- `telemetry_stream.interval_seconds`: Update interval for stream pushes (default: 0.1).

## Recording

- `recording.default_fps`: Default target FPS for session recordings (default: 30.0).
- `recording.codec`: OpenCV VideoWriter FourCC code (default: `mp4v`).

## Plugins

- `plugins.enabled`: Enable dynamic loading of worker plugins (default: false).
- `plugins.paths`: List of directories to scan for plugins (default: `["plugins"]`).