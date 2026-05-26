"""
Base class for AI/Autonomy workers in the HuntEye pipeline (Dev 3).

Defines the standard interface for workers that perform high-level 
decision making, path planning, and autonomous behavior.
"""

from typing import Any, Dict, List, Optional
from core.worker_base import WorkerBase
from core.logger import Logger

class AIWorkerBase(WorkerBase):
    """
    Base class for AI and Autonomy workers.
    
    Expected SharedState contract:
    - Reads: telemetry, tracks, detections, mission, system_mode
    - Writes: planned_path, active_target_id, system_mode (transitions)
    """
    
    def __init__(self, name: str, state: Any, loop_interval: float = 0.1, restartable: bool = True):
        super().__init__(name=name, loop_interval=loop_interval, restartable=restartable)
        self.state = state
        self.logger = Logger

    def plan_path(self) -> List[Dict[str, float]]:
        """
        Generate a path based on current state.
        MUST be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement plan_path()")

    def decide_mode(self) -> Optional[str]:
        """
        Optionally decide if a system mode transition is required (e.g. IDLE -> TRACKING).
        """
        return None

    def safe_run(self) -> None:
        while self.running:
            start_time = self.state.profiler.measure(f"{self.name}_cycle") if hasattr(self.state, 'profiler') else None
            
            try:
                # Execute AI logic
                new_path = self.plan_path()
                new_mode = self.decide_mode()
                
                with self.state.lock:
                    if new_path is not None:
                        self.state.planned_path = new_path
                    if new_mode is not None:
                        self.state.system_mode = new_mode
                
                self.heartbeat()
                
                if start_time is not None:
                    with start_time:
                        pass
                        
            except Exception as e:
                self.logger.error(f"AI error in {self.name}: {e}")
                self.failed = True
                self.error = str(e)
                self.sleep(1.0)
                
            self.sleep()
