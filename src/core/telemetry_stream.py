"""Distributed telemetry streaming (Dev 1.1).

This is a simple NDJSON-over-TCP stream.

- Client connects
- Optionally sends one line JSON: {"token": "..."}
- Server sends one JSON line per interval with a subset of SharedState snapshot

This is intended for remote monitoring / observability.
"""

from __future__ import annotations

import json
import socketserver
import threading
import time
from typing import Any

from core.json_utils import json_safe
from core.logger import Logger
from core.worker_base import WorkerBase


class _ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


class TelemetryStreamServerWorker(WorkerBase):
    def __init__(
        self,
        state: Any,
        host: str = "127.0.0.1",
        port: int = 8787,
        interval_seconds: float = 0.5,
        token: str | None = None,
        name: str = "TelemetryStream",
        restartable: bool = True,
    ):
        super().__init__(name=name, loop_interval=0.0, restartable=restartable)
        self.state = state
        self.host = host
        self.port = int(port)
        self.interval_seconds = float(interval_seconds)
        self.token = token

        self._server: _ThreadingTCPServer | None = None

    def stop(self):
        super().stop()
        if self._server is not None:
            try:
                self._server.shutdown()
            except Exception:
                pass
            try:
                self._server.server_close()
            except Exception:
                pass

    def safe_run(self) -> None:
        handler_cls = _make_handler(state=self.state, token=self.token, interval_seconds=self.interval_seconds)
        self._server = _ThreadingTCPServer((self.host, self.port), handler_cls)
        Logger.info(f"Telemetry stream listening | host={self.host} | port={self.port}")
        try:
            self._server.serve_forever(poll_interval=0.2)
        finally:
            try:
                self._server.server_close()
            except Exception:
                pass


def _make_handler(*, state: Any, token: str | None, interval_seconds: float):
    class Handler(socketserver.StreamRequestHandler):
        def handle(self) -> None:
            # Optional auth line
            if token is not None:
                raw = self.rfile.readline()
                if not raw:
                    return
                try:
                    msg = json.loads(raw.decode("utf-8", errors="replace"))
                except Exception:
                    return
                if msg.get("token") != token:
                    return

            last_sent = 0.0
            while True:
                now = time.time()
                if now - last_sent < interval_seconds:
                    time.sleep(min(0.05, interval_seconds))
                    continue

                snapshot = state.snapshot() if hasattr(state, "snapshot") else {}

                payload = {
                    "ts": now,
                    "system_mode": snapshot.get("system_mode"),
                    "has_frame": snapshot.get("has_frame"),
                    "telemetry": snapshot.get("telemetry", {}),
                    "worker_health": snapshot.get("worker_health", {}),
                    "latency": snapshot.get("latency", {}),
                }

                line = (json.dumps(json_safe(payload), separators=(",", ":"), default=str) + "\n").encode("utf-8")
                try:
                    self.wfile.write(line)
                    self.wfile.flush()
                    last_sent = now
                except Exception:
                    return

    return Handler
