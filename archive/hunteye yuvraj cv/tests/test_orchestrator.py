import time
import pytest
from core.orchestrator import Orchestrator
from core.worker_base import WorkerBase

class DummyWorker(WorkerBase):
    def safe_run(self):
        while self.running:
            self.sleep(0.1)

def test_orchestrator():
    orchestrator = Orchestrator()
    worker = DummyWorker("test_worker")
    
    orchestrator.add_worker(worker)
    assert any(w.name == "test_worker" for w in orchestrator.workers)
    
    orchestrator.start()
    time.sleep(0.2)
    assert worker.running is True
    
    status_list = orchestrator.status()
    assert any(s["name"] == "test_worker" and s["alive"] is True for s in status_list)
    
    orchestrator.stop()
    time.sleep(0.2)
    assert worker.running is False
