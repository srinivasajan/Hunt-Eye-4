from ai.planner import AStarPlanner
from control.mavlink_interface import PIDController
from core.safety import SafetyLayer
from core.shared_state import SharedState


def test_safety_caps_velocity_and_blocks_limits():
    safety = SafetyLayer(max_velocity=2.0, max_altitude=10.0, geofence_radius=50.0)

    vx, vy, vz, safe, reason = safety.enforce_command(5.0, -5.0, 3.0, 5.0, 10.0, "TRACKING")
    assert (vx, vy, vz) == (2.0, -2.0, 2.0)
    assert safe is True
    assert reason == "OK"

    vx, vy, vz, safe, reason = safety.enforce_command(1.0, 1.0, 1.0, 12.0, 10.0, "TRACKING")
    assert (vx, vy, vz) == (0.0, 0.0, 0.0)
    assert safe is False
    assert reason == "ALTITUDE_LIMIT"


def test_pid_and_planner_feed_shared_state():
    state = SharedState()
    pid = PIDController()
    planner = AStarPlanner()

    vx, vy = pid.calculate(800, 450, frame_cx=640, frame_cy=360)
    path = planner.find_path((0, 0), (19, 19))

    with state.lock:
        state.control_command = {"vx": vx, "vy": vy, "vz": 0.0}
        state.planned_path = [{"x": float(x), "y": float(y), "z": 0.0} for x, y in path]

    snapshot = state.snapshot()
    assert snapshot["control_command"]["vx"] > 0
    assert snapshot["planned_path"][0] == {"x": 0.0, "y": 0.0, "z": 0.0}
    assert snapshot["planned_path"][-1] == {"x": 19.0, "y": 19.0, "z": 0.0}


def test_planner_uses_runtime_cost_map_size():
    planner = AStarPlanner()
    planner.cost_map = planner.cost_map[:10, :10]

    path = planner.find_path((0, 0), (9, 9))

    assert path[0] == (0, 0)
    assert path[-1] == (9, 9)
