"""Single-instance enforcement built on QLocalServer/QLocalSocket.

The primary instance listens on a per-user, per-configuration local socket.
A second launch connects to that socket to ask the primary to surface its UI
and then exits, so the proxy listener port is never bound twice.  A socket
left behind by a crashed primary is removed before listening.
"""

from __future__ import annotations

import getpass
import hashlib
import logging
import os

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from pyproxyswitch.paths import USER_CONFIG_DIR

logger = logging.getLogger("PyProxySwitch")

_ACTIVATE_MESSAGE = b"activate"
_CONNECT_TIMEOUT_MS = 250


def _user_key() -> str:
    try:
        return str(os.getuid())
    except AttributeError:  # Windows
        return getpass.getuser()


def server_name() -> str:
    """Return the local-server name scoped to the user and configuration."""

    digest = hashlib.sha1(
        f"{_user_key()}:{USER_CONFIG_DIR}".encode("utf-8", "surrogateescape")
    ).hexdigest()[:12]
    return f"PyProxySwitch-{digest}"


class SingleInstanceGuard(QObject):
    """Elect one primary instance and relay activation requests to it."""

    activated = Signal()

    def __init__(self, parent: QObject | None = None, *, name: str | None = None) -> None:
        super().__init__(parent)
        self._name = name or server_name()
        self._server: QLocalServer | None = None

    @property
    def is_primary(self) -> bool:
        return self._server is not None

    def try_become_primary(self) -> bool:
        """Become the primary instance, or activate the existing one.

        Returns ``True`` when this process is the primary and must continue
        starting up; returns ``False`` when another instance was notified and
        this process should exit.
        """

        if self._notify_primary():
            return False
        server = QLocalServer(self)
        if not server.listen(self._name):
            # A crashed primary can leave a stale socket behind; remove it and
            # retry once before conceding to a concurrently starting instance.
            QLocalServer.removeServer(self._name)
            if not server.listen(self._name):
                logger.warning(
                    "Single-instance listen on %s failed: %s",
                    self._name,
                    server.errorString(),
                )
                server.close()
                return False
        server.newConnection.connect(self._on_new_connection)
        self._server = server
        return True

    def _notify_primary(self) -> bool:
        """Ask the running primary to activate; return whether one answered."""

        probe = QLocalSocket()
        probe.connectToServer(self._name)
        if not probe.waitForConnected(_CONNECT_TIMEOUT_MS):
            probe.abort()
            return False
        probe.write(_ACTIVATE_MESSAGE)
        probe.flush()
        probe.waitForBytesWritten(_CONNECT_TIMEOUT_MS)
        probe.disconnectFromServer()
        logger.info("Another instance is already running; asked it to activate")
        return True

    def _on_new_connection(self) -> None:
        """Surface the UI for every activation request from a second launch."""

        if self._server is None:
            return
        while self._server.hasPendingConnections():
            connection = self._server.nextPendingConnection()
            connection.disconnected.connect(connection.deleteLater)
            connection.disconnectFromServer()
            self.activated.emit()


__all__ = ["SingleInstanceGuard", "server_name"]
