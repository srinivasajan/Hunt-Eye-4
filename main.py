import cv2
import time
import sys
import os

# Ensure PyTorch uses local offline cache before loading any Torch libraries
os.environ["TORCH_HOME"] = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "models", "torch_hub_cache")

# Add src to the Python path to allow imports from the src directory
sys.path.insert(0, os.path.abspath('src'))

from config import WINDOW_NAME, load_config
from core.hal import HAL
from core.logger import Logger
from core.shared_state import SharedState
from core.safety import SafetyLayer
from core.orchestrator import Orchestrator
from core.monitor import Monitor
from core.fps_counter import FPSCounter
from core.watchdog import Watchdog
from core.ipc import IPCServerWorker
from core.telemetry_stream import TelemetryStreamServerWorker
from core.plugin_loader import load_plugins
from core.service_registry import get_service_registry

from simulation.camera_worker import CameraWorker
from ui.dashboard import OperationsDashboard
from ui.ops_state import (
    EventLog,
    MissionState,
    OperatorControls,
    SessionExporter,
    SessionRecorder,
    TelemetryHistory,
)
from ui.ui_state import UIState
from ui.layout_persistence import load_layout, save_layout
from ui.config_editor import ConfigEditor
from ui.waypoint_editor import WaypointEditor
from ui import preflight
from ui import hud as hud_overlay
from ui.demo_scene import DemoScene
from ai.planner import AStarPlanner
from control.mavlink_interface import PIDController
from control.worker import ControlWorker
from perception.worker import PerceptionWorker

# Input source passed from launcher via environment variable
_INPUT_SOURCE = os.environ.get("HUNTEYE_SOURCE", "SIMULATOR").upper()



