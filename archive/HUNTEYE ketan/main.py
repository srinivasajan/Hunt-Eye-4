 # HUNT EYE - Main File
# Dev 3 ka sara kaam ek saath

import sys
sys.path.append('.')

from core.shared_state import SharedState
from core.safety import SafetyLayer
from ai.gym_env import HuntEyeEnv
from ai.planner import AStarPlanner
from control.mavlink_interface import PIDController

def main():
    print("=== HUNT EYE SYSTEM STARTING ===")
    
    # Sab modules initialize karo
    state = SharedState()
    safety = SafetyLayer()
    env = HuntEyeEnv()
    planner = AStarPlanner()
    pid = PIDController()
    
    print("✅ SharedState ready")
    print("✅ Safety Layer ready")
    print("✅ Gym Environment ready")
    print("✅ A* Planner ready")
    print("✅ PID Controller ready")
    
    # Simulate karo - target detect hua
    print("\n=== SIMULATION START ===")
    
    with state.lock:
        state.target_bbox = (800, 400, 900, 500)
        state.system_mode = "hunting"
    
    # PID se velocity nikalo
    target_cx = 850
    target_cy = 450
    vx, vy = pid.calculate(target_cx, target_cy)
    print(f"\nTarget at ({target_cx}, {target_cy})")
    print(f"PID → vx={vx:.4f}, vy={vy:.4f}")
    
    # Safety check karo
    print("\nSafety check...")
    is_safe = safety.is_safe(vx, vy, 0.0, 15.0, 50.0, state.system_mode)
    
    # A* path nikalo
    print("\nPath planning...")
    path = planner.find_path((0,0), (19,19))
    
    with state.lock:
        state.planned_path = path
    
    print(f"Path mila: {len(path)} steps")
    print(f"\n=== HUNT EYE READY TO FLY ===")

if __name__ == "__main__":
    main()
