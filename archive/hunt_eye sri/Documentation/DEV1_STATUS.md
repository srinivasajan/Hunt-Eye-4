# HuntEye — Dev 1 / Dev 1.1 / Dev 1.2 Status

> **Scope:** Infrastructure, Systems Engineering, Orchestration, Monitoring, UI/Dashboard, Operator Tooling.
> **Excludes:** Dev 2 (Perception/Tracking) and Dev 3 (AI/Autonomy/Control).

---

## 1. PAST — FOUNDATION MILESTONES (COMPLETED)

### 1.1 Environment & Toolchain

| Item | Status | Details |
|---|---|---|
| Python 3.10.11 | Done | Virtual environment isolated |
| PyTorch + CUDA | Done | `torch.cuda.is_available()` = True |
| OpenCV | Done | Frame rendering, overlay, window management |
| NumPy | Done | Image buffer and array operations |
| AirSim API | Done | MultirotorClient RPC verified |

### 1.2 AirSim Integration

| Item | Status | Details |
|---|---|---|
| Simulator launch (AirSimNH) | Done | Unreal Engine environment |
| Drone mode config | Done | API control, arm, takeoff |
| Python RPC communication | Done | `test_airsim.py` verified |
| Camera streaming | Done | Frame buffer decode + live render |

### 1.3 Project Structure

```
hunt_eye/
├── core/          # Infrastructure backbone
├── simulation/    # Simulator + camera abstraction
├── perception/    # (reserved for Dev 2)
├── tracking/      # (reserved for Dev 2)
├── ai/            # (reserved for Dev 3)
├── control/       # (reserved for Dev 3)
├── ui/            # Dashboard + ops state
├── config/        # Config loader + defaults
├── recordings/    # Session recording output
├── sessions/      # Snapshot export output
├── main.py        # Runtime entrypoint
├── config.yaml    # External configuration
└── test_airsim.py # Connectivity test
```

### 1.4 Core Infrastructure (Dev 1.1)

| Component | File | Lines | Capabilities |
|---|---|---|---|
| **SharedState** | `core/shared_state.py` | 110 | Thread-safe centralized memory, RLock, snapshot, event bus integration, profiler integration |
| **WorkerBase** | `core/worker_base.py` | 110 | Thread subclass, lifecycle, heartbeat, exception-safe loop, stop/status API |
| **Orchestrator** | `core/orchestrator.py` | 111 | Worker registration, start/stop sequencing, restart with factory, status aggregation |
| **Config System** | `config/loader.py` | 225 | YAML parsing, deep-merge with defaults, validation (mode, backend, camera API) |
| **Config Settings** | `config/settings.py` | 21 | Pythonic settings constants |
| **Logger** | `core/logger.py` | 37 | File + stream handlers, structured format, lifecycle logging |
| **Monitor** | `core/monitor.py` | 25 | Worker health diagnostics, stale detection, console status |
| **FPSCounter** | `core/fps_counter.py` | 32 | Rolling average FPS calculation |
| **EventBus** | `core/event_bus.py` | 54 | Pub/sub with subscribe/unsubscribe/emit, exception-safe callbacks |
| **Watchdog** | `core/watchdog.py` | 109 | Periodic worker health check, stale/dead/failed detection, auto-restart, event emission |
| **HAL** | `core/hal.py` | 339 | Abstract backend (AirSimBackend + RealBackend), sim-to-real switching, frame/telemetry/velocity APIs |
| **LatencyProfiler** | `core/profiler.py` | 52 | Context-manager timing, rolling samples, avg/max metrics |

### 1.5 Camera Pipeline (Dev 1.1)

| Component | File | Lines | Capabilities |
|---|---|---|---|
| **CameraStream** | `simulation/camera.py` | 15 | Wraps HAL for frame acquisition |
| **CameraWorker** | `simulation/camera_worker.py` | 38 | Independent thread, async frame updates, profiler integration |
| **Legacy stream** | `simulation/camera_stream.py` | 20 | Original proof-of-concept (superseded) |

### 1.6 UI / Dashboard (Dev 1.2)

