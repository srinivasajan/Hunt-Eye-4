"""
Base class for Control workers in the HuntEye pipeline (Dev 3).

Defines the standard interface for workers that convert planned paths 
and target states into low-level drone flight commands.
"""

from typing import Any, Dict
from core.worker_base import WorkerBase
from core.logger import Logger

class ControlWorkerBase(WorkerBase):
    """
    Base class for Flight Control workers.
    
    Expected SharedState contract:
    - Reads: planned_path, telemetry, active_target
    - Outputs: Hardware commands via HAL (Hardware Abstraction Layer)
    """
    
    def __init__(self, name: str, state: Any, hal: Any, loop_interval: float = 0.05, restartable: bool = True):
        super().__init__(name=name, loop_interval=loop_interval, restartable=restartable)
        self.state = state
        self.hal = hal
        self.logger = Logger

    def compute_control_commands(self) -> Dict[str, float]:
        """
        Compute velocity/attitude commands based on current path and telemetry.
        MUST be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement compute_control_commands()")

    def apply_commands(self, commands: Dict[str, float]) -> None:
        """
        Send computed commands to the HAL.
        """
        # Example: self.hal.move_by_velocity_async(commands.get('vx', 0), ...)
        pass

    def safe_run(self) -> None:
        while self.running:
            start_time = self.state.profiler.measure(f"{self.name}_cycle") if hasattr(self.state, 'profiler') else None
            
            try:
                commands = self.compute_control_commands()
                if commands:
                    self.apply_commands(commands)
                
                self.heartbeat()
                
                if start_time is not None:
                    with start_time:
                        pass
                        
            except Exception as e:
                self.logger.error(f"Control error in {self.name}: {e}")
                self.failed = True
                self.error = str(e)
                self.sleep(1.0)
                
            self.sleep()
