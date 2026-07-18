import asyncio
import contextlib
import http.server
import queue
import socket
import socketserver
import struct
import threading
from unittest.mock import AsyncMock

import pytest

from pyproxyswitch.native_proxy import NativeProxyServer, ProxyProtocolError, Upstream


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise AssertionError(f"connection closed after {len(chunks)} of {size} bytes")
        chunks.extend(chunk)
    return bytes(chunks)


def _recv_until(sock: socket.socket, marker: bytes) -> bytes:
    chunks = bytearray()
    while marker not in chunks:
        chunk = sock.recv(4096)
        if not chunk:
            break
        chunks.extend(chunk)
    return bytes(chunks)


class _EchoHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        while data := self.request.recv(65536):
            self.request.sendall(data)


class _ThreadingServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class _HttpHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        body = f"proxied:{self.path}".encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.do_GET()

    def log_message(self, format: str, *args: object) -> None:
        pass


class _UpgradeEchoHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        request = _recv_until(self.request, b"\r\n\r\n")
        if b"Connection: Upgrade\r\n" not in request or b"Upgrade: websocket\r\n" not in request:
            self.request.sendall(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n")
            return
        self.request.sendall(
            b"HTTP/1.1 101 Switching Protocols\r\n"
            b"Connection: Upgrade\r\n"
            b"Upgrade: websocket\r\n\r\n"
        )
        while data := self.request.recv(65536):
            self.request.sendall(data)


class _RemoteHalfCloseHandler(socketserver.BaseRequestHandler):
    received: queue.Queue[bytes] = queue.Queue()

    def handle(self) -> None:
        self.request.sendall(b"ready")
        self.request.shutdown(socket.SHUT_WR)
        chunks = bytearray()
        while data := self.request.recv(65536):
            chunks.extend(data)
        type(self).received.put(bytes(chunks))


@contextlib.contextmanager
def _running_tcp_server(handler: type[socketserver.BaseRequestHandler]):
    server = _ThreadingServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@contextlib.contextmanager
def _running_http_server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _HttpHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@contextlib.contextmanager
def _running_proxy(*, handshake_timeout: float = 1.0, upstream: Upstream | None = None):
    server = NativeProxyServer(
        host="127.0.0.1",
        port=0,
        upstream=upstream,
        connect_timeout=2,
        handshake_timeout=handshake_timeout,
    )
    server.start()
    try:
        yield server
    finally:
        assert server.stop()


def test_plain_http_forwarding() -> None:
    with (
        _running_http_server() as (_, destination_port),
        _running_proxy() as proxy,
        socket.create_connection(("127.0.0.1", proxy.bound_port), timeout=2) as client,
    ):
        client.sendall(
            f"GET http://127.0.0.1:{destination_port}/hello?q=1 HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{destination_port}\r\n\r\n".encode()
        )
        response = bytearray()
        while chunk := client.recv(4096):
            response.extend(chunk)

    assert b"200 OK" in response
    assert response.endswith(b"proxied:/hello?q=1")


def test_plain_http_forwarding_through_http_upstream() -> None:
    with (
        _running_http_server() as (_, destination_port),
        _running_proxy() as upstream_server,
        _running_proxy(
            upstream=Upstream(
                name="http-upstream",
                proxy_type="HTTP",
                host="127.0.0.1",
                port=upstream_server.bound_port,
            )
        ) as proxy,
        socket.create_connection(("127.0.0.1", proxy.bound_port), timeout=2) as client,
    ):
        client.sendall(
            f"GET http://127.0.0.1:{destination_port}/chained HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{destination_port}\r\n\r\n".encode()
        )
        response = bytearray()
        while chunk := client.recv(4096):
            response.extend(chunk)

    assert response.endswith(b"proxied:/chained")


def test_explicit_zero_port_in_absolute_http_url_is_rejected() -> None:
    server = NativeProxyServer(port=0)

    with pytest.raises(ProxyProtocolError, match="Invalid HTTP URL port"):
        server._http_destination("http://example.com:0/test", [])


def test_options_asterisk_is_preserved_through_http_upstream() -> None:
    with (
        _running_http_server() as (_, destination_port),
        _running_proxy() as upstream_server,
        _running_proxy(
            upstream=Upstream(
                name="http-upstream",
                proxy_type="HTTP",
                host="127.0.0.1",
                port=upstream_server.bound_port,
            )
        ) as proxy,
        socket.create_connection(("127.0.0.1", proxy.bound_port), timeout=2) as client,
    ):
        client.sendall(
            f"OPTIONS * HTTP/1.1\r\nHost: 127.0.0.1:{destination_port}\r\n\r\n".encode()
        )
        response = bytearray()
        while chunk := client.recv(4096):
            response.extend(chunk)

    assert response.endswith(b"proxied:*")


def test_http_connect_tunnel() -> None:
    with (
        _running_tcp_server(_EchoHandler) as (_, destination_port),
        _running_proxy() as proxy,
        socket.create_connection(("127.0.0.1", proxy.bound_port), timeout=2) as client,
    ):
        client.sendall(
            f"CONNECT 127.0.0.1:{destination_port} HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{destination_port}\r\n\r\n".encode()
        )
        response = _recv_until(client, b"\r\n\r\n")
        assert response.endswith(b"\r\n\r\n")
        assert b"200 Connection Established" in response

        client.sendall(b"connect-echo")
        assert _recv_exact(client, len(b"connect-echo")) == b"connect-echo"


@pytest.mark.parametrize("proxy_type", ["HTTP", "SOCKS4", "SOCKS5"])
def test_connect_tunnel_through_each_upstream_type(proxy_type: str) -> None:
    with (
        _running_tcp_server(_EchoHandler) as (_, destination_port),
        _running_proxy() as upstream_server,
        _running_proxy(
            upstream=Upstream(
                name="upstream",
                proxy_type=proxy_type,
                host="127.0.0.1",
                port=upstream_server.bound_port,
            )
        ) as proxy,
        socket.create_connection(("127.0.0.1", proxy.bound_port), timeout=2) as client,
    ):
        client.sendall(
            f"CONNECT 127.0.0.1:{destination_port} HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{destination_port}\r\n\r\n".encode()
        )
        assert b"200 Connection Established" in _recv_until(client, b"\r\n\r\n")

        payload = f"{proxy_type}-upstream".encode()
        client.sendall(payload)
        assert _recv_exact(client, len(payload)) == payload


def test_socks5_connect_tunnel() -> None:
    with (
        _running_tcp_server(_EchoHandler) as (_, destination_port),
        _running_proxy() as proxy,
        socket.create_connection(("127.0.0.1", proxy.bound_port), timeout=2) as client,
    ):
        client.sendall(b"\x05\x01\x00")
        assert _recv_exact(client, 2) == b"\x05\x00"

        client.sendall(
            b"\x05\x01\x00\x01"
            + socket.inet_aton("127.0.0.1")
            + struct.pack(">H", destination_port)
        )
        version, reply, _, address_type = _recv_exact(client, 4)
        assert (version, reply) == (5, 0)
        address_size = {1: 4, 4: 16}[address_type]
        _recv_exact(client, address_size + 2)

        client.sendall(b"socks5-echo")
        assert _recv_exact(client, len(b"socks5-echo")) == b"socks5-echo"


def test_socks4a_connect_tunnel() -> None:
    with (
        _running_tcp_server(_EchoHandler) as (_, destination_port),
        _running_proxy() as proxy,
        socket.create_connection(("127.0.0.1", proxy.bound_port), timeout=2) as client,
    ):
        client.sendall(
            b"\x04\x01"
            + struct.pack(">H", destination_port)
            + b"\x00\x00\x00\x01user\x00localhost\x00"
        )
        reply = _recv_exact(client, 8)
        assert reply[:2] == b"\x00\x5a"

        client.sendall(b"socks4a-echo")
        assert _recv_exact(client, len(b"socks4a-echo")) == b"socks4a-echo"


def test_socks4a_invalid_domain_returns_failure_reply() -> None:
    with (
        _running_proxy() as proxy,
        socket.create_connection(("127.0.0.1", proxy.bound_port), timeout=2) as client,
    ):
        client.sendall(b"\x04\x01\x00\x50\x00\x00\x00\x01user\x00\xff\x00")

        assert _recv_exact(client, 8)[:2] == b"\x00\x5b"


def test_socks5_unsupported_address_type_returns_specific_reply() -> None:
    with (
        _running_proxy() as proxy,
        socket.create_connection(("127.0.0.1", proxy.bound_port), timeout=2) as client,
    ):
        client.sendall(b"\x05\x01\x00")
        assert _recv_exact(client, 2) == b"\x05\x00"
        client.sendall(b"\x05\x01\x00\x09")

        assert _recv_exact(client, 2) == b"\x05\x08"


def test_socks5_destination_read_obeys_handshake_timeout() -> None:
    with (
        _running_proxy(handshake_timeout=0.05) as proxy,
        socket.create_connection(("127.0.0.1", proxy.bound_port), timeout=1) as client,
    ):
        client.sendall(b"\x05\x01\x00")
        assert _recv_exact(client, 2) == b"\x05\x00"
        client.sendall(b"\x05\x01\x00\x03\x05")

        assert _recv_exact(client, 2) == b"\x05\x06"


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_invalid_timeouts_are_rejected(timeout: float) -> None:
    with pytest.raises(ValueError, match="positive finite"):
        NativeProxyServer(connect_timeout=timeout)


def test_server_can_restart_after_bind_failure() -> None:
    blocker = socket.socket()
    blocker.bind(("127.0.0.1", 0))
    blocker.listen()
    port = blocker.getsockname()[1]
    server = NativeProxyServer(host="127.0.0.1", port=port)

    with pytest.raises(RuntimeError, match="Cannot start"):
        server.start()
    assert not server.is_running

    blocker.close()
    server.start()
    assert server.is_running
    assert server.stop()


def test_start_timeout_cannot_create_a_late_listener() -> None:
    server = NativeProxyServer(host="127.0.0.1", port=0)
    release_thread = threading.Event()
    original_thread_main = server._thread_main

    def delayed_thread_main() -> None:
        release_thread.wait(timeout=1)
        original_thread_main()

    server._thread_main = delayed_thread_main

    with pytest.raises(TimeoutError, match="Timed out"):
        server.start(timeout=0.01)

    release_thread.set()
    assert server._thread is not None
    server._thread.join(timeout=1)

    assert not server.is_running
    assert server.bound_port == 0
    assert server.stop()


def test_stop_closes_active_client_before_waiting_for_server() -> None:
    server = NativeProxyServer(host="127.0.0.1", port=0, handshake_timeout=60)
    server.start()
    client = socket.create_connection(("127.0.0.1", server.bound_port), timeout=2)
    stopped = False
    try:
        client.sendall(b"\x05")
        wait_step = threading.Event()
        for _ in range(100):
            if server._client_tasks:
                break
            wait_step.wait(0.01)
        assert server._client_tasks

        stopped = server.stop(timeout=2)
    finally:
        client.close()
        if not stopped:
            assert server.stop(timeout=2)

    assert stopped


def test_close_writer_aborts_a_stalled_transport() -> None:
    class StalledTransport:
        def __init__(self) -> None:
            self.aborted = False

        def abort(self) -> None:
            self.aborted = True

    class StalledWriter:
        def __init__(self) -> None:
            self.closed = False
            self.transport = StalledTransport()

        def close(self) -> None:
            self.closed = True

        async def wait_closed(self) -> None:
            await asyncio.Event().wait()

    writer = StalledWriter()

    async def run_test() -> None:
        await asyncio.wait_for(NativeProxyServer._close_writer(writer), timeout=1)

    asyncio.run(run_test())

    assert writer.closed
    assert writer.transport.aborted


def test_http_upgrade_headers_are_forwarded() -> None:
    server = NativeProxyServer()

    request = server._build_http_request(
        "GET",
        "/socket",
        "HTTP/1.1",
        [
            ("Host", "example.test"),
            ("Connection", "keep-alive, Upgrade"),
            ("Upgrade", "websocket"),
        ],
        None,
    )

    assert b"Upgrade: websocket\r\n" in request
    assert b"Connection: Upgrade\r\n" in request
    assert b"Connection: close\r\n" not in request


def test_http_upgrade_switches_to_bidirectional_relay() -> None:
    with (
        _running_tcp_server(_UpgradeEchoHandler) as (_, destination_port),
        _running_proxy() as proxy,
        socket.create_connection(("127.0.0.1", proxy.bound_port), timeout=2) as client,
    ):
        client.sendall(
            (
                f"GET http://127.0.0.1:{destination_port}/socket HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{destination_port}\r\n"
                "Connection: keep-alive, Upgrade\r\n"
                "Upgrade: websocket\r\n\r\n"
            ).encode()
        )
        response = _recv_until(client, b"\r\n\r\n")
        assert b"101 Switching Protocols" in response

        client.sendall(b"upgrade-echo")
        assert _recv_exact(client, len(b"upgrade-echo")) == b"upgrade-echo"


def test_tunnel_preserves_remote_half_close() -> None:
    while not _RemoteHalfCloseHandler.received.empty():
        _RemoteHalfCloseHandler.received.get_nowait()

    with (
        _running_tcp_server(_RemoteHalfCloseHandler) as (_, destination_port),
        _running_proxy() as proxy,
        socket.create_connection(("127.0.0.1", proxy.bound_port), timeout=2) as client,
    ):
        client.sendall(
            f"CONNECT 127.0.0.1:{destination_port} HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{destination_port}\r\n\r\n".encode()
        )
        assert b"200 Connection Established" in _recv_until(client, b"\r\n\r\n")
        assert _recv_exact(client, 5) == b"ready"
        assert client.recv(1) == b""

        client.sendall(b"after-remote-eof")
        client.shutdown(socket.SHUT_WR)
        assert _RemoteHalfCloseHandler.received.get(timeout=2) == b"after-remote-eof"


def test_absolute_http_target_replaces_mismatched_host_header() -> None:
    server = NativeProxyServer()
    headers = [("Host", "wrong.example")]
    host, port, path, _ = server._http_destination(
        "http://right.example/resource", headers
    )
    headers = server._replace_host_header(headers, host, port)

    request = server._build_http_request("GET", path, "HTTP/1.1", headers, None)

    assert b"Host: right.example\r\n" in request
    assert b"wrong.example" not in request


def test_socks5_upstream_rejects_auth_method_that_was_not_offered() -> None:
    class RecordingWriter:
        def __init__(self) -> None:
            self.data = bytearray()

        def write(self, data: bytes) -> None:
            self.data.extend(data)

        async def drain(self) -> None:
            pass

    async def run_test() -> None:
        server = NativeProxyServer()
        reader = asyncio.StreamReader()
        reader.feed_data(b"\x05\x02")
        reader.feed_eof()
        writer = RecordingWriter()

        with pytest.raises(ProxyProtocolError, match="not offered"):
            await server._socks5_connect(
                reader, writer, "example.com", 443, Upstream("upstream", "SOCKS5", "proxy", 1080)
            )
        assert writer.data == b"\x05\x01\x00"

    asyncio.run(run_test())


def test_socks5_upstream_rejects_incomplete_credentials() -> None:
    with pytest.raises(ValueError, match="both username and password"):
        Upstream("upstream", "SOCKS5", "proxy", 1080, "", "password")


def test_socks5_upstream_rejects_oversized_utf8_credentials() -> None:
    with pytest.raises(ValueError, match="255 UTF-8 bytes"):
        Upstream("upstream", "SOCKS5", "proxy", 1080, "user", "😀" * 100)


def test_connect_closes_remote_when_client_drops_during_success_reply() -> None:
    class ClientReader:
        async def readuntil(self, separator: bytes) -> bytes:
            return b"ONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n"

    class ClientWriter:
        def write(self, data: bytes) -> None:
            pass

        async def drain(self) -> None:
            raise ConnectionResetError("client disconnected")

    class RemoteWriter:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

        async def wait_closed(self) -> None:
            pass

    async def run_test() -> None:
        server = NativeProxyServer()
        remote_writer = RemoteWriter()
        server._open_tunnel = AsyncMock(return_value=(object(), remote_writer))

        with pytest.raises(ConnectionResetError):
            await server._handle_http(
                b"C",
                ClientReader(),
                ClientWriter(),
                Upstream.direct(),
            )
        assert remote_writer.closed

    asyncio.run(run_test())