def main():

    config = load_config()

    # -- Stage 1 --
    preflight.render_startup(WINDOW_NAME, step=1, source=_INPUT_SOURCE)

    state = SharedState()
    state.system_mode = config["system"]["mode"].upper()
    orchestrator = Orchestrator()

    # -- Stage 2 --
    preflight.render_startup(WINDOW_NAME, step=2, source=_INPUT_SOURCE)

    registry = get_service_registry()
    registry.register_service("config", config, override=True)
    registry.register_service("state", state, override=True)
    registry.register_service("orchestrator", orchestrator, override=True)

    # One shared HAL instance — used by both CameraWorker and ControlWorker.
    # This is intentional: creating multiple HAL instances would cause multiple
    # independent AirSim connection attempts, bypassing the NullBackend fallback
    # and causing CameraWorker to retry AirSim even after failover.
    shared_hal = HAL(config)

    safety_config = config.get("safety", {})
    safety = SafetyLayer(
        max_velocity=safety_config.get("max_velocity", 5.0),
        max_altitude=safety_config.get("max_altitude", 30.0),
        geofence_radius=safety_config.get("geofence_radius", 100.0),
    )
    pid = PIDController()
    planner = AStarPlanner()

    # CameraWorker receives the shared HAL.  The factory also uses the same
    # shared_hal so restarts don't create new AirSim connection attempts.
    def build_camera_worker():
        return CameraWorker(
            state=state,
            hal=shared_hal,
            config=config
        )

    camera_worker = build_camera_worker()
    orchestrator.add_worker(camera_worker, factory=build_camera_worker)

    # Perception and Tracking Worker
    def build_perception_worker():
        return PerceptionWorker(state=state, config=config)
    orchestrator.add_worker(build_perception_worker(), factory=build_perception_worker)

    # Control Worker — also uses the shared HAL
    def build_control_worker():
        return ControlWorker(state=state, hal=shared_hal, config=config, pid=pid, planner=planner, safety=safety)
    orchestrator.add_worker(build_control_worker(), factory=build_control_worker)


    if config.get("plugins", {}).get("enabled"):

        plugin_cfg = config.get("plugins", {})
        plugin_paths = plugin_cfg.get("paths")
        if not plugin_paths:
            plugin_paths = [plugin_cfg.get("path", "plugins")]
        elif isinstance(plugin_paths, str):
            plugin_paths = [plugin_paths]

        loaded = load_plugins(
            state=state,
            orchestrator=orchestrator,
            config=config,
            paths=plugin_paths,
        )
        Logger.info(f"Plugins loaded | count={len(loaded)}")

    # -- Stage 3: hardware / comms connecting ---------------------------------
    preflight.render_startup(
        WINDOW_NAME, step=3,
        degraded=shared_hal.degraded,
        degraded_reason=shared_hal.degraded_reason,
        source=_INPUT_SOURCE,
    )
    if shared_hal.degraded:
        Logger.warning(
            f"Runtime starting in degraded mode | reason={shared_hal.degraded_reason}"
        )

    if config.get("ipc", {}).get("enabled"):

        ipc = IPCServerWorker(
            state=state,
            orchestrator=orchestrator,
            host=config["ipc"]["host"],
            port=config["ipc"]["port"],
            token=config["ipc"].get("token"),
        )

        orchestrator.add_worker(ipc)

    if config.get("telemetry_stream", {}).get("enabled"):

        telemetry_stream = TelemetryStreamServerWorker(
            state=state,
            host=config["telemetry_stream"]["host"],
            port=config["telemetry_stream"]["port"],
            interval_seconds=config["telemetry_stream"]["interval_seconds"],
            token=config["telemetry_stream"].get("token"),
        )

        orchestrator.add_worker(telemetry_stream)

    if config["watchdog"]["enabled"]:

        watchdog = Watchdog(
            orchestrator=orchestrator,
            event_bus=state.event_bus,
            interval_seconds=config["watchdog"]["interval_seconds"],
            stale_after_seconds=config["monitor"]["stale_after_seconds"],
            auto_restart=config["watchdog"]["auto_restart"],
            max_restarts_per_minute=config["watchdog"]["max_restarts_per_minute"],
            restart_cooldown_seconds=config["watchdog"]["restart_cooldown_seconds"],
        )

        orchestrator.add_worker(watchdog)

    monitor = Monitor(
        orchestrator,
        stale_after_seconds=config["monitor"]["stale_after_seconds"]
    )

    fps_counter = FPSCounter()

    dashboard = OperationsDashboard(config)

    event_log = EventLog()

    telemetry_history = TelemetryHistory()

    mission_state = MissionState()

    operator_controls = OperatorControls()

    recorder = SessionRecorder(config)

    exporter = SessionExporter(config)

    layout_data = load_layout()
    ui_state = UIState.from_dict(layout_data.get("ui_state"))
    config_editor = ConfigEditor(
        selected_index=ui_state.config_selected_index,
        scroll=ui_state.config_scroll,
    )
    waypoint_editor = WaypointEditor(
        selected_index=ui_state.waypoint_selected_index,
    )

    state.event_bus.subscribe(
        "TEST_EVENT",
        lambda data: event_log.append(state, "INFO", "Event bus ready", data)
    )

    state.event_bus.subscribe(
        "WORKER_UNHEALTHY",
        lambda data: event_log.append(
            state,
            "WARN",
            f"{data['worker']} unhealthy",
            data
        )
    )

    Logger.info("HuntEye runtime starting")

    event_log.append(state, "INFO", "Runtime starting")

    orchestrator.start()

    # -- Stage 4: workers running --
    preflight.render_startup(
        WINDOW_NAME, step=4,
        degraded=shared_hal.degraded,
        degraded_reason=shared_hal.degraded_reason,
        source=_INPUT_SOURCE,
    )

    state.event_bus.emit("TEST_EVENT", {"message": "Event Bus Working"})

    # Surface degraded mode in the dashboard event log.
    if shared_hal.degraded:
        event_log.append(
            state, "WARN",
            f"DEGRADED MODE: {shared_hal.degraded_reason}",
        )

    # -- Stage 5: ready --
    preflight.render_startup(
        WINDOW_NAME, step=5,
        degraded=shared_hal.degraded,
        degraded_reason=shared_hal.degraded_reason,
        source=_INPUT_SOURCE,
    )
    time.sleep(0.5)

    # -----------------------------------------------------------------------
    # READY STATE — operator sees capability summary, presses SPACE to start
    # -----------------------------------------------------------------------
    ai_available = getattr(getattr(shared_hal, 'backend', None), '_dead', False) is False
    depth_available = False  # MiDaS optional; update if loaded

    # Detect whether AI models actually loaded by checking PerceptionWorker state
    # (conservative default — the worker logs will confirm)
    try:
        from ultralytics import YOLO  # noqa: F401
        ai_available = True
    except ImportError:
        ai_available = False

    # Set initial UIState fields from runtime context
    ui_state.input_source = _INPUT_SOURCE
    ui_state.app_state = "DEGRADED" if shared_hal.degraded else "READY"

    # Show the READY screen and wait for SPACE or Q
    while True:
        preflight.render_ready(
            WINDOW_NAME,
            degraded=shared_hal.degraded,
            degraded_reason=shared_hal.degraded_reason,
            source=_INPUT_SOURCE,
            ai_available=ai_available,
            depth_available=depth_available,
        )
        key = cv2.waitKey(40) & 0xFF
        if key == ord('q') or key == 27:  # Q or ESC
            Logger.info("Operator quit at READY screen.")
            orchestrator.stop()
            shared_hal.close()
            cv2.destroyAllWindows()
            return
        if key == ord(' '):
            ui_state.app_state = "LIVE"
            event_log.append(state, "INFO", "Mission started by operator.")
            break
        if key == ord('d'):
            ui_state.panel_mode = "DIAG"
            ui_state.app_state = "LIVE"
            break

    # Initialize DemoScene if we are in degraded mode
    demo = DemoScene() if shared_hal.degraded else None

    last_monitor = time.time()

    try:

        while True:

            display_frame = None

            frame = state.get_latest_frame()

            if frame is not None:

                fps_counter.update()
                fps = fps_counter.get_fps()
                snapshot = state.snapshot()

                if shared_hal.degraded:
                    demo_patch = demo.update()
                    snapshot.update(demo_patch)
                    
                    # Also override the shared state's mission started_at so the timer runs in demo mode
                    if "started_at" not in state._state["mission"] and ui_state.tracking_state != "SEARCHING":
                         state._state["mission"]["started_at"] = time.time()
                         state._state["mission"]["status"] = "ACTIVE"
                    if snapshot.get("target_bbox") is not None:
                         state.system_mode = "TRACKING"
                    else:
                         state.system_mode = "IDLE"
                    snapshot["system_mode"] = state.system_mode

                worker_statuses = orchestrator.status()

                for status in worker_statuses:
                    state.update_worker_health(status["name"], status)

                # Apply tactical HUD overlays on top of the raw frame
                hud_frame = hud_overlay.draw_live_hud(
                    frame, snapshot, ui_state, fps
                )

                display_frame = dashboard.render(
                    hud_frame,
                    snapshot,
                    worker_statuses,
                    fps,
                    ui_state=ui_state,
                    config_for_editor=config,
                )

                recorder.write(state, display_frame)
                cv2.imshow(WINDOW_NAME, display_frame)

            if time.time() - last_monitor > config["monitor"]["interval_seconds"]:

                monitor.print_status()

                last_monitor = time.time()

            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                break

            if key != 255:

                _handle_keypress(
                    key,
                    config,
                    state,
                    event_log,
                    mission_state,
                    operator_controls,
                    recorder,
                    exporter,
                    display_frame,
                    ui_state,
                    config_editor,
                    waypoint_editor,
                )

    finally:

        try:
            ui_state.config_selected_index = config_editor.selected_index
            ui_state.config_scroll = config_editor.scroll
            ui_state.waypoint_selected_index = waypoint_editor.selected_index
            save_layout({"ui_state": ui_state.to_dict()})
        except Exception:
            pass

        recorder.stop(state)

        orchestrator.stop()

        shared_hal.close()

        cv2.destroyAllWindows()

        Logger.info("HuntEye runtime stopped")
        import sys
        sys.exit(0)