| Component | File | Lines | Capabilities |
|---|---|---|---|
| **OperationsDashboard** | `ui/dashboard.py` | 713 | Live frame + panel rendering, telemetry, workers, latency, events, mission, controls, target overlay |
| **EventLog** | `ui/ops_state.py` | 9–34 | Time-stamped event ring buffer |
| **TelemetryHistory** | `ui/ops_state.py` | 35–58 | Rolling telemetry sample buffer |
| **MissionState** | `ui/ops_state.py` | 59–83 | Waypoint management, status tracking |
| **OperatorControls** | `ui/ops_state.py` | 84–104 | Mode set, pause toggle |
| **SessionRecorder** | `ui/ops_state.py` | 105–198 | Video recording with codec config |
| **SessionExporter** | `ui/ops_state.py` | 199–219 | JSON snapshot export |

### 1.7 Runtime Entrypoint (main.py)

| Feature | Details |
|---|---|
| Worker initialization | CameraWorker + Watchdog |
| Main loop | Frame acquisition, telemetry polling, FPS tracking, dashboard render, key handling |
| Key bindings | `q` quit, `r` record, `p` pause, `i` idle, `t` tracking, `e` emergency, `w` waypoint, `c` clear, `s` snapshot, `o/d/g/y` switch panels, `1/2/3` overlays, `l` save layout |
| Shutdown | Graceful recorder stop, orchestrator stop, HAL close, window destroy |

---

## 2. PRESENT — CURRENT SYSTEM CAPABILITIES

### 2.1 Runtime Architecture

- **Multithreaded execution** — workers run independently in daemon threads
- **Shared-state communication** — all modules read/write through `SharedState` with `RLock`
- **Centralized orchestration** — Orchestrator manages worker lifecycle (register, start, stop, restart)
- **Config-driven** — external `config.yaml` with defaults, validation, hot-reload ready
- **Structured logging** — file + console output with timestamps and levels

### 2.2 Reliability

- **Exception-safe workers** — crashes caught, logged, and tracked in worker status
- **Health monitoring** — periodic diagnostics via `Monitor.print_status()`
- **Watchdog** — automatic stale/dead/failed detection with event emission
- **Auto-restart** — configurable automatic worker restart on failure
- **Heartbeat** — per-worker timestamp tracking for hang detection

### 2.3 Simulation Interface

- **HAL abstraction** — `AirSimBackend` (current) and `RealBackend` (ready) switchable via config
- **Frame acquisition** — AirSim `simGetImage` → buffer decode → OpenCV frame
- **Telemetry** — position, velocity, landed state
- **Velocity control** — `moveByVelocityAsync` via HAL

### 2.4 Operational Tooling

- **Live dashboard** — real-time FPS, telemetry, worker health, event log, latency metrics
- **Target overlay** — bounding boxes for detections, tracks, and active target
- **Recording** — video capture to MP4 with configurable codec
- **Snapshot export** — JSON state snapshots to `sessions/`
- **Mission waypoints** — add/clear waypoints from current position
- **Mode switching** — IDLE / TRACKING / EMERGENCY via key bindings

### 2.5 Performance

- **FPS monitoring** — rolling average displayed on dashboard
- **Latency profiling** — per-operation timing (e.g., `camera_get_frame`) with avg/max/samples
- **~64 FPS** achieved in stable rendering (documented from earlier testing)

---

## 3. FUTURE — REMAINING WORK

### 3.1 Dev 1.1 — Infrastructure Gaps

| Priority | Feature | Description | Status |
|---|---|---|---|
| High | **IPC / Inter-Process Communication** | Cross-process messaging for distributed deployment | **Done** - `core/ipc.py` (NDJSON TCP), wired via `config.yaml` -> `ipc.enabled` |
| High | **Runtime Scheduler** | Timed/periodic task scheduling (e.g., maintenance, periodic telemetry) | **Done** - `core/scheduler.py` |
| High | **Pipeline Execution Graph** | Dependency-aware execution sequencing for perception/tracking/control pipelines | **Done** - `core/pipeline_graph.py` (DAG + executor worker) |
| High | **Dev 2 Integration Layer** | SharedState schema, worker templates, and wiring for DetectorWorker + TrackerWorker | **Partially done** - base classes exist (`core/detector_base.py`, `core/tracker_base.py`); concrete workers + pipeline wiring still needed |
| High | **Dev 3 Integration Layer** | SharedState schema, worker templates, and wiring for ControlWorker + AIWorker | Not started |
| Medium | **Reliability Hardening** | Graceful degradation, circuit breakers, crash isolation zones | **Done** - restart limiting + zone quarantine (`core/restart_limiter.py`, `core/watchdog.py`, `core/worker_base.py`) |
| Medium | **Deployment Runtime** | Packaging, installer, environment bootstrap script, dependency freeze | **Done** - freeze script (`tools/freeze_requirements.ps1`), PyInstaller build (`tools/build.ps1`), CI artifact build (`.github/workflows/build-windows.yml`), docs (`Documentation/DEPLOYMENT.md`) |
| Medium | **Service Registry** | Central registry for runtime service discovery | **Done** - `core/service_registry.py` |
| Low | **Plugin Architecture** | Dynamic module loading, plugin API, hot-swap workers | **Done** - minimal loader (`core/plugin_loader.py`), wired via `config.yaml` -> `plugins.enabled` (+ `plugins.path`) |
| Low | **Distributed Telemetry** | Remote telemetry streaming over network (WebSocket / gRPC) | **Done** - NDJSON stream server (`core/telemetry_stream.py`), wired via `config.yaml` -> `telemetry_stream.enabled` |

