"""Out-of-band interaction channel: a unix-socket line protocol.

`peerpet feed` (a separate process) connects to the running host's socket and
sends one JSON line; the host applies it and replies. This is what keeps the
shell unblocked — interaction never touches the host's stdin/stdout.

Protocol: newline-delimited JSON. Request {"command": "feed"}.
Response {"ok": true, "state": {...}} or {"ok": false, "error": "..."}.
"""

from __future__ import annotations

import json
import os
import socket
from collections.abc import Callable
from pathlib import Path


def socket_path() -> Path:
    """Per-user socket path under the runtime dir (falls back to /tmp)."""
    runtime = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    return Path(runtime) / f"peerpet-{os.getuid()}.sock"


# ---- client side (used by the CLI) ---------------------------------------


class HostNotRunning(Exception):
    pass


def send(command: str, payload: dict | None = None, timeout: float = 2.0) -> dict:
    """Send a command to the running host and return its reply dict."""
    path = socket_path()
    if not path.exists():
        raise HostNotRunning(f"no host socket at {path}; is `peerpet run` active?")
    msg = json.dumps({"command": command, "payload": payload or {}}) + "\n"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect(str(path))
        except (ConnectionRefusedError, FileNotFoundError) as e:
            raise HostNotRunning(str(e)) from e
        sock.sendall(msg.encode())
        data = b""
        while not data.endswith(b"\n"):
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
    return json.loads(data.decode() or "{}")


# ---- server side (used by the host) --------------------------------------


class IpcServer:
    """Minimal blocking unix-socket server.

    The host should run `serve_forever()` on a dedicated thread, or integrate
    the listening socket into its select loop. `handler(command, payload)`
    returns the reply dict.
    """

    def __init__(self, handler: Callable[[str, dict], dict]) -> None:
        self.handler = handler
        self.path = socket_path()
        self._sock: socket.socket | None = None

    def start(self) -> socket.socket:
        if self.path.exists():
            self.path.unlink()
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(str(self.path))
        self._sock.listen(8)
        return self._sock

    def handle_connection(self, conn: socket.socket) -> None:
        with conn:
            data = conn.recv(65536)
            if not data:
                return
            try:
                req = json.loads(data.decode())
                reply = self.handler(req.get("command", ""), req.get("payload", {}))
            except Exception as e:  # noqa: BLE001 — never let one client kill the host
                reply = {"ok": False, "error": str(e)}
            conn.sendall((json.dumps(reply) + "\n").encode())

    def serve_forever(self) -> None:
        sock = self._sock or self.start()
        try:
            while True:
                conn, _ = sock.accept()
                self.handle_connection(conn)
        finally:
            self.close()

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None
        if self.path.exists():
            self.path.unlink()
