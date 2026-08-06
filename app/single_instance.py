from __future__ import annotations

import hashlib
import getpass
from collections.abc import Callable

from PySide6.QtNetwork import QLocalServer, QLocalSocket


def _default_server_name() -> str:
    """Keep one pet per Windows user without exposing the username in the pipe name."""
    user_fingerprint = hashlib.sha256(getpass.getuser().encode("utf-8")).hexdigest()[:16]
    return f"dafeiyu-pet-{user_fingerprint}"


class SingleInstance:
    """Prevent duplicate pets and wake the existing window on a repeated launch."""

    def __init__(self, server_name: str | None = None) -> None:
        self.server_name = server_name or _default_server_name()
        self._server = QLocalServer()
        self._activation_handler: Callable[[], None] | None = None
        self._activation_pending = False
        self._server.newConnection.connect(self._on_new_connection)

    def acquire(self) -> bool:
        """Return True only for the primary process."""
        if self._notify_existing():
            return False
        # A crashed process can leave a stale endpoint. It is safe to clear only
        # after a connection attempt proved that no peer is serving it.
        QLocalServer.removeServer(self.server_name)
        if self._server.listen(self.server_name):
            return True
        # Handle a short startup race: another process may have won the listener.
        if self._notify_existing():
            return False
        raise RuntimeError("无法创建桌宠的单实例通信通道。")

    def set_activation_handler(self, handler: Callable[[], None]) -> None:
        self._activation_handler = handler
        if self._activation_pending:
            self._activation_pending = False
            handler()

    def close(self) -> None:
        self._server.close()
        QLocalServer.removeServer(self.server_name)

    def _notify_existing(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self.server_name)
        if not socket.waitForConnected(250):
            return False
        socket.write(b"activate")
        socket.flush()
        socket.waitForBytesWritten(250)
        socket.disconnectFromServer()
        return True

    def _on_new_connection(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            socket.disconnected.connect(socket.deleteLater)
            # The connection itself is the activation signal. This avoids a
            # startup race where the tiny payload arrives before Qt dispatches
            # readyRead on the primary process.
            socket.readAll()
            socket.disconnectFromServer()
            if self._activation_handler is None:
                self._activation_pending = True
            else:
                self._activation_handler()