### 3.2 Dev 1.2 — UI / Dashboard Gaps

| Priority | Feature | Description | Status |
|---|---|---|---|
| Medium | **Analytics Graphs** | Time-series charts for FPS, latency, telemetry over time | **Done** - `ui/analytics_panel.py` |
| Medium | **Replay / Playback System** | Session recording playback with seek, speed control, frame-by-frame | **Done** - `ui/replay_system.py` |
| Medium | **Diagnostics Panel** | Dedicated diagnostics view with error history, stack traces, system info | **Done (basic)** - DIAG panel with worker summary + recent events (`ui/dashboard.py`, `ui/diagnostics_utils.py`) |
| Medium | **Debug Visualizers** | Depth map overlay, cost map visualization, path preview | **Done (basic)** - toggles + overlays (`ui/ui_state.py`, `ui/dashboard.py`) |
| Low | **Config Editor UI** | Graphical config editor with validation feedback | **Done (basic)** - selection/edit/save for scalar fields (`ui/config_editor.py`, `config/writer.py`) |
| Low | **Waypoint Visual Editor** | Map/grid-based waypoint placement and editing | **Partial** - list-based editor + numeric nudge controls (`ui/waypoint_editor.py`, `ui/dashboard.py`) |
| Low | **Advanced Usability** | Drag-and-drop panels, theme support, layout persistence | **Partial** - layout persistence only (`ui/layout_persistence.py`) |

### 3.3 Quality & Maintenance

| Item | Description | Status |
|---|---|---|
| **`core/__init__.py`** | Missing package init files for clean imports | **Done** |
| **Unit tests** | Test coverage for orchestrator, worker_base, shared_state, event_bus, watchdog | Not started |
| **Type annotations** | Full mypy-compatible type hints across entire codebase | Partial |
| **Config documentation** | Document all config fields and their effects | Not started |
| **Error handling audit** | Systematic review of all exception paths and recovery | Not done |

---

## 4. KEY OBSERVATIONS

### 4.1 Documentation Is Outdated

The previous documentation lists several features as "remaining" that are already implemented:

- Watchdog system ✅ done
- Event bus / pub-sub ✅ done
- HAL abstraction + sim-to-real switching ✅ done
- Profiler / latency tracing ✅ done
- Structured config loader with validation ✅ done
- Operations dashboard ✅ done
- Recording system ✅ done
- Mission planner ✅ done
- Operator controls ✅ done

### 4.2 Dev 1.1 Has Delivered Beyond Original Scope

The codebase contains infrastructure that goes well beyond the original plan:
- `core/event_bus.py` — pub/sub was planned as future
- `core/watchdog.py` — auto-restart was planned as future
- `core/hal.py` — full sim/real abstraction was planned as future
- `core/profiler.py` — latency tracing was planned as future
- `config/loader.py` — structured config with YAML and validation was planned as future

### 4.3 Empty Module Directories

These directories exist but have no code — they are reserved for Dev 2 and Dev 3:
- `perception/` — empty
- `tracking/` — empty
- `ai/` — empty
- `control/` — empty

Integration with these is the next major milestone for Dev 1.1.

### 4.4 Architecture Maturity

The current system has evolved from "basic scripts" to a **modular robotics runtime** with:
- Independent worker threads ↔ centralized shared state
- Config-driven hardware abstraction layer
- Health monitoring + watchdog reliability
- Pub/sub event communication
- Latency profiling instrumentation
- Full operational dashboard with recording and mission support

The infrastructure foundation is solid and ready for perception/tracking/control integration.
