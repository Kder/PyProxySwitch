#!/usr/bin/env python3

"""High-performance, standard-library-only local proxy server.

The listener accepts HTTP proxy, SOCKS4/SOCKS4a and SOCKS5 clients on the
same TCP port.  Each accepted connection takes an immutable snapshot of the
current upstream, so changing the upstream is atomic and does not restart the
listener or interrupt connections that are already transferring data.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import ipaddress
import logging
import socket
import struct
import threading
from dataclasses import dataclass
from typing import Awaitable, TypeVar
from urllib.parse import SplitResult, urlsplit, urlunsplit

logger = logging.getLogger("PyProxySwitch")

_BUFFER_SIZE = 512 * 1024
_HEADER_LIMIT = 64 * 1024
_WRITE_HIGH_WATER = 2 * 1024 * 1024
_WRITE_LOW_WATER = 512 * 1024
_SUPPORTED_TYPES = frozenset({"DIRECT", "HTTP", "SOCKS4", "SOCKS5"})
_T = TypeVar("_T")


class ProxyProtocolError(Exception):
    """A client or upstream proxy sent an invalid/unsupported message."""


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
        if proxy_type == "DIRECT":
            object.__setattr__(self, "host", "")
            object.__setattr__(self, "port", 0)
            return
        if not self.host:
            raise ValueError("Upstream proxy address cannot be empty")
        if not 1 <= int(self.port) <= 65535:
            raise ValueError(f"Invalid upstream proxy port: {self.port}")
        object.__setattr__(self, "port", int(self.port))

    @classmethod
    def direct(cls) -> Upstream:
        return cls(name="NoProxy")

    @property
    def description(self) -> str:
        if self.proxy_type == "DIRECT":
            return "NoProxy (direct)"
        return f"{self.name} ({self.proxy_type} {self.host}:{self.port})"


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
    ) -> None:
        if not 0 <= int(port) <= 65535:
            raise ValueError(f"Invalid local proxy port: {port}")
        self.host = host
        self.port = int(port)
        self.connect_timeout = float(connect_timeout)
        self.handshake_timeout = float(handshake_timeout)
        self._upstream = upstream or Upstream.direct()

        self._state_lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server: asyncio.AbstractServer | None = None
        self._stop_event: asyncio.Event | None = None
        self._ready = threading.Event()
        self._startup_error: BaseException | None = None
        self._bound_port = 0
        self._client_tasks: set[asyncio.Task[None]] = set()

    @property
    def upstream(self) -> Upstream:
        # Assigning/reading an object reference is atomic under CPython's GIL.
        # The lock also makes that contract explicit for alternative runtimes.
        with self._state_lock:
            return self._upstream

    @property
    def bound_port(self) -> int:
        with self._state_lock:
            return self._bound_port

    @property
    def is_running(self) -> bool:
        with self._state_lock:
            return (
                self._thread is not None
                and self._thread.is_alive()
                and self._ready.is_set()
                and self._startup_error is None
                and self._bound_port != 0
            )

    def set_upstream(self, upstream: Upstream) -> None:
        """Atomically route newly accepted connections through *upstream*."""
        if not isinstance(upstream, Upstream):
            raise TypeError("upstream must be an Upstream instance")
        with self._state_lock:
            self._upstream = upstream
        logger.info("Native proxy switched to %s", upstream.description)

    def start(self, timeout: float = 5.0) -> None:
        """Start the listener and wait until binding has completed."""
        with self._state_lock:
            if self.is_running:
                return
            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError("Native proxy is still starting or stopping")

            self._ready = threading.Event()
            self._startup_error = None
            self._bound_port = 0
            self._thread = threading.Thread(
                target=self._thread_main,
                name="PyProxySwitch-native-proxy",
                daemon=True,
            )
            self._thread.start()

        if not self._ready.wait(timeout):
            self.stop(timeout=timeout)
            raise TimeoutError("Timed out while starting the native proxy")
        if self._startup_error is not None:
            error = self._startup_error
            self.stop(timeout=timeout)
            raise RuntimeError(f"Cannot start native proxy: {error}") from error
        logger.info("Native proxy listening on %s:%s", self.host, self.bound_port)

    def stop(self, timeout: float = 5.0) -> bool:
        """Stop accepting clients, close active connections and join the loop."""
        with self._state_lock:
            thread = self._thread
            loop = self._loop
            stop_event = self._stop_event
        if thread is None:
            return True

        if loop is not None and stop_event is not None and loop.is_running():
            with contextlib.suppress(RuntimeError):
                loop.call_soon_threadsafe(stop_event.set)
        thread.join(max(0.0, timeout))
        stopped = not thread.is_alive()
        if stopped:
            with self._state_lock:
                self._thread = None
                self._loop = None
                self._server = None
                self._stop_event = None
                self._bound_port = 0
            logger.info("Native proxy stopped")
        return stopped

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run_server())
        except BaseException as exc:
            self._startup_error = exc
            logger.exception("Native proxy event loop failed")
        finally:
            self._ready.set()

    async def _run_server(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stop_event = asyncio.Event()
        try:
            self._server = await asyncio.start_server(
                self._handle_client,
                self.host,
                self.port,
                backlog=512,
                limit=_HEADER_LIMIT,
                start_serving=True,
            )
            sockets = self._server.sockets or []
            if not sockets:
                raise RuntimeError("Listener did not expose a bound socket")
            self._bound_port = int(sockets[0].getsockname()[1])
            self._ready.set()
            await self._stop_event.wait()
        except BaseException as exc:
            if not self._ready.is_set():
                self._startup_error = exc
                self._ready.set()
            else:
                raise
        finally:
            if self._server is not None:
                self._server.close()
                await self._server.wait_closed()
            tasks = tuple(self._client_tasks)
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        task = asyncio.current_task()
        if task is not None:
            self._client_tasks.add(task)

        upstream = self.upstream
        self._tune_writer(writer)
        try:
            first = await self._timed(reader.readexactly(1), self.handshake_timeout)
            if first == b"\x05":
                await self._handle_socks5(reader, writer, upstream)
            elif first == b"\x04":
                await self._handle_socks4(reader, writer, upstream)
            else:
                await self._handle_http(first, reader, writer, upstream)
        except (asyncio.IncompleteReadError, ConnectionError, BrokenPipeError):
            pass
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            peer = writer.get_extra_info("peername")
            logger.debug("Proxy client %s failed: %s", peer, exc)
        finally:
            await self._close_writer(writer)
            if task is not None:
                self._client_tasks.discard(task)

    async def _handle_http(
        self,
        first: bytes,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        upstream: Upstream,
    ) -> None:
        try:
            remainder = await self._timed(
                client_reader.readuntil(b"\r\n\r\n"), self.handshake_timeout
            )
            raw_header = first + remainder
            if len(raw_header) > _HEADER_LIMIT:
                raise ProxyProtocolError("HTTP request headers are too large")
            request_line, headers = self._parse_http_header(raw_header)
            method, target, version = request_line
        except (UnicodeError, ValueError, asyncio.LimitOverrunError, ProxyProtocolError) as exc:
            await self._send_http_error(client_writer, 400, "Bad Request")
            raise ProxyProtocolError(str(exc)) from exc

        if method.upper() == "CONNECT":
            try:
                host, port = self._parse_authority(target, 443)
                remote_reader, remote_writer = await self._open_tunnel(host, port, upstream)
            except (OSError, asyncio.TimeoutError, ProxyProtocolError, ValueError) as exc:
                await self._send_http_error(client_writer, 502, "Bad Gateway")
                raise ProxyProtocolError(f"CONNECT {target} failed: {exc}") from exc
            client_writer.write(f"{version} 200 Connection Established\r\n\r\n".encode("ascii"))
            await client_writer.drain()
            await self._relay(client_reader, client_writer, remote_reader, remote_writer)
            return

        remote_writer: asyncio.StreamWriter | None = None
        try:
            host, port, path, absolute_url = self._http_destination(target, headers)
            if upstream.proxy_type == "HTTP":
                remote_reader, remote_writer = await self._timed(
                    self._open_endpoint(upstream.host, upstream.port),
                    self.connect_timeout,
                )
                outgoing_target = absolute_url
            else:
                remote_reader, remote_writer = await self._open_tunnel(host, port, upstream)
                outgoing_target = path

            outgoing = self._build_http_request(
                method,
                outgoing_target,
                version,
                headers,
                upstream if upstream.proxy_type == "HTTP" else None,
            )
            remote_writer.write(outgoing)
            await remote_writer.drain()
        except (OSError, asyncio.TimeoutError, ProxyProtocolError, ValueError) as exc:
            if remote_writer is not None:
                await self._close_writer(remote_writer)
            await self._send_http_error(client_writer, 502, "Bad Gateway")
            raise ProxyProtocolError(f"HTTP {target} failed: {exc}") from exc

        assert remote_writer is not None
        await self._relay(client_reader, client_writer, remote_reader, remote_writer)

    async def _handle_socks5(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        upstream: Upstream,
    ) -> None:
        nmethods = (await self._timed(client_reader.readexactly(1), self.handshake_timeout))[0]
        methods = await self._timed(client_reader.readexactly(nmethods), self.handshake_timeout)
        if b"\x00" not in methods:
            client_writer.write(b"\x05\xff")
            await client_writer.drain()
            return
        client_writer.write(b"\x05\x00")
        await client_writer.drain()

        version, command, reserved, address_type = await self._timed(
            client_reader.readexactly(4), self.handshake_timeout
        )
        if version != 5 or reserved != 0:
            raise ProxyProtocolError("Invalid SOCKS5 request")
        if command != 1:
            await self._send_socks5_reply(client_writer, 7)
            return
        try:
            host = await self._read_socks_address(client_reader, address_type)
            port = struct.unpack(">H", await client_reader.readexactly(2))[0]
            remote_reader, remote_writer = await self._open_tunnel(host, port, upstream)
        except asyncio.TimeoutError:
            await self._send_socks5_reply(client_writer, 6)
            return
        except (OSError, ProxyProtocolError, ValueError):
            await self._send_socks5_reply(client_writer, 5)
            return

        await self._send_socks5_reply(client_writer, 0, remote_writer.get_extra_info("sockname"))
        await self._relay(client_reader, client_writer, remote_reader, remote_writer)

    async def _handle_socks4(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        upstream: Upstream,
    ) -> None:
        command = (await self._timed(client_reader.readexactly(1), self.handshake_timeout))[0]
        port = struct.unpack(">H", await client_reader.readexactly(2))[0]
        raw_address = await client_reader.readexactly(4)
        await self._read_cstring(client_reader)  # Client user ID is intentionally not required.
        if command != 1:
            client_writer.write(b"\x00\x5b\x00\x00\x00\x00\x00\x00")
            await client_writer.drain()
            return
        if raw_address[:3] == b"\x00\x00\x00" and raw_address[3] != 0:
            host = (await self._read_cstring(client_reader)).decode("idna")
        else:
            host = socket.inet_ntoa(raw_address)
        try:
            remote_reader, remote_writer = await self._open_tunnel(host, port, upstream)
        except (OSError, asyncio.TimeoutError, ProxyProtocolError, ValueError):
            client_writer.write(b"\x00\x5b\x00\x00\x00\x00\x00\x00")
            await client_writer.drain()
            return

        reply_port, reply_ip = self._socks4_bound_address(remote_writer)
        client_writer.write(b"\x00\x5a" + struct.pack(">H", reply_port) + reply_ip)
        await client_writer.drain()
        await self._relay(client_reader, client_writer, remote_reader, remote_writer)

    async def _open_tunnel(
        self, target_host: str, target_port: int, upstream: Upstream
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        async def connect() -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
            if upstream.proxy_type == "DIRECT":
                return await self._open_endpoint(target_host, target_port)
            reader, writer = await self._open_endpoint(upstream.host, upstream.port)
            try:
                if upstream.proxy_type == "HTTP":
                    await self._http_connect(reader, writer, target_host, target_port, upstream)
                elif upstream.proxy_type == "SOCKS5":
                    await self._socks5_connect(reader, writer, target_host, target_port, upstream)
                elif upstream.proxy_type == "SOCKS4":
                    await self._socks4_connect(reader, writer, target_host, target_port, upstream)
                return reader, writer
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
        response = await reader.readuntil(b"\r\n\r\n")
        if len(response) > _HEADER_LIMIT:
            raise ProxyProtocolError("HTTP upstream response is too large")
        status_line = response.split(b"\r\n", 1)[0].decode("latin-1")
        parts = status_line.split(None, 2)
        if len(parts) < 2 or not parts[1].isdigit() or not 200 <= int(parts[1]) < 300:
            raise ProxyProtocolError(f"HTTP upstream rejected CONNECT: {status_line}")

    async def _socks5_connect(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        host: str,
        port: int,
        upstream: Upstream,
    ) -> None:
        methods = b"\x00\x02" if upstream.username or upstream.password else b"\x00"
        writer.write(b"\x05" + bytes((len(methods),)) + methods)
        await writer.drain()
        version, method = await reader.readexactly(2)
        if version != 5 or method == 0xFF:
            raise ProxyProtocolError("SOCKS5 upstream has no acceptable auth method")
        if method == 2:
            username = upstream.username.encode("utf-8")
            password = upstream.password.encode("utf-8")
            if len(username) > 255 or len(password) > 255:
                raise ProxyProtocolError("SOCKS5 credentials are too long")
            writer.write(
                b"\x01" + bytes((len(username),)) + username + bytes((len(password),)) + password
            )
            await writer.drain()
            auth_version, status = await reader.readexactly(2)
            if auth_version != 1 or status != 0:
                raise ProxyProtocolError("SOCKS5 upstream authentication failed")
        elif method != 0:
            raise ProxyProtocolError(f"Unsupported SOCKS5 auth method: {method}")

        address = self._encode_socks5_address(host)
        writer.write(b"\x05\x01\x00" + address + struct.pack(">H", port))
        await writer.drain()
        version, reply, reserved, address_type = await reader.readexactly(4)
        if version != 5 or reserved != 0:
            raise ProxyProtocolError("Invalid SOCKS5 upstream response")
        await self._read_socks_address(reader, address_type)
        await reader.readexactly(2)
        if reply != 0:
            raise ProxyProtocolError(f"SOCKS5 upstream connect failed with code {reply}")

    async def _socks4_connect(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        host: str,
        port: int,
        upstream: Upstream,
    ) -> None:
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if isinstance(address, ipaddress.IPv4Address):
            raw_address = address.packed
            domain = b""
        else:
            try:
                domain = host.encode("idna") + b"\x00"
            except UnicodeError as exc:
                raise ProxyProtocolError("Invalid SOCKS4a destination") from exc
            raw_address = b"\x00\x00\x00\x01"
        user = upstream.username.encode("utf-8")
        if b"\x00" in user:
            raise ProxyProtocolError("SOCKS4 user ID contains a null byte")
        writer.write(b"\x04\x01" + struct.pack(">H", port) + raw_address + user + b"\x00" + domain)
        await writer.drain()
        response = await reader.readexactly(8)
        if response[1] != 0x5A:
            raise ProxyProtocolError(f"SOCKS4 upstream connect failed with code {response[1]}")

    async def _relay(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        remote_reader: asyncio.StreamReader,
        remote_writer: asyncio.StreamWriter,
    ) -> None:
        client_to_remote = asyncio.create_task(self._pipe(client_reader, remote_writer))
        remote_to_client = asyncio.create_task(self._pipe(remote_reader, client_writer))
        try:
            done, _ = await asyncio.wait(
                (client_to_remote, remote_to_client), return_when=asyncio.FIRST_COMPLETED
            )
            first = next(iter(done))
            error = first.exception()
            if error is not None:
                raise error
            if remote_to_client in done:
                client_to_remote.cancel()
            else:
                # A client may half-close after uploading a request body.  Keep
                # receiving the response in that case instead of truncating it.
                await remote_to_client
        finally:
            for task in (client_to_remote, remote_to_client):
                if not task.done():
                    task.cancel()
            await asyncio.gather(client_to_remote, remote_to_client, return_exceptions=True)
            await self._close_writer(remote_writer)

    @staticmethod
    async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        while True:
            data = await reader.read(_BUFFER_SIZE)
            if not data:
                with contextlib.suppress(OSError, RuntimeError):
                    await writer.drain()
                    if writer.can_write_eof():
                        writer.write_eof()
                        await writer.drain()
                return
            writer.write(data)
            if writer.transport.get_write_buffer_size() >= _WRITE_HIGH_WATER:
                await writer.drain()

    @staticmethod
    def _parse_http_header(raw_header: bytes) -> tuple[tuple[str, str, str], list[tuple[str, str]]]:
        text = raw_header.decode("latin-1")
        lines = text.split("\r\n")
        parts = lines[0].split(None, 2)
        if len(parts) != 3 or not parts[2].startswith("HTTP/"):
            raise ProxyProtocolError("Invalid HTTP request line")
        headers: list[tuple[str, str]] = []
        for line in lines[1:]:
            if not line:
                break
            if line[:1] in " \t" or ":" not in line:
                raise ProxyProtocolError("Invalid HTTP header")
            name, value = line.split(":", 1)
            headers.append((name.strip(), value.strip()))
        return (parts[0], parts[1], parts[2]), headers

    def _http_destination(
        self, target: str, headers: list[tuple[str, str]]
    ) -> tuple[str, int, str, str]:
        parsed = urlsplit(target)
        if parsed.scheme:
            if parsed.scheme.lower() != "http" or not parsed.hostname:
                raise ProxyProtocolError("Only plain HTTP absolute URLs are supported")
            host = parsed.hostname
            try:
                port = parsed.port or 80
            except ValueError as exc:
                raise ProxyProtocolError("Invalid HTTP URL port") from exc
            path = urlunsplit(SplitResult("", "", parsed.path or "/", parsed.query, ""))
            authority = self._format_authority(host, port, omit_default=80)
            absolute_url = urlunsplit(
                SplitResult("http", authority, parsed.path or "/", parsed.query, "")
            )
            return host, port, path, absolute_url

        host_header = next((value for name, value in headers if name.lower() == "host"), "")
        if not host_header:
            raise ProxyProtocolError("HTTP Host header is required")
        host, port = self._parse_authority(host_header, 80)
        path = target if target.startswith(("/", "*")) else f"/{target}"
        authority = self._format_authority(host, port, omit_default=80)
        return host, port, path, f"http://{authority}{path}"

    def _build_http_request(
        self,
        method: str,
        target: str,
        version: str,
        headers: list[tuple[str, str]],
        http_upstream: Upstream | None,
    ) -> bytes:
        connection_tokens: set[str] = set()
        for name, value in headers:
            if name.lower() == "connection":
                connection_tokens.update(token.strip().lower() for token in value.split(","))
        removed = {
            "connection",
            "proxy-connection",
            "proxy-authorization",
            "keep-alive",
            *connection_tokens,
        }
        output = [f"{method} {target} {version}"]
        output.extend(f"{name}: {value}" for name, value in headers if name.lower() not in removed)
        if http_upstream is not None:
            auth = self._basic_auth(http_upstream)
            if auth:
                output.append(f"Proxy-Authorization: Basic {auth}")
        # One request per plain-HTTP client connection avoids incorrectly
        # pinning a reused proxy connection to the first requested hostname.
        output.append("Connection: close")
        return ("\r\n".join(output) + "\r\n\r\n").encode("latin-1")

    @staticmethod
    def _parse_authority(authority: str, default_port: int) -> tuple[str, int]:
        authority = authority.strip()
        if authority.startswith("["):
            end = authority.find("]")
            if end < 0:
                raise ValueError("Invalid IPv6 authority")
            host = authority[1:end]
            suffix = authority[end + 1 :]
            if suffix and not suffix.startswith(":"):
                raise ValueError("Invalid IPv6 authority")
            port = int(suffix[1:]) if suffix.startswith(":") else default_port
        elif authority.count(":") == 1:
            host, raw_port = authority.rsplit(":", 1)
            port = int(raw_port)
        elif ":" in authority:
            host, port = authority, default_port
        else:
            host, port = authority, default_port
        if not host or not 1 <= port <= 65535:
            raise ValueError("Invalid host or port")
        return host, port

    @staticmethod
    def _format_authority(host: str, port: int, omit_default: int | None = None) -> str:
        formatted_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
        return formatted_host if port == omit_default else f"{formatted_host}:{port}"

    @staticmethod
    def _basic_auth(upstream: Upstream) -> str:
        if not upstream.username and not upstream.password:
            return ""
        credentials = f"{upstream.username}:{upstream.password}".encode("utf-8")
        return base64.b64encode(credentials).decode("ascii")

    @staticmethod
    def _encode_socks5_address(host: str) -> bytes:
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            encoded = host.encode("idna")
            if len(encoded) > 255:
                raise ProxyProtocolError("SOCKS5 destination name is too long")
            return b"\x03" + bytes((len(encoded),)) + encoded
        if isinstance(address, ipaddress.IPv4Address):
            return b"\x01" + address.packed
        return b"\x04" + address.packed

    async def _read_socks_address(self, reader: asyncio.StreamReader, address_type: int) -> str:
        if address_type == 1:
            return socket.inet_ntop(socket.AF_INET, await reader.readexactly(4))
        if address_type == 4:
            return socket.inet_ntop(socket.AF_INET6, await reader.readexactly(16))
        if address_type == 3:
            size = (await reader.readexactly(1))[0]
            return (await reader.readexactly(size)).decode("idna")
        raise ProxyProtocolError(f"Unsupported SOCKS5 address type: {address_type}")

    async def _send_socks5_reply(
        self,
        writer: asyncio.StreamWriter,
        reply: int,
        sockname: tuple[object, ...] | None = None,
    ) -> None:
        host = str(sockname[0]) if sockname else "0.0.0.0"
        port = int(sockname[1]) if sockname else 0
        try:
            address = self._encode_socks5_address(host)
        except ProxyProtocolError:
            address = b"\x01\x00\x00\x00\x00"
        writer.write(b"\x05" + bytes((reply, 0)) + address + struct.pack(">H", port))
        await writer.drain()

    @staticmethod
    def _socks4_bound_address(writer: asyncio.StreamWriter) -> tuple[int, bytes]:
        sockname = writer.get_extra_info("sockname")
        if not sockname:
            return 0, b"\x00\x00\x00\x00"
        try:
            return int(sockname[1]), socket.inet_aton(str(sockname[0]))
        except OSError:
            return int(sockname[1]), b"\x00\x00\x00\x00"

    @staticmethod
    async def _read_cstring(reader: asyncio.StreamReader, limit: int = 1024) -> bytes:
        value = await reader.readuntil(b"\x00")
        if len(value) > limit:
            raise ProxyProtocolError("SOCKS4 field is too long")
        return value[:-1]

    @staticmethod
    async def _send_http_error(writer: asyncio.StreamWriter, status: int, reason: str) -> None:
        body = f"{status} {reason}\n".encode("ascii")
        writer.write(
            f"HTTP/1.1 {status} {reason}\r\n"
            f"Content-Type: text/plain; charset=us-ascii\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n\r\n".encode("ascii")
            + body
        )
        with contextlib.suppress(ConnectionError):
            await writer.drain()

    @staticmethod
    def _tune_writer(writer: asyncio.StreamWriter) -> None:
        transport = writer.transport
        transport.set_write_buffer_limits(high=_WRITE_HIGH_WATER, low=_WRITE_LOW_WATER)
        sock = writer.get_extra_info("socket")
        if sock is not None:
            with contextlib.suppress(OSError):
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with contextlib.suppress(OSError):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    @staticmethod
    async def _close_writer(writer: asyncio.StreamWriter) -> None:
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()

    @staticmethod
    async def _timed(awaitable: Awaitable[_T], timeout: float) -> _T:
        return await asyncio.wait_for(awaitable, timeout=timeout)


__all__ = ["NativeProxyServer", "ProxyProtocolError", "Upstream"]
