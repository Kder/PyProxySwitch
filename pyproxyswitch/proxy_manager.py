#!/usr/bin/env python3

"""Lifecycle and hot-switching facade for the built-in proxy server."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from pyproxyswitch.errors import ConfigError, ProxyStartError
from pyproxyswitch.native_proxy import NativeProxyServer, Upstream

logger = logging.getLogger("PyProxySwitch")

if TYPE_CHECKING:
    from pyproxyswitch.config import ConfigManager


class ProxyManager:
    """Manage one native listener and atomically switch its upstream route.

    Switching a proxy only replaces an immutable :class:`Upstream` snapshot.
    The listening socket, event loop and existing TCP connections stay alive.
    The listener is restarted only when its bind address or port changes.
    """

    def __init__(self, config: ConfigManager | None = None) -> None:
        if config is None:
            from pyproxyswitch.config import ConfigManager

            config = ConfigManager()
        self._config = config
        self._server: NativeProxyServer | None = None
        self._lock = threading.RLock()

    @property
    def server(self) -> NativeProxyServer | None:
        """Return the native server instance for diagnostics."""
        return self._server

    @property
    def current_upstream(self) -> Upstream:
        if self._server is None:
            return Upstream.direct()
        return self._server.upstream

    def start_proxy(self, proxy_name: str) -> None:
        """Start the native listener or hot-switch newly accepted connections.

        Proxy details are read from the current proxy list.
        """
        try:
            upstream = self._resolve_upstream(proxy_name)
            host, port = self._listener_address()
            with self._lock:
                if (
                    self._server is not None
                    and self._server.is_running
                    and self._server.host == host
                    and self._server.port == port
                ):
                    self._server.set_upstream(upstream)
                    return
                self._replace_listener(
                    host,
                    port,
                    upstream,
                    timeout=5,
                    user_message="Failed to reconfigure proxy service",
                )
        except (ConfigError, ProxyStartError):
            raise
        except (OSError, RuntimeError, TimeoutError, TypeError, ValueError) as exc:
            logger.error("Failed to start native proxy: %s", exc)
            raise ProxyStartError("Failed to start proxy service", str(exc)) from exc

    def restart_listener(self, timeout: int = 5) -> None:
        """Apply a changed local bind address/port while preserving the route."""
        with self._lock:
            upstream = self.current_upstream
            host, port = self._listener_address()
            self._replace_listener(
                host,
                port,
                upstream,
                timeout=timeout,
                user_message="Failed to restart proxy service",
            )

    def stop_proxy(self, timeout: int = 5) -> bool:
        """Stop the in-process proxy server."""
        with self._lock:
            if self._server is None:
                return True
            stopped = self._server.stop(timeout=timeout)
            if stopped:
                self._server = None
            else:
                logger.error("Native proxy did not stop within %s seconds", timeout)
            return stopped

    def _listener_address(self) -> tuple[str, int]:
        host = str(self._config.get("LOCAL_ADDRESS", "127.0.0.1")).strip()
        if not host:
            raise ConfigError("Invalid local address", "LOCAL_ADDRESS cannot be empty")
        try:
            port = int(self._config.get("LOCAL_PORT", 8888))
        except (TypeError, ValueError):
            raise ConfigError("Invalid local port", "LOCAL_PORT must be an integer") from None
        if not 1 <= port <= 65535:
            raise ConfigError(
                f"Invalid local port: {port}", "LOCAL_PORT must be between 1 and 65535"
            )
        return host, port

    def _replace_listener(
        self,
        host: str,
        port: int,
        upstream: Upstream,
        *,
        timeout: int,
        user_message: str,
    ) -> None:
        """Replace a listener and restore its old address when the new bind fails."""

        old_server = self._server
        old_address = (
            (old_server.host, old_server.port)
            if old_server is not None and old_server.is_running
            else None
        )
        old_upstream = (
            old_server.upstream
            if old_server is not None and old_address is not None
            else upstream
        )

        if old_server is not None:
            if not old_server.stop(timeout=timeout):
                raise ProxyStartError(user_message, "Native listener did not stop in time")
            self._server = None

        server: NativeProxyServer | None = None
        try:
            server = self._create_server(host, port, upstream)
            server.start(timeout=timeout)
            self._server = server
            return
        except (OSError, OverflowError, RuntimeError, TimeoutError, TypeError, ValueError) as exc:
            if server is not None:
                try:
                    server.stop(timeout=timeout)
                except Exception:
                    logger.debug("Failed to clean up a partially started listener", exc_info=True)

            if old_address is not None:
                try:
                    fallback = self._create_server(old_address[0], old_address[1], old_upstream)
                    fallback.start(timeout=timeout)
                    self._server = fallback
                except Exception:
                    logger.exception("Failed to restore the previous listener")
            raise ProxyStartError(user_message, str(exc)) from exc

    def _create_server(self, host: str, port: int, upstream: Upstream) -> NativeProxyServer:
        return NativeProxyServer(
            host=host,
            port=port,
            upstream=upstream,
            connect_timeout=float(self._config.get("CONNECT_TIMEOUT", 15)),
        )

    def _resolve_upstream(self, proxy_name: str) -> Upstream:
        if not isinstance(proxy_name, str) or not proxy_name:
            raise ConfigError("Invalid proxy name", "Proxy name must be a non-empty string")
        if proxy_name == "NoProxy":
            return Upstream.direct()

        selected = next(
            (proxy for proxy in self._config.get_proxies() if proxy[0] == proxy_name), None
        )
        if selected is None:
            raise ConfigError(
                f"Proxy not found: {proxy_name}",
                f"No proxy named {proxy_name!r} exists in the configured proxy list",
            )
        name, host, port, kind, username, password = selected

        try:
            port_number = int(port)
            return Upstream(
                name=str(name),
                proxy_type=str(kind).upper(),
                host=str(host),
                port=port_number,
                username=str(username),
                password=str(password),
            )
        except (TypeError, ValueError) as exc:
            raise ConfigError(
                f"Invalid proxy configuration: {proxy_name}",
                f"Invalid configuration for {proxy_name!r}: {exc}",
            ) from exc


__all__ = ["ProxyManager"]