def _handle_keypress(
    key,
    config,
    state,
    event_log,
    mission_state,
    operator_controls,
    recorder,
    exporter,
    frame,
    ui_state,
    config_editor,
    waypoint_editor,
):

    # Panel mode switching
    if key in (ord('o'), ord('O')):
        ui_state.panel_mode = "OPS"
        event_log.append(state, "INFO", "Panel: OPS")
        return
    if key in (ord('d'), ord('D')):
        ui_state.panel_mode = "DIAG"
        event_log.append(state, "INFO", "Panel: DIAG")
        return
    if key in (ord('g'), ord('G')):
        ui_state.panel_mode = "CONFIG"
        event_log.append(state, "INFO", "Panel: CONFIG")
        return
    if key in (ord('y'), ord('Y')):
        ui_state.panel_mode = "WAYPOINTS"
        event_log.append(state, "INFO", "Panel: WAYPOINTS")
        return

    # Debug visualizers
    if key == ord('1'):
        ui_state.show_depth_overlay = not ui_state.show_depth_overlay
        event_log.append(state, "INFO", f"Depth overlay: {ui_state.show_depth_overlay}")
        return
    if key == ord('2'):
        ui_state.show_cost_overlay = not ui_state.show_cost_overlay
        event_log.append(state, "INFO", f"Cost overlay: {ui_state.show_cost_overlay}")
        return
    if key == ord('3'):
        ui_state.show_path_overlay = not ui_state.show_path_overlay
        event_log.append(state, "INFO", f"Path overlay: {ui_state.show_path_overlay}")
        return

    # Advanced usability: explicit layout save
    if key in (ord('l'), ord('L')):
        ui_state.config_selected_index = config_editor.selected_index
        ui_state.config_scroll = config_editor.scroll
        ui_state.waypoint_selected_index = waypoint_editor.selected_index
        ok = save_layout({"ui_state": ui_state.to_dict()})
        event_log.append(state, "INFO", "Layout saved" if ok else "Layout save failed")
        return

    # Theme toggle
    if key in (ord('m'), ord('M')):
        ui_state.theme = "LIGHT" if ui_state.theme == "DARK" else "DARK"
        event_log.append(state, "INFO", f"Theme: {ui_state.theme}")
        return

    # Layout reordering
    if key in (ord('v'), ord('V')):
        if not hasattr(ui_state, "panel_order") or not ui_state.panel_order:
            ui_state.panel_order = ["latency", "workers", "mission", "events"]
        # Rotate the first element to the back
        po = ui_state.panel_order
        ui_state.panel_order = po[1:] + [po[0]]
        event_log.append(state, "INFO", f"Layout changed: {ui_state.panel_order[0].upper()} first")
        return

    # Contextual editors
    if ui_state.panel_mode == "CONFIG":
        msg = config_editor.handle_key(key, config)
        ui_state.config_selected_index = config_editor.selected_index
        ui_state.config_scroll = config_editor.scroll
        if msg:
            event_log.append(state, "INFO", msg)
        return

    if ui_state.panel_mode == "WAYPOINTS":
        msg = waypoint_editor.handle_key(key, state)
        ui_state.waypoint_selected_index = waypoint_editor.selected_index
        if msg:
            event_log.append(state, "INFO", msg)
        return

    if key in (ord('r'), ord('R')) and frame is not None:
        active = recorder.toggle(state, frame.shape)
        event_log.append(state, "INFO", "Recording started" if active else "Recording stopped")

    elif key in (ord('s'), ord('S')) and frame is not None:
        import os
        from pathlib import Path
        from core.paths import get_app_dir
        folder = get_app_dir() / config.get("recording", {}).get("folder", "recordings") / "screenshots"
        folder.mkdir(parents=True, exist_ok=True)
        import time
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = folder / f"screenshot_{ts}.png"
        cv2.imwrite(str(path), frame)
        event_log.append(state, "INFO", f"Screenshot saved")

    elif key in (ord('p'), 32):  # P or SPACE = pause/resume
        paused = operator_controls.toggle_pause(state)
        event_log.append(state, "INFO", "Paused" if paused else "Resumed")

    elif key == ord('i'):

        operator_controls.set_mode(state, "IDLE")

        event_log.append(state, "INFO", "Mode set to IDLE")

    elif key == ord('t'):

        operator_controls.set_mode(state, "TRACKING")

        event_log.append(state, "INFO", "Mode set to TRACKING")

    elif key == ord('e'):

        operator_controls.set_mode(state, "EMERGENCY")

        event_log.append(state, "ERROR", "Emergency mode requested")

    elif key == ord('w'):

        waypoint = _current_waypoint(state)

        mission_state.add_waypoint(state, waypoint)

        event_log.append(state, "INFO", "Waypoint added", waypoint)

    elif key == ord('c'):

        mission_state.clear(state)

        event_log.append(state, "INFO", "Mission cleared")

    elif key == ord('s'):

        path = exporter.export_snapshot(state.snapshot())

        event_log.append(state, "INFO", "Snapshot exported", {"path": path})


def _current_waypoint(state):

    with state.lock:

        position = state.telemetry.get("position", {})

    return {
        "x": float(position.get("x", 0.0)),
        "y": float(position.get("y", 0.0)),
        "z": float(position.get("z", 0.0)),
        "time": time.time(),
    }


def _normalize_bbox(bbox):
    x1, y1, a, b = [float(v) for v in bbox[:4]]
    if a > x1 and b > y1:
        return x1, y1, a - x1, b - y1
    return x1, y1, a, b


if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception as e:
        Logger.error(f"FATAL CRASH in main: {e}")
        with open("crash_log.txt", "w") as f:
            f.write(traceback.format_exc())
            print(f"CRASH: {e}\nCheck crash_log.txt")
