import cv2
import time

from config import WINDOW_NAME, load_config
from core.hal import HAL
from core.logger import Logger
from core.shared_state import SharedState
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


def main():

    config = load_config()

    state = SharedState()

    state.system_mode = config["system"]["mode"].upper()

    orchestrator = Orchestrator()

    registry = get_service_registry()
    registry.register_service("config", config, override=True)
    registry.register_service("state", state, override=True)
    registry.register_service("orchestrator", orchestrator, override=True)

    telemetry_hal = HAL(config)

    def build_camera_worker():

        return CameraWorker(
            state=state,
            hal=HAL(config),
            config=config
        )

    camera_worker = build_camera_worker()

    orchestrator.add_worker(camera_worker, factory=build_camera_worker)

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

    state.event_bus.emit(
        "TEST_EVENT",
        {"message": "Event Bus Working"}
    )

    last_monitor = time.time()

    try:

        while True:

            display_frame = None

            frame = state.get_latest_frame()

            if frame is not None:

                fps_counter.update()

                fps = fps_counter.get_fps()

                try:

                    telemetry = telemetry_hal.get_telemetry()

                    with state.lock:

                        state.telemetry = telemetry

                    telemetry_history.append(state, telemetry)

                except Exception as error:

                    Logger.warning(f"Telemetry update failed | error={error}")

                    event_log.append(state, "WARN", "Telemetry update failed", {"error": str(error)})

                snapshot = state.snapshot()

                worker_statuses = orchestrator.status()

                for status in worker_statuses:

                    state.update_worker_health(status["name"], status)

                display_frame = dashboard.render(
                    frame,
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

        telemetry_hal.close()

        cv2.destroyAllWindows()

        Logger.info("HuntEye runtime stopped")


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

    if key == ord('r') and frame is not None:

        active = recorder.toggle(state, frame.shape)

        event_log.append(state, "INFO", "Recording started" if active else "Recording stopped")

    elif key == ord('p'):

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


if __name__ == "__main__":

    main()
