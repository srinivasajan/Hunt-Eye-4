import threading
import time
import traceback
from typing import Any, Dict, Optional

from core.logger import Logger


class WorkerBase(threading.Thread):

    def __init__(self, name: str, loop_interval: float = 0.0, restartable: bool = True, isolation_zone: Optional[str] = None) -> None:

        super().__init__(name=name, daemon=True)

        self.loop_interval = loop_interval

        self.restartable = restartable

        self.isolation_zone = isolation_zone

        self._stop_event = threading.Event()

        self.last_update: float = time.time()

        self.failed: bool = False

        self.error: Optional[str] = None

        self.error_type: Optional[str] = None

        self.error_traceback: Optional[str] = None

        self.started_at: Optional[float] = None

        self.stopped_at: Optional[float] = None

    @property
    def running(self) -> bool:

        return not self._stop_event.is_set()

    def heartbeat(self) -> None:

        self.last_update = time.time()

    def sleep(self, seconds: Optional[float] = None) -> None:

        interval = self.loop_interval if seconds is None else seconds

        if interval > 0:
            self._stop_event.wait(interval)

    def safe_run(self) -> None:

        raise NotImplementedError

    def run(self) -> None:

        self.started_at = time.time()

        self.heartbeat()

        Logger.info(f"Worker started | name={self.name}")

        try:

            self.safe_run()

        except Exception as e:

            self.failed = True

            self.error = str(e)

            self.error_type = type(e).__name__

            self.error_traceback = traceback.format_exc()

            Logger.error(f"Worker crashed | name={self.name} | error={e}")

            # Keep printing for local debugging while also retaining structured traceback.
            traceback.print_exc()

        finally:

            self.stopped_at = time.time()

            Logger.info(f"Worker stopped | name={self.name}")

    def stop(self) -> None:

        self._stop_event.set()

    def status(self) -> Dict[str, Any]:

        now = time.time()

        return {
            "name": self.name,
            "alive": self.is_alive(),
            "failed": self.failed,
            "error": self.error,
            "error_type": self.error_type,
            "error_traceback": self.error_traceback,
            "restartable": self.restartable,
            "isolation_zone": self.isolation_zone,
            "last_update_age": now - self.last_update,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
        }
