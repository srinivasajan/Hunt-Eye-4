from __future__ import annotations
import threading
from typing import Any, Callable, Dict, List, Optional

from core.logger import Logger
from core.worker_base import WorkerBase


class Orchestrator:

    def __init__(self) -> None:

        self.workers: List[WorkerBase] = []

        self.worker_factories: Dict[str, Callable[[], WorkerBase]] = {}

        self.lock = threading.RLock()

    def add_worker(self, worker: WorkerBase, factory: Optional[Callable[[], WorkerBase]] = None) -> None:

        with self.lock:

            self.workers.append(worker)

            if factory is not None:

                self.worker_factories[worker.name] = factory

    def start(self) -> None:

        with self.lock:

            workers = list(self.workers)

        for worker in workers:

            if not worker.is_alive():

                Logger.info(f"Starting worker | name={worker.name}")

                worker.start()

    def stop(self, timeout: float = 3.0) -> None:

        with self.lock:

            workers = list(self.workers)

        for worker in workers:

            Logger.info(f"Stopping worker | name={worker.name}")

            worker.stop()

        for worker in workers:

            worker.join(timeout=timeout)

            if worker.is_alive():

                Logger.warning(f"Worker did not stop before timeout | name={worker.name}")

    def get_worker(self, name: str) -> Optional[WorkerBase]:

        with self.lock:

            for worker in self.workers:

                if worker.name == name:

                    return worker

        return None

    def status(self) -> List[Dict[str, Any]]:

        with self.lock:

            return [worker.status() for worker in self.workers]

    def restart_worker(self, name: str) -> bool:

        factory = self.worker_factories.get(name)

        if factory is None:

            Logger.warning(f"Worker restart skipped; no factory | name={name}")

            return False

        with self.lock:

            old_worker = self.get_worker(name)

            if old_worker is not None:

                old_worker.stop()

                old_worker.join(timeout=2.0)

                self.workers = [worker for worker in self.workers if worker.name != name]

            new_worker = factory()

            self.workers.append(new_worker)

        Logger.warning(f"Restarting worker | name={name}")

        new_worker.start()

        return True
