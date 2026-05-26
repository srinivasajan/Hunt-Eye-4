# Core - SharedState
# Yeh sab devs ka common whiteboard hai
# Dev 1 likhta hai, Dev 2 likhta hai, Tu padhta hai

import threading
import numpy as np
from dataclasses import dataclass, field

@dataclass
class SharedState:
    lock: threading.RLock = field(default_factory=threading.RLock)
    
    # Dev 1 likhta hai - Tu padhta hai
    latest_frame: np.ndarray = None
    uav_position: np.ndarray = None
    
    # Dev 2 likhta hai - Tu padhta hai
    detections: list = field(default_factory=list)
    target_bbox: tuple = None
    active_target_id: int = -1
    cost_map: np.ndarray = None
    
    # Tu likhta hai - Dev 1 display karta hai
    planned_path: list = field(default_factory=list)
    system_mode: str = "idle"


# TEST
if __name__ == "__main__":
    print("=== SharedState Test ===")
    
    state = SharedState()
    
    # Dev 2 ne target detect kiya - simulate
    with state.lock:
        state.detections = [{"bbox": [100, 200, 300, 400], "confidence": 0.95}]
        state.target_bbox = (100, 200, 300, 400)
        state.active_target_id = 1
        state.system_mode = "hunting"
    
    # Tu read karta hai
    with state.lock:
        print(f"\nTarget mila: {state.detections}")
        print(f"Target bbox: {state.target_bbox}")
        print(f"System mode: {state.system_mode}")
    
    # Tu likhta hai
    with state.lock:
        state.planned_path = [(0,0), (1,1), (2,2), (3,3)]
        print(f"\nPath set kiya: {state.planned_path}")
    
    print("\nSharedState bilkul ready hai!")