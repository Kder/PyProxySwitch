#!/usr/bin/env python3

"""High-performance, standard-library-only local proxy server.

The listener accepts HTTP proxy, SOCKS4/SOCKS4a and SOCKS5 clients on the same
TCP port.  Each accepted connection takes an immutable snapshot of the current
upstream, so changing the upstream is atomic and does not restart the listener
or interrupt connections that are already transferring data.

Design invariants
-----------------
* One request per plain-HTTP client connection.  Nothing is pooled, so a
  smuggled request can never be paired with another user's connection.
* Whoever opens a writer closes it.  ``_relay*`` helpers close nothing.
* Every read is bounded: setup by ``handshake_timeout``/``connect_timeout``,
  streaming by a connection-wide ``idle_timeout`` watchdog that either
  direction can refresh.
* Nothing synthetic is ever written to a client after an upstream byte has
  started a final response (``_ResponseProgress``).

Requires Python 3.11+: ``asyncio.TimeoutError is TimeoutError`` and
``asyncio.timeout()`` are both load-bearing.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import errno
import ipaddress
import logging
import math
import socket
import string
import struct
import sys
import threading
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Final, Literal, TypeVar
from urllib.parse import SplitResult, urlsplit, urlunsplit

logger = logging.getLogger("PyProxySwitch")

_BUFFER_SIZE: Final = 64 * 1024
_HEADER_LIMIT: Final = 64 * 1024
_WRITE_HIGH_WATER: Final = 512 * 1024
_WRITE_LOW_WATER: Final = 128 * 1024
_WRITER_FLUSH_TIMEOUT: Final = 10.0
_WRITER_CLOSE_TIMEOUT: Final = 10.0
_SHUTDOWN_CLOSE_TIMEOUT: Final = 0.25
_SERVER_CLOSE_TIMEOUT: Final = 0.5
_MAX_HTTP_BODY_LENGTH: Final = (1 << 63) - 1
_MAX_CONTENT_LENGTH_DIGITS: Final = 19
_MAX_CHUNK_SIZE_DIGITS: Final = 16
_MAX_INTERIM_RESPONSES: Final = 8
_MAX_HOST_LENGTH: Final = 255
_MAX_SOCKS_FIELD_LENGTH: Final = 255
_DEFAULT_IDLE_TIMEOUT: Final = 300.0
_DEFAULT_MAX_CONNECTIONS: Final = 512
_WINDOWS_SELECTOR_MAX_CONNECTIONS: Final = 200

_SUPPORTED_TYPES = frozenset({"DIRECT", "HTTP", "SOCKS4", "SOCKS5"})
_HTTP_VERSIONS = frozenset({"HTTP/1.0", "HTTP/1.1"})
_HTTP_TOKEN_CHARS = frozenset(
    "!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)
_HTTP_HEX_CHARS = frozenset("0123456789ABCDEFabcdef")
_HOST_LABEL_CHARS = frozenset(string.ascii_letters + string.digits + "-_")
_FORBIDDEN_TRAILER_FIELDS = frozenset(
    {
        "connection",
        "content-length",
        "host",
        "proxy-connection",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)
# Hop-by-hop fields never survive a forwarding hop.  ``te`` is included: this
# proxy forwards message bodies verbatim and negotiates no transfer coding.
_HOP_BY_HOP_FIELDS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "proxy-connection",
        "te",
        "upgrade",
    }
)
# Framing/routing fields stay end-to-end even when a hostile ``Connection``
# option names them.  The ``Connection`` field itself is always replaced.
_END_TO_END_FIELDS = frozenset({"content-length", "host", "trailer", "transfer-encoding"})
_SOCKS5_ERRNO_REPLIES: Final = {
    errno.ECONNREFUSED: 5,
    errno.ENETUNREACH: 3,
    errno.ENETDOWN: 3,
    errno.EHOSTUNREACH: 4,
    errno.EHOSTDOWN: 4,
}

_Headers = tuple[tuple[str, str], ...]
_BodyMode = Literal["none", "content-length", "chunked", "eof"]
_TargetForm = Literal["origin", "absolute", "authority", "asterisk"]
DestinationPolicy = Callable[[str, int], bool]
_T = TypeVar("_T")


class ProxyProtocolError(Exception):
    """A client or upstream proxy sent an invalid/unsupported message."""


class ClientProtocolError(ProxyProtocolError):
    """The local client is at fault (mapped to HTTP 400)."""


class UpstreamProtocolError(ProxyProtocolError):
    """The upstream proxy or origin is at fault (mapped to HTTP 502)."""


class _ClientTimeoutError(ClientProtocolError):
    """The client stopped making progress (mapped to HTTP 408)."""


class _UpstreamTimeoutError(UpstreamProtocolError):
    """The upstream stopped making progress (mapped to HTTP 504)."""


class ProxyPolicyError(ProxyProtocolError):
    """The destination was rejected by policy (HTTP 403 / SOCKS5 reply 2)."""


class _Socks5RequestError(ProxyProtocolError):
    """A SOCKS5 request that has a specific reply code."""

    def __init__(self, message: str, reply: int) -> None:
        super().__init__(message)
        self.reply = reply


def _ip_literal(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None


def _validate_destination_host(host: str) -> str:
    """Validate an opaque ASCII destination host (IP literal or DNS name).

    Names are never transcoded: whatever the client asked for is what the next
    hop receives.  IDNs must arrive as A-labels, which is what every client
    that is not itself broken already sends.
    """

    if not host:
        raise ProxyProtocolError("Destination host cannot be empty")
    if len(host) > _MAX_HOST_LENGTH:
        raise ProxyProtocolError("Destination host is too long")
    if not host.isascii():
        raise ProxyProtocolError("Destination host must be ASCII (use IDNA A-labels)")
    if _ip_literal(host) is not None:
        return host
    name = host[:-1] if host.endswith(".") else host
    if not name:
        raise ProxyProtocolError("Destination host cannot be empty")
    for label in name.split("."):
        if not 1 <= len(label) <= 63 or not set(label) <= _HOST_LABEL_CHARS:
            raise ProxyProtocolError(f"Invalid destination host: {host!r}")
    return host


def _decode_host_name(raw: bytes) -> str:
    try:
        host = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ProxyProtocolError("Destination host is not ASCII") from exc
    return _validate_destination_host(host)


@dataclass(frozen=True, slots=True)
class _HttpBodyFraming:
    """Validated framing for one non-tunnel HTTP message body."""

    mode: _BodyMode
    content_length: int = 0

    @property
    def has_body(self) -> bool:
        return self.mode in {"chunked", "eof"} or (
            self.mode == "content-length" and self.content_length > 0
        )


@dataclass(frozen=True, slots=True)
class _HttpTarget:
    """Where a request goes and how the request-target is rendered."""

    host: str
    port: int
    origin_form: str = ""
    proxy_form: str = ""


@dataclass(frozen=True, slots=True)
class _BoundAddress:
    """Address a proxy used for its target-side connection."""

    host: str
    port: int


@dataclass(frozen=True, slots=True)
class _HttpRequest:
    """A fully validated client request head."""

    method: str
    target: str
    version: str
    target_form: _TargetForm
    headers: _Headers
    framing: _HttpBodyFraming
    is_upgrade: bool
    upgrade_protocols: tuple[str, ...]
    destination: _HttpTarget


@dataclass(slots=True)
class _ResponseProgress:
    """Tracks whether a final response has started reaching the client.

    Informational responses do not set this flag: HTTP permits a final response
    after them.  Once a 101 or non-1xx head starts, no synthetic status line may
    be written because that would append a second final response.
    """

    final_started: bool = False


class _ConnectionActivity:
    """One inactivity deadline shared by every streaming task on a connection."""

    __slots__ = ("_deadline", "_loop", "_timeout", "_watchdogs")

    def __init__(self, timeout: float | None) -> None:
        self._timeout = timeout
        self._loop = asyncio.get_running_loop()
        self._deadline = None if timeout is None else self._loop.time() + timeout
        self._watchdogs: set[asyncio.Timeout] = set()

    def touch(self) -> None:
        """Refresh every pending I/O wait after actual connection progress."""

        if self._timeout is None:
            return
        deadline = self._loop.time() + self._timeout
        self._deadline = deadline
        for watchdog in tuple(self._watchdogs):
            if not watchdog.expired():
                watchdog.reschedule(deadline)

    async def wait(self, awaitable: Awaitable[_T]) -> _T:
        """Bound one I/O operation by the shared, refreshable deadline."""

        if self._deadline is None:
            return await awaitable
        watchdog = asyncio.timeout_at(self._deadline)
        self._watchdogs.add(watchdog)
        try:
            async with watchdog:
                return await awaitable
        finally:
            self._watchdogs.discard(watchdog)


@dataclass(frozen=True, slots=True)
class Upstream:
    """Immutable routing target used by a client connection."""

    name: str
    proxy_type: str = "DIRECT"
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""

    def __post_init__(self) -> None:
        proxy_type = self.proxy_type.upper()
        object.__setattr__(self, "proxy_type", proxy_type)
        if proxy_type not in _SUPPORTED_TYPES:
            raise ValueError(f"Unsupported upstream proxy type: {self.proxy_type}")
        for label in ("username", "password"):
            value = getattr(self, label)
            if not isinstance(value, str):
                raise ValueError(f"Upstream {label} must be a string")
            if any(ord(char) < 32 or ord(char) == 127 for char in value):
                raise ValueError(f"Upstream {label} cannot contain control characters")
            try:
                encoded = value.encode("utf-8")
            except UnicodeEncodeError:
                raise ValueError(f"Upstream {label} is not encodable as UTF-8") from None
            if proxy_type == "SOCKS5" and len(encoded) > _MAX_SOCKS_FIELD_LENGTH:
                raise ValueError(
                    f"Upstream {label} cannot exceed {_MAX_SOCKS_FIELD_LENGTH} UTF-8 bytes"
                )
        if proxy_type == "DIRECT":
            object.__setattr__(self, "host", "")
            object.__setattr__(self, "port", 0)
            return
        if proxy_type == "SOCKS4" and self.password:
            raise ValueError("SOCKS4 supports a User ID but does not support passwords")
        if not self.host:
            raise ValueError("Upstream proxy address cannot be empty")
        try:
            _validate_destination_host(self.host)
        except ProxyProtocolError as exc:
            raise ValueError(f"Invalid upstream proxy address: {exc}") from None
        port = _coerce_port(self.port, "Upstream proxy port")
        if not 1 <= port <= 65535:
            raise ValueError(f"Invalid upstream proxy port: {self.port}")
        object.__setattr__(self, "port", port)
        if (
            proxy_type == "SOCKS5"
            and (self.username or self.password)
            and (not self.username or not self.password)
        ):
            raise ValueError("SOCKS5 authentication requires both username and password")

    @classmethod
    def direct(cls) -> Upstream:
        return cls(name="NoProxy")

    @property
    def description(self) -> str:
        if self.proxy_type == "DIRECT":
            return "NoProxy (direct)"
        return f"{self.name} ({self.proxy_type} {self.host}:{self.port})"


def _coerce_port(value: object, description: str) -> int:
    """Accept an ``int`` or a plain decimal string; never truncate silently."""

    if isinstance(value, bool):
        raise ValueError(f"{description} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.isascii() and text.isdecimal():
            return int(text)
    raise ValueError(f"{description} must be an integer")


def _uses_windows_selector_event_loop() -> bool:
    return sys.platform == "win32" and sys.version_info[:2] == (3, 14)


class NativeProxyServer:
    """A mixed HTTP/SOCKS local proxy running on a background asyncio loop."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8888,
        upstream: Upstream | None = None,
        *,
        connect_timeout: float = 15.0,
        handshake_timeout: float = 15.0,
        idle_timeout: float | None = _DEFAULT_IDLE_TIMEOUT,
        max_connections: int = _DEFAULT_MAX_CONNECTIONS,
        allow_remote_clients: bool = False,
        destination_policy: DestinationPolicy | None = None,
    ) -> None:
        bound_port = _coerce_port(port, "Local proxy port")
        if not 0 <= bound_port <= 65535:
            raise ValueError(f"Invalid local proxy port: {port}")
        if not allow_remote_clients and not self._is_loopback_host(host):
            raise ValueError(
                f"Refusing to bind {host!r}: this proxy has no client authentication, so a "
                "non-loopback bind is an open relay.  Pass allow_remote_clients=True to "
                "override once you have an external control (firewall, netns, ...)."
            )
        if allow_remote_clients and not self._is_loopback_host(host):
            logger.warning(
                "Native proxy will accept unauthenticated clients on %s - it is an open relay",
                host,
            )
        self.host = host
        self.port = bound_port
        self.connect_timeout = self._positive_timeout("connect_timeout", connect_timeout)
        self.handshake_timeout = self._positive_timeout("handshake_timeout", handshake_timeout)
        self.idle_timeout = (
            None if idle_timeout is None else self._positive_timeout("idle_timeout", idle_timeout)
        )
        if not isinstance(max_connections, int) or isinstance(max_connections, bool):
            raise ValueError("max_connections must be an integer")
        if max_connections < 1:
            raise ValueError("max_connections must be at least 1")
        if (
            _uses_windows_selector_event_loop()
            and max_connections > _WINDOWS_SELECTOR_MAX_CONNECTIONS
        ):
            logger.warning(
                "Capping max_connections from %d to %d because Windows Python 3.14 "
                "SelectorEventLoop can monitor at most 512 sockets",
                max_connections,
                _WINDOWS_SELECTOR_MAX_CONNECTIONS,
            )
            max_connections = _WINDOWS_SELECTOR_MAX_CONNECTIONS
        self.max_connections = max_connections
        if destination_policy is not None and not callable(destination_policy):
            raise TypeError("destination_policy must be callable")
        # Called as policy(host, port) for every client-requested destination.
        # It must be pure: it can be consulted more than once per connection and
        # it never resolves names, so it is a coarse filter, not an SSRF cure.
        self.destination_policy = destination_policy
        self._upstream = upstream or Upstream.direct()

        self._state_lock = threading.RLock()
        # Lifecycle transitions include waiting for bind/join, so the state
        # lock alone cannot prevent a new generation from starting while an
        # older stop() is still cleaning up its handles.
        self._lifecycle_lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server: asyncio.AbstractServer | None = None
        self._stop_event: asyncio.Event | None = None
        self._stop_requested = threading.Event()
        self._ready = threading.Event()
        self._startup_error: BaseException | None = None
        self._loop_error: BaseException | None = None
        self._bound_port = 0
        self._shutting_down = False
        self._client_tasks: set[asyncio.Task[None]] = set()

    # ------------------------------------------------------------------ state

    @property
    def upstream(self) -> Upstream:
        with self._state_lock:
            return self._upstream

    @property
    def bound_port(self) -> int:
        with self._state_lock:
            return self._bound_port

    @property
    def active_connections(self) -> int:
        """Approximate in-flight client handler count (mutated on the loop)."""
        return len(self._client_tasks)

    @property
    def is_running(self) -> bool:
        with self._state_lock:
            return (
                self._thread is not None
                and self._thread.is_alive()
                and self._ready.is_set()
                and self._startup_error is None
                and self._loop_error is None
                and self._bound_port != 0
            )

    def set_upstream(self, upstream: Upstream) -> None:
        """Atomically route newly accepted connections through *upstream*."""
        if not isinstance(upstream, Upstream):
            raise TypeError("upstream must be an Upstream instance")
        with self._state_lock:
            self._upstream = upstream
        logger.info("Native proxy switched to %s", upstream.description)

    # -------------------------------------------------------------- lifecycle

    def start(self, timeout: float = 5.0) -> None:
        """Start the listener and wait until binding has completed."""
        with self._lifecycle_lock:
            with self._state_lock:
                if self.is_running:
                    return
                if self._thread is not None and self._thread.is_alive():
                    raise RuntimeError("Native proxy is still starting or stopping")
                self._ready = threading.Event()
                self._startup_error = None
                self._loop_error = None
                self._bound_port = 0
                self._shutting_down = False
                self._stop_requested.clear()
                thread = threading.Thread(
                    target=self._thread_main,
                    name="PyProxySwitch-native-proxy",
                    daemon=True,
                )
                self._thread = thread
                thread.start()

            if not self._ready.wait(timeout):
                self.stop(timeout=timeout)
                raise TimeoutError("Timed out while starting the native proxy")
            startup_error, running = self._startup_state()
            if startup_error is not None:
                self.stop(timeout=timeout)
                raise RuntimeError(f"Cannot start native proxy: {startup_error}") from startup_error
            if not running:
                self.stop(timeout=timeout)
                raise RuntimeError("Native proxy stopped before it finished starting")
            logger.info("Native proxy listening on %s:%s", self.host, self.bound_port)

    def stop(self, timeout: float = 5.0) -> bool:
        """Stop accepting clients, close active connections and join the loop."""
        with self._lifecycle_lock:
            # Set before reading the loop handles: this closes the race where
            # stop() runs before the event loop publishes its asyncio.Event.
            self._stop_requested.set()
            with self._state_lock:
                thread = self._thread
                loop = self._loop
                stop_event = self._stop_event
            if thread is None:
                return True
            if loop is not None and stop_event is not None and not loop.is_closed():
                with contextlib.suppress(RuntimeError):
                    loop.call_soon_threadsafe(stop_event.set)
            thread.join(max(0.0, timeout))
            stopped = not thread.is_alive()
            if stopped:
                with self._state_lock:
                    # Never let an old generation clear handles published by a
                    # newer one, even if lifecycle locking changes later.
                    if self._thread is thread:
                        self._thread = None
                        self._loop = None
                        self._server = None
                        self._stop_event = None
                        self._bound_port = 0
                logger.info("Native proxy stopped")
            return stopped

    def _thread_main(self) -> None:
        try:
            if _uses_windows_selector_event_loop():
                # Avoid CPython 3.14 Proactor cleanup races on Windows.
                with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
                    runner.run(self._run_server())
            else:
                asyncio.run(self._run_server())
        except BaseException as exc:
            with self._state_lock:
                if self._ready.is_set() and self._startup_error is None:
                    self._loop_error = exc
                else:
                    self._startup_error = exc
            logger.exception("Native proxy event loop failed")
        finally:
            self._ready.set()

    async def _run_server(self) -> None:
        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()
        with self._state_lock:
            self._loop = loop
            self._stop_event = stop_event
        if self._stop_requested.is_set():
            return
        server: asyncio.AbstractServer | None = None
        try:
            server = await asyncio.start_server(
                self._handle_client,
                self.host,
                self.port,
                backlog=512,
                limit=_HEADER_LIMIT,
                start_serving=True,
            )
            sockets = server.sockets or ()
            if not sockets:
                raise RuntimeError("Listener did not expose a bound socket")
            with self._state_lock:
                self._server = server
                self._bound_port = int(sockets[0].getsockname()[1])
            self._ready.set()
            if self._stop_requested.is_set():
                return
            await stop_event.wait()
        except BaseException as exc:
            if not self._ready.is_set():
                with self._state_lock:
                    self._startup_error = exc
                self._ready.set()
            else:
                raise
        finally:
            # Shorten every close budget: handlers are about to be cancelled and
            # nothing may block the loop from finishing.
            self._shutting_down = True
            if server is not None:
                # Stop accepting first, but do not wait for the server until the
                # active client handlers have released their sockets.
                server.close()
            tasks = tuple(self._client_tasks)
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            if server is not None:
                await self._wait_for_server_closed(server)

    # ----------------------------------------------------------- dispatch

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        task = asyncio.current_task()
        if task is not None:
            self._client_tasks.add(task)
        peer = writer.get_extra_info("peername")
        try:
            if len(self._client_tasks) > self.max_connections:
                logger.warning(
                    "Refusing proxy client %s: max_connections=%d reached",
                    peer,
                    self.max_connections,
                )
                return
            upstream = self.upstream
            self._tune_writer(writer)
            first = await self._timed(
                self._read_exactly(reader, 1, "client greeting", ClientProtocolError),
                self.handshake_timeout,
            )
            if first == b"\x05":
                await self._handle_socks5(reader, writer, upstream)
            elif first == b"\x04":
                await self._handle_socks4(reader, writer, upstream)
            else:
                await self._handle_http(first, reader, writer, upstream)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.debug("Proxy client %s failed: %s: %s", peer, type(exc).__name__, exc)
        finally:
            await self._close_writer(writer)
            if task is not None:
                self._client_tasks.discard(task)

    # --------------------------------------------------------------- HTTP

    async def _handle_http(
        self,
        first: bytes,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        upstream: Upstream,
    ) -> None:
        progress = _ResponseProgress()
        try:
            remainder = await self._timed(
                self._read_header_block(client_reader, "HTTP request headers", ClientProtocolError),
                self.handshake_timeout,
            )
            raw_header = first + remainder
            if len(raw_header) > _HEADER_LIMIT:
                raise ClientProtocolError("HTTP request headers are too large")
            request = self._parse_http_request(raw_header)
        except TimeoutError as exc:
            await self._send_http_error(client_writer, 408, "Request Timeout", progress)
            raise ClientProtocolError("Timed out reading HTTP request headers") from exc
        except (ValueError, ProxyProtocolError) as exc:
            await self._send_http_error(client_writer, 400, "Bad Request", progress)
            raise ClientProtocolError(str(exc)) from exc

        if request.method == "CONNECT":
            await self._handle_connect(request, client_reader, client_writer, upstream, progress)
        else:
            await self._handle_http_forward(
                request, client_reader, client_writer, upstream, progress
            )

    async def _handle_connect(
        self,
        request: _HttpRequest,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        upstream: Upstream,
        progress: _ResponseProgress,
    ) -> None:
        destination = request.destination
        try:
            tunnel_reader, tunnel_writer, _ = await self._open_tunnel(
                destination.host, destination.port, upstream
            )
        except ProxyPolicyError:
            await self._send_http_error(client_writer, 403, "Forbidden", progress)
            raise
        except TimeoutError as exc:
            await self._send_http_error(client_writer, 504, "Gateway Timeout", progress)
            raise _UpstreamTimeoutError(f"CONNECT {request.target} timed out") from exc
        except (OSError, ProxyProtocolError, ValueError) as exc:
            await self._send_http_error(client_writer, 502, "Bad Gateway", progress)
            raise UpstreamProtocolError(f"CONNECT {request.target} failed: {exc}") from exc
        try:
            client_writer.write(
                f"{request.version} 200 Connection Established\r\n\r\n".encode("ascii")
            )
            progress.final_started = True
            await client_writer.drain()
            await self._relay(client_reader, client_writer, tunnel_reader, tunnel_writer)
        finally:
            await self._close_writer(tunnel_writer)

    async def _handle_http_forward(
        self,
        request: _HttpRequest,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        upstream: Upstream,
        progress: _ResponseProgress,
    ) -> None:
        destination = request.destination
        remote_reader: asyncio.StreamReader | None = None
        remote_writer: asyncio.StreamWriter | None = None
        try:
            self._check_destination(destination.host, destination.port)
            headers = self._replace_host_header(request.headers, destination.host, destination.port)
            if upstream.proxy_type == "HTTP":
                remote_reader, remote_writer = await self._timed(
                    self._open_endpoint(upstream.host, upstream.port), self.connect_timeout
                )
                outgoing_target = destination.proxy_form
                http_upstream: Upstream | None = upstream
            else:
                remote_reader, remote_writer, _ = await self._open_tunnel(
                    destination.host, destination.port, upstream
                )
                outgoing_target = destination.origin_form
                http_upstream = None
            assert remote_writer is not None
            remote_writer.write(
                self._build_http_request(request, outgoing_target, headers, http_upstream)
            )
            await remote_writer.drain()
        except BaseException as exc:
            if remote_writer is not None:
                await self._close_writer(remote_writer)
            if isinstance(exc, ProxyPolicyError):
                await self._send_http_error(client_writer, 403, "Forbidden", progress)
                raise
            if isinstance(exc, TimeoutError):
                await self._send_http_error(client_writer, 504, "Gateway Timeout", progress)
                raise _UpstreamTimeoutError(f"HTTP {request.target} timed out") from exc
            if isinstance(exc, (OSError, ProxyProtocolError, ValueError)):
                await self._send_http_error(client_writer, 502, "Bad Gateway", progress)
                raise UpstreamProtocolError(f"HTTP {request.target} failed: {exc}") from exc
            raise

        assert remote_reader is not None
        assert remote_writer is not None
        try:
            if request.is_upgrade:
                await self._relay_http_upgrade(
                    client_reader,
                    client_writer,
                    remote_reader,
                    remote_writer,
                    request.method,
                    request.upgrade_protocols,
                    progress,
                )
            else:
                await self._relay_http_request(
                    client_reader,
                    client_writer,
                    remote_reader,
                    remote_writer,
                    request.method,
                    request.framing,
                    progress,
                )
        except _ClientTimeoutError:
            await self._send_http_error(client_writer, 408, "Request Timeout", progress)
            raise
        except _UpstreamTimeoutError:
            await self._send_http_error(client_writer, 504, "Gateway Timeout", progress)
            raise
        except ClientProtocolError:
            await self._send_http_error(client_writer, 400, "Bad Request", progress)
            raise
        except ProxyProtocolError:
            await self._send_http_error(client_writer, 502, "Bad Gateway", progress)
            raise
        except OSError as exc:
            # The upstream connection died mid-request (for example an early
            # rejection followed by a TCP reset).  Surface a gateway error
            # instead of dropping the client silently; the synthetic response
            # is suppressed automatically once a final response has started.
            await self._send_http_error(client_writer, 502, "Bad Gateway", progress)
            raise UpstreamProtocolError(f"HTTP {request.method} request failed: {exc}") from exc
        finally:
            await self._close_writer(remote_writer)

    # -------------------------------------------------------------- SOCKS5

    async def _handle_socks5(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        upstream: Upstream,
    ) -> None:
        accepted = await self._timed(
            self._negotiate_socks5_auth(client_reader, client_writer), self.handshake_timeout
        )
        if not accepted:
            return
        try:
            host, port = await self._timed(
                self._read_socks5_request(client_reader), self.handshake_timeout
            )
            remote_reader, remote_writer, bound_address = await self._open_tunnel(
                host, port, upstream
            )
        except _Socks5RequestError as exc:
            await self._send_socks5_reply(client_writer, exc.reply)
            return
        except (OSError, ProxyProtocolError, ValueError) as exc:
            await self._send_socks5_reply(client_writer, self._socks5_reply_for(exc))
            return

        try:
            await self._send_socks5_reply(client_writer, 0, bound_address)
            await self._relay(client_reader, client_writer, remote_reader, remote_writer)
        finally:
            await self._close_writer(remote_writer)

    async def _negotiate_socks5_auth(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> bool:
        count = (await self._read_exactly(reader, 1, "SOCKS5 method count"))[0]
        methods = await self._read_exactly(reader, count, "SOCKS5 methods") if count else b""
        if b"\x00" not in methods:
            writer.write(b"\x05\xff")
            await writer.drain()
            return False
        writer.write(b"\x05\x00")
        await writer.drain()
        return True

    async def _read_socks5_request(self, reader: asyncio.StreamReader) -> tuple[str, int]:
        version, command, reserved, address_type = await self._read_exactly(
            reader, 4, "SOCKS5 request"
        )
        if version != 5 or reserved != 0:
            raise ProxyProtocolError("Invalid SOCKS5 request")
        if command != 1:
            raise _Socks5RequestError(f"Unsupported SOCKS5 command: {command}", 7)
        if address_type not in (1, 3, 4):
            raise _Socks5RequestError(f"Unsupported SOCKS5 address type: {address_type}", 8)
        host = await self._read_socks_address(reader, address_type)
        port = struct.unpack(">H", await self._read_exactly(reader, 2, "SOCKS5 port"))[0]
        if not 1 <= port <= 65535:
            raise ProxyProtocolError("Invalid SOCKS5 destination port")
        return host, port

    # -------------------------------------------------------------- SOCKS4

    async def _handle_socks4(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        upstream: Upstream,
    ) -> None:
        try:
            host, port = await self._timed(
                self._read_socks4_request(client_reader), self.handshake_timeout
            )
            remote_reader, remote_writer, bound_address = await self._open_tunnel(
                host, port, upstream
            )
        except (OSError, ProxyProtocolError, ValueError):
            client_writer.write(b"\x00\x5b" + bytes(6))
            with contextlib.suppress(OSError):
                await client_writer.drain()
            return

        reply_port, reply_ip = self._socks4_bound_address(bound_address)
        try:
            client_writer.write(b"\x00\x5a" + struct.pack(">H", reply_port) + reply_ip)
            await client_writer.drain()
            await self._relay(client_reader, client_writer, remote_reader, remote_writer)
        finally:
            await self._close_writer(remote_writer)

    async def _read_socks4_request(self, reader: asyncio.StreamReader) -> tuple[str, int]:
        command = (await self._read_exactly(reader, 1, "SOCKS4 command"))[0]
        port = struct.unpack(">H", await self._read_exactly(reader, 2, "SOCKS4 port"))[0]
        raw_address = await self._read_exactly(reader, 4, "SOCKS4 address")
        # The client user ID is read to stay in frame, then discarded.
        await self._read_cstring(reader, "SOCKS4 user ID")
        if command != 1:
            raise ProxyProtocolError(f"Unsupported SOCKS4 command: {command}")
        if not 1 <= port <= 65535:
            raise ProxyProtocolError("Invalid SOCKS4 destination port")
        if raw_address[:3] == b"\x00\x00\x00" and raw_address[3] != 0:
            raw_host = await self._read_cstring(reader, "SOCKS4a destination")
            if not raw_host:
                raise ProxyProtocolError("SOCKS4a destination cannot be empty")
            host = _decode_host_name(raw_host)
        else:
            host = socket.inet_ntoa(raw_address)
        return host, port

    # ------------------------------------------------------------- upstream

    async def _open_tunnel(
        self, target_host: str, target_port: int, upstream: Upstream
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter, _BoundAddress | None]:
        self._check_destination(target_host, target_port)

        async def connect() -> (
            tuple[asyncio.StreamReader, asyncio.StreamWriter, _BoundAddress | None]
        ):
            if upstream.proxy_type == "DIRECT":
                reader, writer = await self._open_endpoint(target_host, target_port)
                return reader, writer, self._writer_bound_address(writer)
            reader, writer = await self._open_endpoint(upstream.host, upstream.port)
            try:
                bound_address: _BoundAddress | None = None
                if upstream.proxy_type == "HTTP":
                    await self._http_connect(reader, writer, target_host, target_port, upstream)
                elif upstream.proxy_type == "SOCKS5":
                    bound_address = await self._socks5_connect(
                        reader, writer, target_host, target_port, upstream
                    )
                else:
                    bound_address = await self._socks4_connect(
                        reader, writer, target_host, target_port, upstream
                    )
                return reader, writer, bound_address
            except BaseException:
                await self._close_writer(writer)
                raise

        return await self._timed(connect(), self.connect_timeout)

    async def _open_endpoint(
        self, host: str, port: int
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        reader, writer = await asyncio.open_connection(
            host,
            port,
            limit=_HEADER_LIMIT,
            happy_eyeballs_delay=0.25,
            interleave=1,
        )
        self._tune_writer(writer)
        return reader, writer

    async def _http_connect(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        host: str,
        port: int,
        upstream: Upstream,
    ) -> None:
        authority = self._format_authority(host, port)
        lines = [
            f"CONNECT {authority} HTTP/1.1",
            f"Host: {authority}",
            "Proxy-Connection: Keep-Alive",
        ]
        auth = self._basic_auth(upstream)
        if auth:
            lines.append(f"Proxy-Authorization: Basic {auth}")
        writer.write(("\r\n".join(lines) + "\r\n\r\n").encode("latin-1"))
        await writer.drain()
        raw = await self._read_header_block(
            reader, "HTTP upstream CONNECT response", UpstreamProtocolError
        )
        _, status, reason, _ = self._parse_http_response_header(raw)
        if not 200 <= status < 300:
            raise UpstreamProtocolError(
                f"HTTP upstream rejected CONNECT: {status} {reason}".rstrip()
            )

    async def _socks5_connect(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        host: str,
        port: int,
        upstream: Upstream,
    ) -> _BoundAddress:
        methods = b"\x00\x02" if upstream.username or upstream.password else b"\x00"
        writer.write(b"\x05" + bytes((len(methods),)) + methods)
        await writer.drain()
        version, method = await self._read_exactly(
            reader, 2, "SOCKS5 upstream greeting", UpstreamProtocolError
        )
        if version != 5 or method == 0xFF:
            raise UpstreamProtocolError("SOCKS5 upstream has no acceptable auth method")
        if method not in methods:
            raise UpstreamProtocolError(
                "SOCKS5 upstream selected an authentication method not offered"
            )
        if method == 2:
            username = upstream.username.encode("utf-8")
            password = upstream.password.encode("utf-8")
            if not 1 <= len(username) <= 255 or not 1 <= len(password) <= 255:
                raise UpstreamProtocolError("SOCKS5 credentials must contain 1 to 255 bytes")
            writer.write(
                b"\x01" + bytes((len(username),)) + username + bytes((len(password),)) + password
            )
            await writer.drain()
            auth_version, status = await self._read_exactly(
                reader, 2, "SOCKS5 upstream auth reply", UpstreamProtocolError
            )
            if auth_version != 1 or status != 0:
                raise UpstreamProtocolError("SOCKS5 upstream authentication failed")
        elif method != 0:
            raise UpstreamProtocolError(f"Unsupported SOCKS5 auth method: {method}")

        writer.write(b"\x05\x01\x00" + self._encode_socks5_address(host) + struct.pack(">H", port))
        await writer.drain()
        version, reply, reserved, address_type = await self._read_exactly(
            reader, 4, "SOCKS5 upstream reply", UpstreamProtocolError
        )
        if version != 5 or reserved != 0:
            raise UpstreamProtocolError("Invalid SOCKS5 upstream response")
        if reply != 0:
            # Checked before the bound address so a bogus ATYP cannot mask the code.
            raise UpstreamProtocolError(f"SOCKS5 upstream connect failed with code {reply}")
        bound_host = await self._read_socks_address(reader, address_type, UpstreamProtocolError)
        bound_port = struct.unpack(
            ">H",
            await self._read_exactly(
                reader, 2, "SOCKS5 upstream bound port", UpstreamProtocolError
            ),
        )[0]
        return _BoundAddress(bound_host, bound_port)

    async def _socks4_connect(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        host: str,
        port: int,
        upstream: Upstream,
    ) -> _BoundAddress:
        address = _ip_literal(host)
        if isinstance(address, ipaddress.IPv6Address):
            raise ProxyProtocolError("SOCKS4 upstream proxies cannot reach IPv6 destinations")
        if isinstance(address, ipaddress.IPv4Address):
            raw_address = address.packed
            domain = b""
        else:
            domain = _validate_destination_host(host).encode("ascii") + b"\x00"
            raw_address = b"\x00\x00\x00\x01"
        user = upstream.username.encode("utf-8")
        if b"\x00" in user or len(user) > _HEADER_LIMIT:
            raise ProxyProtocolError("Invalid SOCKS4 user ID")
        writer.write(b"\x04\x01" + struct.pack(">H", port) + raw_address + user + b"\x00" + domain)
        await writer.drain()
        response = await self._read_exactly(
            reader, 8, "SOCKS4 upstream reply", UpstreamProtocolError
        )
        if response[0] != 0 or response[1] != 0x5A:
            raise UpstreamProtocolError(
                "Invalid SOCKS4 upstream response " f"(version={response[0]}, status={response[1]})"
            )
        return _BoundAddress(socket.inet_ntoa(response[4:8]), struct.unpack(">H", response[2:4])[0])

    # ---------------------------------------------------------------- relay

    async def _relay(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        remote_reader: asyncio.StreamReader,
        remote_writer: asyncio.StreamWriter,
        *,
        activity: _ConnectionActivity | None = None,
    ) -> None:
        """Copy both directions until both sides reach EOF.

        Half-closes are preserved.  No writer is closed here: the function that
        opened a writer is the one that closes it.  Both directions share one
        inactivity watchdog, so legitimate one-way traffic keeps the tunnel
        alive while a completely stalled pair is still reaped.
        """

        if activity is None:
            activity = _ConnectionActivity(self.idle_timeout)
        client_to_remote = asyncio.create_task(self._pipe(client_reader, remote_writer, activity))
        remote_to_client = asyncio.create_task(self._pipe(remote_reader, client_writer, activity))
        tasks = (client_to_remote, remote_to_client)
        try:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for completed in done:
                if completed.cancelled():
                    raise asyncio.CancelledError
                error = completed.exception()
                if error is not None:
                    raise error
            for task in pending:
                await task
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _relay_http_request(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        remote_reader: asyncio.StreamReader,
        remote_writer: asyncio.StreamWriter,
        request_method: str,
        framing: _HttpBodyFraming,
        progress: _ResponseProgress,
    ) -> None:
        """Forward one framed request body while streaming the response.

        The response direction starts immediately so ``Expect: 100-continue``
        stays usable.  The request task stops exactly at the validated body
        boundary; any following pipelined request stays buffered locally and is
        discarded when this one-request connection closes.
        """

        activity = _ConnectionActivity(self.idle_timeout)
        request_body = asyncio.create_task(
            self._forward_http_body(client_reader, remote_writer, framing, activity=activity)
        )
        response = asyncio.create_task(
            self._forward_http_response(
                remote_reader,
                client_writer,
                request_method,
                progress,
                activity=activity,
            )
        )
        try:
            done, _ = await asyncio.wait(
                (request_body, response), return_when=asyncio.FIRST_COMPLETED
            )
            if request_body in done:
                try:
                    self._task_result(request_body, ClientProtocolError)
                except OSError:
                    # The upstream stopped reading the upload, typically an
                    # early rejection (401/413) followed by a close.  It may
                    # already have sent a complete final response; finish
                    # relaying it before surfacing the upload failure.
                    if not response.done():
                        await asyncio.wait((response,))
                    self._task_result(response, UpstreamProtocolError)
                    return
                if not response.done():
                    await asyncio.wait((response,))
                self._task_result(response, UpstreamProtocolError)
            else:
                # The upstream completed a framed response before the upload:
                # honour the early response and drop the rest of the body.
                self._task_result(response, UpstreamProtocolError)
                if request_body.done():
                    self._task_result(request_body, ClientProtocolError)
        finally:
            for task in (request_body, response):
                if not task.done():
                    task.cancel()
            await asyncio.gather(request_body, response, return_exceptions=True)

    async def _relay_http_upgrade(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        remote_reader: asyncio.StreamReader,
        remote_writer: asyncio.StreamWriter,
        request_method: str,
        requested_upgrades: Sequence[str],
        progress: _ResponseProgress,
    ) -> None:
        """Switch to an unbounded relay only after a valid upstream 101."""

        activity = _ConnectionActivity(self.idle_timeout)
        try:
            switched = await self._forward_http_response(
                remote_reader,
                client_writer,
                request_method,
                progress,
                activity=activity,
                requested_upgrades=requested_upgrades,
            )
        except TimeoutError as exc:
            raise _UpstreamTimeoutError("Timed out reading HTTP response") from exc
        except ProxyProtocolError as exc:
            raise self._as_error(exc, UpstreamProtocolError) from exc
        if switched:
            await self._relay(
                client_reader,
                client_writer,
                remote_reader,
                remote_writer,
                activity=activity,
            )

    async def _forward_http_response(
        self,
        remote_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        request_method: str,
        progress: _ResponseProgress,
        *,
        activity: _ConnectionActivity,
        requested_upgrades: Sequence[str] = (),
    ) -> bool:
        """Sanitise and forward one response; return True on an accepted 101.

        Interim (1xx) heads are forwarded so ``100-continue`` works, capped so a
        hostile upstream cannot stream them forever.  The final head is rebuilt
        without hop-by-hop fields and with ``Connection: close``, because this
        proxy always closes after one request; relaying the upstream's
        ``keep-alive`` would make the client lose its next request.
        """

        interim = 0
        while True:
            raw = await activity.wait(
                self._read_header_block(
                    remote_reader, "HTTP response headers", UpstreamProtocolError
                )
            )
            activity.touch()
            try:
                version, status, reason, headers = self._parse_http_response_header(raw)
            except ProxyProtocolError as exc:
                raise self._as_error(exc, UpstreamProtocolError) from exc

            if status == 101:
                if not requested_upgrades:
                    raise UpstreamProtocolError("Unexpected HTTP 101 response")
                selected_upgrades = self._http_upgrade_protocols(headers, UpstreamProtocolError)
                if not selected_upgrades:
                    raise UpstreamProtocolError("Invalid HTTP 101 Upgrade response")
                requested_keys = {
                    self._http_upgrade_protocol_key(protocol) for protocol in requested_upgrades
                }
                if any(
                    self._http_upgrade_protocol_key(protocol) not in requested_keys
                    for protocol in selected_upgrades
                ):
                    raise UpstreamProtocolError("HTTP 101 selected an unrequested Upgrade protocol")
                await self._write_response_head(
                    client_writer,
                    version,
                    status,
                    reason,
                    headers,
                    "Upgrade",
                    progress,
                    activity,
                )
                return True

            if 100 <= status < 200:
                interim += 1
                if interim > _MAX_INTERIM_RESPONSES:
                    raise UpstreamProtocolError("Too many interim HTTP responses")
                await self._write_response_head(
                    client_writer,
                    version,
                    status,
                    reason,
                    headers,
                    None,
                    progress,
                    activity,
                )
                continue

            framing, headers = self._http_response_body_framing(
                request_method, version, status, headers
            )
            await self._write_response_head(
                client_writer,
                version,
                status,
                reason,
                headers,
                "close",
                progress,
                activity,
            )
            await self._forward_http_body(
                remote_reader,
                client_writer,
                framing,
                activity=activity,
                error=UpstreamProtocolError,
                description="HTTP response",
            )
            return False

    async def _write_response_head(
        self,
        client_writer: asyncio.StreamWriter,
        version: str,
        status: int,
        reason: str,
        headers: Sequence[tuple[str, str]],
        connection: str | None,
        progress: _ResponseProgress,
        activity: _ConnectionActivity,
    ) -> None:
        client_writer.write(self._build_http_response(version, status, reason, headers, connection))
        if status == 101 or status >= 200:
            progress.final_started = True
        await self._drain(client_writer, activity)

    async def _forward_http_body(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        framing: _HttpBodyFraming,
        *,
        activity: _ConnectionActivity,
        error: type[ProxyProtocolError] = ClientProtocolError,
        description: str = "HTTP request",
    ) -> None:
        if framing.mode == "none":
            return
        if framing.mode == "content-length":
            await self._copy_http_body_bytes(
                reader,
                writer,
                framing.content_length,
                f"{description} body",
                error,
                activity,
            )
            await self._drain(writer, activity)
            return
        if framing.mode == "chunked":
            await self._forward_chunked_body(reader, writer, error, description, activity)
            return
        await self._pipe(reader, writer, activity)

    async def _forward_chunked_body(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        error: type[ProxyProtocolError] = ClientProtocolError,
        description: str = "HTTP request",
        activity: _ConnectionActivity | None = None,
    ) -> None:
        if activity is None:
            activity = _ConnectionActivity(self.idle_timeout)
        while True:
            size_line = await self._read_http_line(
                reader, f"{description} chunk size", error, activity
            )
            try:
                chunk_size = self._parse_http_chunk_size(size_line[:-2])
            except ProxyProtocolError as exc:
                raise error(str(exc)) from exc
            self._write_open(writer, size_line)
            await self._maybe_drain(writer, activity)

            if chunk_size:
                await self._copy_http_body_bytes(
                    reader,
                    writer,
                    chunk_size,
                    f"{description} chunk data",
                    error,
                    activity,
                )
                terminator = await self._read_exactly_active(
                    reader,
                    2,
                    f"{description} chunk terminator",
                    error,
                    activity,
                )
                if terminator != b"\r\n":
                    raise error(f"Invalid {description} chunk terminator")
                self._write_open(writer, terminator)
                await self._maybe_drain(writer, activity)
                continue

            trailer_size = 0
            while True:
                trailer_line = await self._read_http_line(
                    reader, f"{description} chunk trailer", error, activity
                )
                trailer_size += len(trailer_line)
                if trailer_size > _HEADER_LIMIT:
                    raise error(f"{description} chunk trailers are too large")
                if trailer_line == b"\r\n":
                    self._write_open(writer, trailer_line)
                    await self._drain(writer, activity)
                    return
                try:
                    name, _ = self._parse_http_field(trailer_line[:-2].decode("latin-1"))
                except ProxyProtocolError as exc:
                    raise error(str(exc)) from exc
                if name.lower() in _FORBIDDEN_TRAILER_FIELDS:
                    raise error(f"Forbidden HTTP trailer field: {name}")
                self._write_open(writer, trailer_line)
                await self._maybe_drain(writer, activity)

    async def _copy_http_body_bytes(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        size: int,
        description: str,
        error: type[ProxyProtocolError] = ClientProtocolError,
        activity: _ConnectionActivity | None = None,
    ) -> None:
        if activity is None:
            activity = _ConnectionActivity(self.idle_timeout)
        remaining = size
        while remaining:
            block_size = min(remaining, _BUFFER_SIZE)
            data = await self._read_exactly_active(
                reader,
                block_size,
                description,
                error,
                activity,
            )
            self._write_open(writer, data)
            remaining -= len(data)
            await self._maybe_drain(writer, activity)

    @staticmethod
    async def _read_exactly_active(
        reader: asyncio.StreamReader,
        size: int,
        description: str,
        error: type[ProxyProtocolError],
        activity: _ConnectionActivity,
    ) -> bytes:
        """Read exactly *size* while refreshing activity for each partial read."""

        output = bytearray()
        while len(output) < size:
            data = await activity.wait(reader.read(size - len(output)))
            if not data:
                raise error(f"Truncated {description}")
            activity.touch()
            output.extend(data)
        return bytes(output)

    async def _pipe(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        activity: _ConnectionActivity | None = None,
    ) -> None:
        """Copy until EOF, guarded by a connection-wide inactivity watchdog."""

        if activity is None:
            activity = _ConnectionActivity(self.idle_timeout)
        while True:
            data = await activity.wait(reader.read(_BUFFER_SIZE))
            if not data:
                with contextlib.suppress(OSError, RuntimeError, TimeoutError):
                    await self._drain(writer, activity)
                    if writer.can_write_eof():
                        writer.write_eof()
                return
            activity.touch()
            self._write_open(writer, data)
            if writer.transport.get_write_buffer_size() >= _WRITE_HIGH_WATER:
                await self._drain(writer, activity)

    @staticmethod
    def _write_open(writer: asyncio.StreamWriter, data: bytes) -> None:
        """Stop streaming as soon as a send marks the transport as closing."""

        if writer.is_closing():
            raise ConnectionResetError("Proxy transport is closing")
        writer.write(data)
        # Selector transports mark themselves closing synchronously when
        # socket.send() fails.  Detect that state before another chunk can
        # produce asyncio's repeated "socket.send() raised exception" warning.
        if writer.is_closing():
            raise ConnectionResetError("Proxy transport closed during write")

    async def _maybe_drain(
        self, writer: asyncio.StreamWriter, activity: _ConnectionActivity
    ) -> None:
        if writer.transport.get_write_buffer_size() >= _WRITE_HIGH_WATER:
            await self._drain(writer, activity)

    async def _drain(self, writer: asyncio.StreamWriter, activity: _ConnectionActivity) -> None:
        try:
            await activity.wait(writer.drain())
        except TimeoutError:
            # A full output buffer cannot be flushed during normal close; abort
            # now so a stalled peer releases its connection slot promptly.
            self._abort_writer(writer)
            raise
        activity.touch()

    # ------------------------------------------------------- HTTP parsing

    @classmethod
    def _parse_http_request(cls, raw_header: bytes) -> _HttpRequest:
        (method, target, version), headers = cls._parse_http_header(raw_header)
        framing, headers = cls._http_body_framing(version, headers)
        if method == "CONNECT":
            if framing.has_body:
                # A CONNECT body has no defined semantics and is a smuggling lever.
                raise ClientProtocolError("CONNECT requests cannot contain a body")
            host, port = cls._parse_authority(target, 443)
            return _HttpRequest(
                method,
                target,
                version,
                "authority",
                headers,
                framing,
                False,
                (),
                _HttpTarget(host, port),
            )
        if target == "*":
            if method != "OPTIONS":
                raise ClientProtocolError("Asterisk-form is only valid for OPTIONS")
            form: _TargetForm = "asterisk"
        elif target.startswith("/"):
            form = "origin"
        elif urlsplit(target).scheme:
            form = "absolute"
        else:
            raise ClientProtocolError("Unsupported HTTP request-target form")
        destination = cls._http_destination(target, form, headers)
        upgrade_protocols = (
            cls._http_upgrade_protocols(headers, ClientProtocolError)
            if version == "HTTP/1.1"
            else ()
        )
        is_upgrade = bool(upgrade_protocols)
        if is_upgrade and framing.has_body:
            raise ClientProtocolError("HTTP Upgrade requests cannot contain a body")
        return _HttpRequest(
            method,
            target,
            version,
            form,
            headers,
            framing,
            is_upgrade,
            upgrade_protocols,
            destination,
        )

    @classmethod
    def _parse_http_header(cls, raw_header: bytes) -> tuple[tuple[str, str, str], _Headers]:
        text = raw_header.decode("latin-1")
        lines = text.split("\r\n")
        if lines and not lines[0]:
            # RFC 9112 2.2: ignore one empty line before the request line.
            lines = lines[1:]
        if not lines:
            raise ClientProtocolError("Empty HTTP request")
        parts = lines[0].split(" ")
        if len(parts) != 3 or parts[2] not in _HTTP_VERSIONS:
            raise ClientProtocolError("Invalid HTTP request line")
        method, target, version = parts
        if not method or not set(method) <= _HTTP_TOKEN_CHARS:
            raise ClientProtocolError("Invalid HTTP method")
        if not target or any(not 0x21 <= ord(char) <= 0x7E for char in target):
            raise ClientProtocolError("Invalid HTTP request target")
        headers: list[tuple[str, str]] = []
        for line in lines[1:]:
            if not line:
                break
            headers.append(cls._parse_http_field(line))
        return (method, target, version), tuple(headers)

    @staticmethod
    def _parse_http_field(line: str) -> tuple[str, str]:
        if line[:1] in (" ", "\t") or ":" not in line:
            raise ProxyProtocolError("Invalid HTTP header")
        name, value = line.split(":", 1)
        if not name or not set(name) <= _HTTP_TOKEN_CHARS:
            raise ProxyProtocolError("Invalid HTTP header name")
        value = value.strip()
        if any((ord(char) < 32 and char != "\t") or ord(char) == 127 for char in value):
            raise ProxyProtocolError("Invalid HTTP header value")
        return name, value

    @classmethod
    def _parse_http_response_header(cls, raw_header: bytes) -> tuple[str, int, str, _Headers]:
        text = raw_header.decode("latin-1")
        lines = text.split("\r\n")
        parts = lines[0].split(" ", 2)
        if (
            len(parts) < 2
            or parts[0] not in _HTTP_VERSIONS
            or len(parts[1]) != 3
            or not parts[1].isascii()
            or not parts[1].isdecimal()
        ):
            raise UpstreamProtocolError("Invalid HTTP response status line")
        reason = parts[2] if len(parts) == 3 else ""
        if any((ord(char) < 32 and char != "\t") or ord(char) == 127 for char in reason):
            raise UpstreamProtocolError("Invalid HTTP response reason phrase")
        headers: list[tuple[str, str]] = []
        for line in lines[1:]:
            if not line:
                break
            headers.append(cls._parse_http_field(line))
        return parts[0], int(parts[1]), reason, tuple(headers)

    @classmethod
    def _http_body_framing(
        cls, version: str, headers: Sequence[tuple[str, str]]
    ) -> tuple[_HttpBodyFraming, _Headers]:
        content_lengths = [value for name, value in headers if name.lower() == "content-length"]
        transfer_encodings = [
            value for name, value in headers if name.lower() == "transfer-encoding"
        ]
        if content_lengths and transfer_encodings:
            raise ClientProtocolError("Content-Length and Transfer-Encoding cannot appear together")

        if content_lengths:
            parsed_lengths: list[int] = []
            for field_value in content_lengths:
                values = [value.strip() for value in field_value.split(",")]
                parsed_lengths.extend(cls._parse_http_content_length(value) for value in values)
            content_length = parsed_lengths[0]
            if any(value != content_length for value in parsed_lengths[1:]):
                raise ClientProtocolError("Conflicting Content-Length fields")
            normalized = cls._normalize_http_field(
                headers, "content-length", "Content-Length", str(content_length)
            )
            return _HttpBodyFraming("content-length", content_length), normalized

        if transfer_encodings:
            if version != "HTTP/1.1":
                raise ClientProtocolError("Transfer-Encoding requires HTTP/1.1")
            if len(transfer_encodings) != 1:
                raise ClientProtocolError("Duplicate Transfer-Encoding fields")
            codings = [value.strip().lower() for value in transfer_encodings[0].split(",")]
            if codings != ["chunked"]:
                raise ClientProtocolError(
                    "Transfer-Encoding must contain exactly one final chunked coding"
                )
            normalized = cls._normalize_http_field(
                headers, "transfer-encoding", "Transfer-Encoding", "chunked"
            )
            return _HttpBodyFraming("chunked"), normalized

        return _HttpBodyFraming("none"), tuple(headers)

    @classmethod
    def _http_response_body_framing(
        cls,
        request_method: str,
        version: str,
        status: int,
        headers: Sequence[tuple[str, str]],
    ) -> tuple[_HttpBodyFraming, _Headers]:
        """Validate upstream framing and resolve the final response boundary."""

        try:
            framing, normalized = cls._http_body_framing(version, headers)
        except ProxyProtocolError as exc:
            raise UpstreamProtocolError(str(exc)) from exc

        # These responses end at the header terminator regardless of metadata
        # fields describing the representation that a GET would have carried.
        if request_method == "HEAD" or status in {204, 304}:
            return _HttpBodyFraming("none"), normalized
        if framing.mode == "none":
            return _HttpBodyFraming("eof"), normalized
        return framing, normalized

    @staticmethod
    def _parse_http_content_length(value: str) -> int:
        if not value or not value.isascii() or not value.isdecimal():
            raise ClientProtocolError("Invalid Content-Length")
        digits = value.lstrip("0") or "0"
        if len(digits) > _MAX_CONTENT_LENGTH_DIGITS:
            raise ClientProtocolError("Content-Length is too large")
        length = int(digits)
        if length > _MAX_HTTP_BODY_LENGTH:
            raise ClientProtocolError("Content-Length is too large")
        return length

    @staticmethod
    def _normalize_http_field(
        headers: Sequence[tuple[str, str]],
        lower_name: str,
        canonical_name: str,
        canonical_value: str,
    ) -> _Headers:
        normalized: list[tuple[str, str]] = []
        added = False
        for name, value in headers:
            if name.lower() != lower_name:
                normalized.append((name, value))
            elif not added:
                normalized.append((canonical_name, canonical_value))
                added = True
        return tuple(normalized)

    @classmethod
    def _parse_http_chunk_size(cls, line: bytes) -> int:
        size_field, separator, extensions = line.partition(b";")
        if separator:
            size_token = size_field.rstrip(b" \t")
            cls._validate_http_chunk_extensions(
                size_field[len(size_token) :] + separator + extensions
            )
        else:
            size_token = size_field
        try:
            size_text = size_token.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ClientProtocolError("Invalid HTTP chunk size") from exc
        if not size_text or not set(size_text) <= _HTTP_HEX_CHARS:
            raise ClientProtocolError("Invalid HTTP chunk size")
        digits = size_text.lstrip("0") or "0"
        if len(digits) > _MAX_CHUNK_SIZE_DIGITS:
            raise ClientProtocolError("HTTP chunk is too large")
        size = int(digits, 16)
        if size > _MAX_HTTP_BODY_LENGTH:
            raise ClientProtocolError("HTTP chunk is too large")
        return size

    @staticmethod
    def _validate_http_chunk_extensions(value: bytes) -> None:
        text = value.decode("latin-1")
        index = 0
        size = len(text)
        while index < size:
            while index < size and text[index] in " \t":
                index += 1
            if index >= size or text[index] != ";":
                raise ClientProtocolError("Invalid HTTP chunk extension")
            index += 1
            while index < size and text[index] in " \t":
                index += 1
            name_start = index
            while index < size and text[index] in _HTTP_TOKEN_CHARS:
                index += 1
            if index == name_start:
                raise ClientProtocolError("Invalid HTTP chunk extension")
            while index < size and text[index] in " \t":
                index += 1
            if index < size and text[index] == "=":
                index += 1
                while index < size and text[index] in " \t":
                    index += 1
                if index < size and text[index] == '"':
                    index += 1
                    while True:
                        if index >= size:
                            raise ClientProtocolError("Invalid HTTP chunk extension")
                        character = text[index]
                        codepoint = ord(character)
                        if character == '"':
                            index += 1
                            break
                        if character == "\\":
                            index += 1
                            if index >= size:
                                raise ClientProtocolError("Invalid HTTP chunk extension")
                            codepoint = ord(text[index])
                            if not (
                                codepoint in (9, 32)
                                or 0x21 <= codepoint <= 0x7E
                                or codepoint >= 0x80
                            ):
                                raise ClientProtocolError("Invalid HTTP chunk extension")
                            index += 1
                        elif (
                            codepoint in (9, 32, 0x21)
                            or 0x23 <= codepoint <= 0x5B
                            or 0x5D <= codepoint <= 0x7E
                            or codepoint >= 0x80
                        ):
                            index += 1
                        else:
                            raise ClientProtocolError("Invalid HTTP chunk extension")
                else:
                    value_start = index
                    while index < size and text[index] in _HTTP_TOKEN_CHARS:
                        index += 1
                    if index == value_start:
                        raise ClientProtocolError("Invalid HTTP chunk extension")
            while index < size and text[index] in " \t":
                index += 1
            if index < size and text[index] != ";":
                raise ClientProtocolError("Invalid HTTP chunk extension")

    # ------------------------------------------------------ HTTP rendering

    @classmethod
    def _http_destination(
        cls, target: str, form: _TargetForm, headers: Sequence[tuple[str, str]]
    ) -> _HttpTarget:
        if form == "absolute":
            parsed = urlsplit(target)
            if parsed.scheme.lower() != "http" or not parsed.hostname:
                raise ClientProtocolError("Only plain HTTP absolute URLs are supported")
            try:
                parsed_port = parsed.port
            except ValueError as exc:
                raise ClientProtocolError("Invalid HTTP URL port") from exc
            port = 80 if parsed_port is None else parsed_port
            if not 1 <= port <= 65535:
                raise ClientProtocolError("Invalid HTTP URL port")
            try:
                host = _validate_destination_host(parsed.hostname)
            except ProxyProtocolError as exc:
                raise ClientProtocolError(str(exc)) from exc
            path = parsed.path or "/"
            authority = cls._format_authority(host, port, omit_default=80)
            return _HttpTarget(
                host,
                port,
                urlunsplit(SplitResult("", "", path, parsed.query, "")),
                urlunsplit(SplitResult("http", authority, path, parsed.query, "")),
            )

        host_headers = [value for name, value in headers if name.lower() == "host"]
        if len(host_headers) != 1 or not host_headers[0]:
            raise ClientProtocolError("HTTP Host header is required")
        host, port = cls._parse_authority(host_headers[0], 80)
        authority = cls._format_authority(host, port, omit_default=80)
        if form == "asterisk":
            # RFC 9112 3.2.4: through a proxy, server-wide OPTIONS travels as
            # absolute-form with an empty path.
            return _HttpTarget(host, port, "*", f"http://{authority}")
        return _HttpTarget(host, port, target, f"http://{authority}{target}")

    def _build_http_request(
        self,
        request: _HttpRequest,
        target: str,
        headers: Sequence[tuple[str, str]],
        http_upstream: Upstream | None,
    ) -> bytes:
        removed = (_HOP_BY_HOP_FIELDS | self._connection_tokens(headers)) - _END_TO_END_FIELDS
        if request.is_upgrade:
            # Upgrade is hop-by-hop, but a forwarding proxy may opt in by
            # recreating Connection: Upgrade on the next hop.
            removed = removed - {"upgrade"}
        lines = [f"{request.method} {target} {request.version}"]
        lines.extend(f"{name}: {value}" for name, value in headers if name.lower() not in removed)
        if http_upstream is not None:
            auth = self._basic_auth(http_upstream)
            if auth:
                lines.append(f"Proxy-Authorization: Basic {auth}")
        # One request per plain-HTTP client connection avoids pinning a reused
        # upstream connection to the first requested hostname.
        lines.append("Connection: Upgrade" if request.is_upgrade else "Connection: close")
        return ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1")

    @classmethod
    def _build_http_response(
        cls,
        version: str,
        status: int,
        reason: str,
        headers: Sequence[tuple[str, str]],
        connection: str | None,
    ) -> bytes:
        removed = (_HOP_BY_HOP_FIELDS | cls._connection_tokens(headers)) - _END_TO_END_FIELDS
        if connection == "Upgrade":
            removed = removed - {"upgrade"}
        if any(name.lower() == "transfer-encoding" for name, _ in headers):
            # RFC 9112 6.1: a proxy must drop Content-Length when a transfer
            # coding is present, otherwise the client sees two framings.
            removed = removed | {"content-length"}
        if 100 <= status < 200 or status == 204:
            # RFC 9110 8.6 and RFC 9112 6.1 forbid framing metadata on these
            # bodyless responses.  Sanitise it even when the upstream did not.
            removed = removed | {"content-length", "transfer-encoding"}
        lines = [f"{version} {status} {reason}"]
        lines.extend(f"{name}: {value}" for name, value in headers if name.lower() not in removed)
        if connection is not None:
            lines.append(f"Connection: {connection}")
        return ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1")

    @staticmethod
    def _connection_tokens(headers: Sequence[tuple[str, str]]) -> frozenset[str]:
        return frozenset(
            token.strip().lower()
            for name, value in headers
            if name.lower() == "connection"
            for token in value.split(",")
            if token.strip()
        )

    @classmethod
    def _replace_host_header(
        cls, headers: Sequence[tuple[str, str]], host: str, port: int
    ) -> _Headers:
        """Replace every client-supplied Host field with the routed authority."""

        authority = cls._format_authority(host, port, omit_default=80)
        output: list[tuple[str, str]] = []
        host_added = False
        for name, value in headers:
            if name.lower() != "host":
                output.append((name, value))
            elif not host_added:
                output.append(("Host", authority))
                host_added = True
        if not host_added:
            output.insert(0, ("Host", authority))
        return tuple(output)

    @classmethod
    def _http_upgrade_protocols(
        cls,
        headers: Sequence[tuple[str, str]],
        error: type[ProxyProtocolError] = ClientProtocolError,
    ) -> tuple[str, ...]:
        """Return a validated Upgrade list when Connection opts into it."""

        if "upgrade" not in cls._connection_tokens(headers):
            return ()
        fields = [value for name, value in headers if name.lower() == "upgrade"]
        if not fields:
            return ()
        protocols: list[str] = []
        for field_value in fields:
            for value in field_value.split(","):
                protocol = value.strip()
                name, separator, version = protocol.partition("/")
                if (
                    not name
                    or not set(name) <= _HTTP_TOKEN_CHARS
                    or (separator and (not version or not set(version) <= _HTTP_TOKEN_CHARS))
                    or "/" in version
                ):
                    raise error("Invalid HTTP Upgrade protocol")
                protocols.append(protocol)
        if not protocols:
            raise error("Invalid HTTP Upgrade protocol")
        return tuple(protocols)

    @staticmethod
    def _http_upgrade_protocol_key(protocol: str) -> tuple[str, str | None]:
        """Match protocol names case-insensitively while preserving versions."""

        name, separator, version = protocol.partition("/")
        return name.lower(), version if separator else None

    @classmethod
    def _is_http_upgrade(cls, headers: Sequence[tuple[str, str]]) -> bool:
        return bool(cls._http_upgrade_protocols(headers))

    @classmethod
    def _parse_authority(cls, authority: str, default_port: int) -> tuple[str, int]:
        authority = authority.strip()
        if not authority:
            raise ClientProtocolError("Empty authority")
        if authority.startswith("["):
            end = authority.find("]")
            if end < 2:
                raise ClientProtocolError("Invalid IPv6 authority")
            host = authority[1:end]
            suffix = authority[end + 1 :]
            if suffix:
                if not suffix.startswith(":"):
                    raise ClientProtocolError("Invalid IPv6 authority")
                port = cls._parse_port_token(suffix[1:])
            else:
                port = default_port
            if not isinstance(_ip_literal(host), ipaddress.IPv6Address):
                raise ClientProtocolError("Invalid IPv6 literal in authority")
        else:
            colons = authority.count(":")
            if colons == 1:
                host, _, raw_port = authority.rpartition(":")
                port = cls._parse_port_token(raw_port)
            elif colons > 1:
                # Tolerated: some clients send an unbracketed IPv6 literal.  It
                # must parse as one, so "a:b:c" cannot smuggle a bogus host.
                if not isinstance(_ip_literal(authority), ipaddress.IPv6Address):
                    raise ClientProtocolError("Invalid authority")
                host, port = authority, default_port
            else:
                host, port = authority, default_port
        try:
            host = _validate_destination_host(host)
        except ProxyProtocolError as exc:
            raise ClientProtocolError(str(exc)) from exc
        if not 1 <= port <= 65535:
            raise ClientProtocolError("Invalid port")
        return host, port

    @staticmethod
    def _parse_port_token(text: str) -> int:
        if not text or len(text) > 5 or not text.isascii() or not text.isdecimal():
            raise ClientProtocolError(f"Invalid port: {text!r}")
        return int(text)

    @staticmethod
    def _format_authority(host: str, port: int, omit_default: int | None = None) -> str:
        formatted_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
        return formatted_host if port == omit_default else f"{formatted_host}:{port}"

    @staticmethod
    def _basic_auth(upstream: Upstream) -> str:
        if not upstream.username and not upstream.password:
            return ""
        credentials = f"{upstream.username}:{upstream.password}".encode()
        return base64.b64encode(credentials).decode("ascii")

    # --------------------------------------------------------------- SOCKS

    @staticmethod
    def _encode_socks5_address(host: str) -> bytes:
        address = _ip_literal(host)
        if isinstance(address, ipaddress.IPv4Address):
            return b"\x01" + address.packed
        if isinstance(address, ipaddress.IPv6Address):
            return b"\x04" + address.packed
        encoded = _validate_destination_host(host).encode("ascii")
        if len(encoded) > 255:
            raise ProxyProtocolError("SOCKS5 destination name is too long")
        return b"\x03" + bytes((len(encoded),)) + encoded

    async def _read_socks_address(
        self,
        reader: asyncio.StreamReader,
        address_type: int,
        error: type[ProxyProtocolError] = ProxyProtocolError,
    ) -> str:
        if address_type == 1:
            raw = await self._read_exactly(reader, 4, "SOCKS IPv4 address", error)
            return socket.inet_ntop(socket.AF_INET, raw)
        if address_type == 4:
            raw = await self._read_exactly(reader, 16, "SOCKS IPv6 address", error)
            return socket.inet_ntop(socket.AF_INET6, raw)
        if address_type == 3:
            size = (await self._read_exactly(reader, 1, "SOCKS domain length", error))[0]
            if size == 0:
                raise error("SOCKS destination name cannot be empty")
            raw = await self._read_exactly(reader, size, "SOCKS domain", error)
            return _decode_host_name(raw)
        raise error(f"Unsupported SOCKS address type: {address_type}")

    async def _send_socks5_reply(
        self,
        writer: asyncio.StreamWriter,
        reply: int,
        bound_address: _BoundAddress | None = None,
    ) -> None:
        host, port = "0.0.0.0", 0
        if bound_address is not None:
            host = bound_address.host
            port = bound_address.port & 0xFFFF
        try:
            address = self._encode_socks5_address(host)
        except (ProxyProtocolError, ValueError):
            address, port = b"\x01\x00\x00\x00\x00", 0
        writer.write(b"\x05" + bytes((reply, 0)) + address + struct.pack(">H", port))
        with contextlib.suppress(OSError):
            await writer.drain()

    @staticmethod
    def _socks4_bound_address(
        bound_address: _BoundAddress | None,
    ) -> tuple[int, bytes]:
        if bound_address is None:
            return 0, b"\x00\x00\x00\x00"
        try:
            return bound_address.port & 0xFFFF, socket.inet_aton(bound_address.host)
        except Exception:
            return 0, b"\x00\x00\x00\x00"

    @staticmethod
    def _writer_bound_address(writer: asyncio.StreamWriter) -> _BoundAddress | None:
        try:
            sockname = writer.get_extra_info("sockname")
            return _BoundAddress(str(sockname[0]), int(sockname[1]) & 0xFFFF)
        except Exception:
            return None

    @staticmethod
    def _socks5_reply_for(exc: BaseException) -> int:
        if isinstance(exc, ProxyPolicyError):
            return 2
        if isinstance(exc, TimeoutError):
            return 6
        if isinstance(exc, socket.gaierror):
            return 4
        if isinstance(exc, OSError):
            if exc.errno is not None:
                return _SOCKS5_ERRNO_REPLIES.get(exc.errno, 1)
            return 1
        return 1

    async def _read_cstring(
        self,
        reader: asyncio.StreamReader,
        description: str,
        limit: int = _MAX_SOCKS_FIELD_LENGTH,
    ) -> bytes:
        value = bytearray()
        while True:
            byte = await self._read_exactly(reader, 1, description)
            if byte == b"\x00":
                return bytes(value)
            if len(value) >= limit:
                raise ProxyProtocolError(f"{description} is too long")
            value += byte

    # ------------------------------------------------------------ plumbing

    def _check_destination(self, host: str, port: int) -> None:
        policy = self.destination_policy
        if policy is None:
            return
        try:
            allowed = bool(policy(host, port))
        except Exception as exc:
            raise ProxyPolicyError(f"Destination policy failed for {host}:{port}") from exc
        if not allowed:
            raise ProxyPolicyError(f"Destination not allowed: {host}:{port}")

    @staticmethod
    async def _read_exactly(
        reader: asyncio.StreamReader,
        size: int,
        description: str,
        error: type[ProxyProtocolError] = ProxyProtocolError,
    ) -> bytes:
        try:
            return await reader.readexactly(size)
        except asyncio.IncompleteReadError as exc:
            raise error(f"Truncated {description}") from exc

    @staticmethod
    async def _read_header_block(
        reader: asyncio.StreamReader,
        description: str,
        error: type[ProxyProtocolError] = ProxyProtocolError,
    ) -> bytes:
        try:
            raw = await reader.readuntil(b"\r\n\r\n")
        except asyncio.IncompleteReadError as exc:
            raise error(f"Truncated {description}") from exc
        except asyncio.LimitOverrunError as exc:
            raise error(f"{description} are too large") from exc
        if len(raw) > _HEADER_LIMIT:
            raise error(f"{description} are too large")
        return raw

    async def _read_http_line(
        self,
        reader: asyncio.StreamReader,
        description: str,
        error: type[ProxyProtocolError] = ClientProtocolError,
        activity: _ConnectionActivity | None = None,
    ) -> bytes:
        if activity is None:
            activity = _ConnectionActivity(self.idle_timeout)
        try:
            line = await activity.wait(reader.readuntil(b"\r\n"))
        except asyncio.IncompleteReadError as exc:
            raise error(f"Truncated {description}") from exc
        except asyncio.LimitOverrunError as exc:
            raise error(f"{description} is too large") from exc
        if len(line) > _HEADER_LIMIT:
            raise error(f"{description} is too large")
        activity.touch()
        return line

    @staticmethod
    async def _timed(awaitable: Awaitable[_T], timeout: float) -> _T:
        return await asyncio.wait_for(awaitable, timeout=timeout)

    @staticmethod
    def _as_error(
        exc: ProxyProtocolError, error_class: type[ProxyProtocolError]
    ) -> ProxyProtocolError:
        if isinstance(exc, (ProxyPolicyError, ClientProtocolError, UpstreamProtocolError)):
            return exc
        return error_class(str(exc))

    @classmethod
    def _task_result(cls, task: asyncio.Task[_T], error_class: type[ProxyProtocolError]) -> _T:
        try:
            return task.result()
        except TimeoutError as exc:
            if issubclass(error_class, ClientProtocolError):
                raise _ClientTimeoutError("Timed out reading HTTP request body") from exc
            raise _UpstreamTimeoutError("Timed out reading HTTP response") from exc
        except ProxyProtocolError as exc:
            raise cls._as_error(exc, error_class) from exc

    async def _send_http_error(
        self,
        writer: asyncio.StreamWriter,
        status: int,
        reason: str,
        progress: _ResponseProgress | None = None,
    ) -> None:
        if progress is not None and progress.final_started:
            # Appending a status line now would splice a second response onto
            # the one already forwarded.
            logger.debug("Suppressed %s %s: response already started", status, reason)
            return
        body = f"{status} {reason}\n".encode("ascii")
        writer.write(
            f"HTTP/1.1 {status} {reason}\r\n"
            f"Content-Type: text/plain; charset=us-ascii\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n\r\n".encode("ascii") + body
        )
        if progress is not None:
            progress.final_started = True
        try:
            await asyncio.wait_for(
                writer.drain(),
                timeout=_WRITER_FLUSH_TIMEOUT,
            )
        except (OSError, TimeoutError):
            self._abort_writer(writer)

    @staticmethod
    def _tune_writer(writer: asyncio.StreamWriter) -> None:
        with contextlib.suppress(Exception):
            writer.transport.set_write_buffer_limits(high=_WRITE_HIGH_WATER, low=_WRITE_LOW_WATER)
        sock = writer.get_extra_info("socket")
        if sock is not None:
            with contextlib.suppress(OSError):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with contextlib.suppress(OSError):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    @staticmethod
    async def _flush_writer(writer: asyncio.StreamWriter) -> None:
        """Wait for the write buffer to become *empty*.

        ``drain()`` alone only guarantees "below the low-water mark", so closing
        right after it can discard up to ``_WRITE_LOW_WATER`` bytes when the
        close is followed by ``abort()``.  Limits of ``(0, 0)`` make any queued
        byte pause the protocol, so ``drain()`` returns only once it is gone.
        """

        with contextlib.suppress(Exception):
            writer.transport.set_write_buffer_limits(high=0, low=0)
        await writer.drain()

    async def _close_writer(self, writer: asyncio.StreamWriter) -> None:
        if self._shutting_down:
            flush_timeout = close_timeout = _SHUTDOWN_CLOSE_TIMEOUT
        else:
            flush_timeout, close_timeout = _WRITER_FLUSH_TIMEOUT, _WRITER_CLOSE_TIMEOUT
        transport = getattr(writer, "transport", None)
        if transport is not None and not transport.is_closing():
            try:
                await asyncio.wait_for(self._flush_writer(writer), timeout=flush_timeout)
            except asyncio.CancelledError:
                self._abort_writer(writer)
                raise
            except Exception:
                pass  # close() still flushes what it can
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=close_timeout)
        except asyncio.CancelledError:
            self._abort_writer(writer)
            raise
        except Exception:
            self._abort_writer(writer)

    @staticmethod
    def _abort_writer(writer: asyncio.StreamWriter) -> None:
        transport = getattr(writer, "transport", None)
        if transport is not None:
            with contextlib.suppress(Exception):
                transport.abort()

    @staticmethod
    async def _wait_for_server_closed(server: asyncio.AbstractServer) -> None:
        """Bound shutdown when a platform transport fails to detach cleanly.

        CPython's Windows Proactor transport can raise ``WSAEINVAL`` while
        closing a peer-disconnected socket; the failed callback then leaves the
        transport attached and ``wait_closed()`` never returns.  Client handlers
        have already been cancelled and awaited, so a bounded wait plus
        ``abort_clients()`` lets the loop finish instead of hanging the thread.
        """

        try:
            await asyncio.wait_for(server.wait_closed(), timeout=_SERVER_CLOSE_TIMEOUT)
        except TimeoutError:
            abort_clients = getattr(server, "abort_clients", None)
            if callable(abort_clients):
                abort_clients()
            logger.debug("Timed out waiting for proxy transports to detach during shutdown")

    @staticmethod
    def _positive_timeout(name: str, value: float) -> float:
        number = float(value)
        if not math.isfinite(number) or number <= 0:
            raise ValueError(f"{name} must be a positive finite number")
        return number

    @staticmethod
    def _is_loopback_host(host: str) -> bool:
        if not host:
            return False
        if host.lower() in {"localhost", "localhost.localdomain"}:
            return True
        address = _ip_literal(host.strip("[]"))
        return address is not None and address.is_loopback

    def _startup_state(self) -> tuple[BaseException | None, bool]:
        """Snapshot state published by the background listener thread."""

        with self._state_lock:
            return self._startup_error, self.is_running


__all__ = [
    "ClientProtocolError",
    "DestinationPolicy",
    "NativeProxyServer",
    "ProxyPolicyError",
    "ProxyProtocolError",
    "UpstreamProtocolError",
    "Upstream",
]
