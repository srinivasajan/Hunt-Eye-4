import time
import pytest
from core.watchdog import Watchdog
from core.shared_state import SharedState
from core.orchestrator import Orchestrator
from core.worker_base import WorkerBase

class FailingWorker(WorkerBase):
    def safe_run(self):
        while self.running:
            self.failed = True
            self.error = "Test error"
            self.sleep(0.1)

def test_watchdog():
    state = SharedState()
    orchestrator = Orchestrator()
    watchdog = Watchdog(orchestrator, state.event_bus, interval_seconds=0.1)
    
    worker = FailingWorker("fail_worker", restartable=True)
    orchestrator.add_worker(worker)
    orchestrator.start()
    
    watchdog.start()
    time.sleep(0.5)
    
    assert any(w.name == "fail_worker" and w.failed for w in orchestrator.workers)
    
    watchdog.stop()
    orchestrator.stop()
