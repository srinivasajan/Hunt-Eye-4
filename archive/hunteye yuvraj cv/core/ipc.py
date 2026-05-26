"""Inter-process communication (IPC) for HuntEye.

Goal: enable basic cross-process control/telemetry without external deps.

Protocol:
- TCP, newline-delimited JSON (NDJSON)
- Each request is one JSON object on a line.
- Each response is one JSON object on a line.

Request schema:
{
  "token": "...",   # optional; required if server configured with a token
  "type": "ping" | "get_snapshot" | "get_status" | "emit_event" | "set_mode",
  ...
}
"""

from __future__ import annotations

import json
import socket
import socketserver
import threading
from typing import Any, Optional

from core.json_utils import json_safe
from core.logger import Logger
from core.worker_base import WorkerBase


class IPCError(Exception):
    pass


class _ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


class IPCServerWorker(WorkerBase):
    """A WorkerBase wrapper around a small NDJSON-over-TCP control server."""

    def __init__(
        self,
        state: Any,
        host: str = "127.0.0.1",
        port: int = 8765,
        token: str | None = None,
        orchestrator: Any | None = None,
        name: str = "IPCServer",
        loop_interval: float = 0.0,
        restartable: bool = True,
    ):
        super().__init__(name=name, loop_interval=loop_interval, restartable=restartable)
        self.state = state
        self.host = host
        self.port = int(port)
        self.token = token
        self.orchestrator = orchestrator

        self._server: _ThreadingTCPServer | None = None
        self._server_thread: threading.Thread | None = None

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
        handler_cls = _make_handler(
            state=self.state,
            token=self.token,
            orchestrator=self.orchestrator,
        )

        self._server = _ThreadingTCPServer((self.host, self.port), handler_cls)
        Logger.info(f"IPC server listening | host={self.host} | port={self.port}")

        # serve_forever blocks, but shutdown() will interrupt.
        try:
            self._server.serve_forever(poll_interval=0.2)
        finally:
            try:
                self._server.server_close()
            except Exception:
                pass


def _make_handler(*, state: Any, token: str | None, orchestrator: Any | None):
    class Handler(socketserver.StreamRequestHandler):
        def _send(self, obj: dict[str, Any]) -> None:
            data = (json.dumps(obj, separators=(",", ":"), default=str) + "\n").encode("utf-8")
            self.wfile.write(data)
            self.wfile.flush()

        def handle(self) -> None:
            while True:
                raw = self.rfile.readline()
                if not raw:
                    return

                try:
                    msg = json.loads(raw.decode("utf-8", errors="replace"))
                except Exception:
                    self._send({"ok": False, "error": "invalid_json"})
                    continue

                try:
                    resp = _process_message(
                        msg=msg,
                        state=state,
                        token=token,
                        orchestrator=orchestrator,
                    )
                except IPCError as e:
                    self._send({"ok": False, "error": str(e)})
                    continue
                except Exception as e:
                    Logger.error(f"IPC handler error | error={e}")
                    self._send({"ok": False, "error": "server_error"})
                    continue

                self._send(resp)

    return Handler


def _process_message(*, msg: dict[str, Any], state: Any, token: str | None, orchestrator: Any | None) -> dict[str, Any]:
    if token is not None:
        if msg.get("token") != token:
            raise IPCError("unauthorized")

    msg_type = msg.get("type")

    if msg_type == "ping":
        return {"ok": True, "type": "pong"}

    if msg_type == "get_snapshot":
        snapshot = state.snapshot() if hasattr(state, "snapshot") else {}
        return {"ok": True, "snapshot": json_safe(snapshot)}

    if msg_type == "get_status":
        if orchestrator is None or not hasattr(orchestrator, "status"):
            return {"ok": False, "error": "orchestrator_unavailable"}
        return {"ok": True, "status": orchestrator.status()}

    if msg_type == "emit_event":
        event_name = msg.get("event")
        data = msg.get("data")
        if not event_name:
            raise IPCError("missing_event")
        state.event_bus.emit(event_name, data)
        return {"ok": True}

    if msg_type == "set_mode":
        mode = msg.get("mode")
        if not mode:
            raise IPCError("missing_mode")
        with state.lock:
            state.system_mode = str(mode).upper()
        return {"ok": True, "system_mode": state.system_mode}

    raise IPCError("unknown_type")


class IPCClient:
    """Small blocking client for IPCServerWorker."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        token: str | None = None,
        timeout_seconds: float = 2.0,
    ):
        self.host = host
        self.port = int(port)
        self.token = token
        self.timeout_seconds = float(timeout_seconds)

    def request(self, msg: dict[str, Any]) -> dict[str, Any]:
        if self.token is not None:
            msg = {**msg, "token": self.token}

        payload = (json.dumps(msg, separators=(",", ":")) + "\n").encode("utf-8")

        with socket.create_connection((self.host, self.port), timeout=self.timeout_seconds) as sock:
            sock.settimeout(self.timeout_seconds)
            sock.sendall(payload)

            buffer = b""
            while b"\n" not in buffer:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buffer += chunk

        if not buffer:
            raise IPCError("no_response")

        line = buffer.split(b"\n", 1)[0]
        return json.loads(line.decode("utf-8", errors="replace"))

    def ping(self) -> bool:
        return bool(self.request({"type": "ping"}).get("ok"))

    def get_snapshot(self) -> dict[str, Any]:
        resp = self.request({"type": "get_snapshot"})
        if not resp.get("ok"):
            raise IPCError(resp.get("error", "error"))
        return resp.get("snapshot", {})
