import time
import pytest
from core.shared_state import SharedState
from core.worker_base import WorkerBase
from core.event_bus import EventBus
from core.watchdog import Watchdog
from core.orchestrator import Orchestrator

def test_shared_state():
    state = SharedState()
    assert state.latest_frame is None
    state.set_latest_frame("dummy_frame")
    assert state.get_latest_frame() == "dummy_frame"
    assert state.last_frame_time is not None
    
    state.update_worker_health("worker1", {"status": "ok"})
    assert state.worker_health["worker1"]["status"] == "ok"
    
    snapshot = state.snapshot()
    assert snapshot["has_frame"] is True
    assert "worker1" in snapshot["worker_health"]

def test_event_bus():
    bus = EventBus()
    events = []
    
    def handler(data):
        events.append(data)
        
    bus.subscribe("test_event", handler)
    bus.emit("test_event", {"key": "value"})
    
    assert len(events) == 1
    assert events[0]["key"] == "value"
    
    bus.unsubscribe("test_event", handler)
    bus.emit("test_event", {"key": "value2"})
    assert len(events) == 1  # Should not increase

class DummyWorker(WorkerBase):
    def safe_run(self):
        while self.running:
            self.heartbeat()
            self.sleep(0.1)

def test_worker_base():
    worker = DummyWorker("dummy")
    assert worker.name == "dummy"
    worker.start()
    time.sleep(0.2)
    assert worker.running is True
    assert worker.status()["alive"] is True
    worker.stop()
    time.sleep(0.2)
    assert worker.running is False
