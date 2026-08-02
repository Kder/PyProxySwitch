#!/usr/bin/env python3

"""Tests for native_proxy.

    python -m unittest -v test_native_proxy

Every test in RegressionTests maps to a numbered finding from the review.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import socket
import struct
import sys
import threading
import time
import unittest
from unittest import mock

from pyproxyswitch import native_proxy
from pyproxyswitch.native_proxy import (
    ClientProtocolError,
    NativeProxyServer,
    ProxyPolicyError,
    ProxyProtocolError,
    Upstream,
    UpstreamProtocolError,
)

LOCAL = "127.0.0.1"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def parse_head(raw: bytes) -> tuple[str, dict[str, str]]:
    head = raw.split(b"\r\n\r\n", 1)[0].decode("latin-1")
    lines = head.split("\r\n")
    fields = {}
    for line in lines[1:]:
        name, _, value = line.partition(":")
        fields[name.lower().strip()] = value.strip()
    return lines[0], fields


async def read_until_eof(reader: asyncio.StreamReader, limit: float = 10.0) -> bytes:
    return await asyncio.wait_for(reader.read(-1), timeout=limit)


async def read_until_closed(reader: asyncio.StreamReader, limit: float = 10.0) -> bytes:
    """Collect bytes even when an early-response close ends with TCP RST."""

    async def collect() -> bytes:
        output = bytearray()
        try:
            while block := await reader.read(65536):
                output.extend(block)
        except ConnectionError:
            pass
        return bytes(output)

    return await asyncio.wait_for(collect(), timeout=limit)


async def relay_pair(a_reader, a_writer, b_reader, b_writer) -> None:
    async def pump(reader, writer):
        try:
            while True:
                data = await reader.read(65536)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            with contextlib.suppress(Exception):
                if writer.can_write_eof():
                    writer.write_eof()

    await asyncio.gather(pump(a_reader, b_writer), pump(b_reader, a_writer), return_exceptions=True)


class ProxyHarness(unittest.IsolatedAsyncioTestCase):
    """Runs origins/fake upstreams on the test loop and proxies on their own."""

    async def asyncSetUp(self) -> None:
        self._servers: list[asyncio.AbstractServer] = []
        self._proxies: list[NativeProxyServer] = []
        self._sockets: list[socket.socket] = []

    async def asyncTearDown(self) -> None:
        for proxy in self._proxies:
            await asyncio.to_thread(proxy.stop, 10.0)
        for server in self._servers:
            server.close()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(server.wait_closed(), 5.0)
        for sock in self._sockets:
            sock.close()

    async def serve(self, handler) -> int:
        async def guard(reader, writer):
            try:
                await handler(reader, writer)
            except (ConnectionError, asyncio.IncompleteReadError, asyncio.CancelledError):
                pass
            finally:
                with contextlib.suppress(Exception):
                    writer.close()

        server = await asyncio.start_server(guard, LOCAL, 0)
        self._servers.append(server)
        return int(server.sockets[0].getsockname()[1])

    async def start_proxy(self, **kwargs) -> NativeProxyServer:
        kwargs.setdefault("port", 0)
        proxy = NativeProxyServer(**kwargs)
        self._proxies.append(proxy)
        await asyncio.to_thread(proxy.start, 10.0)
        self.assertTrue(proxy.is_running)
        self.assertNotEqual(0, proxy.bound_port)
        return proxy

    async def connect(self, proxy: NativeProxyServer):
        return await asyncio.wait_for(asyncio.open_connection(LOCAL, proxy.bound_port), timeout=5.0)

    async def http_roundtrip(self, proxy: NativeProxyServer, raw: bytes) -> bytes:
        reader, writer = await self.connect(proxy)
        try:
            writer.write(raw)
            await writer.drain()
            return await read_until_eof(reader)
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

    async def http_roundtrip_eof(self, proxy: NativeProxyServer, raw: bytes) -> bytes:
        reader, writer = await self.connect(proxy)
        try:
            writer.write(raw)
            await writer.drain()
            writer.write_eof()
            return await read_until_eof(reader)
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

    async def wait_until(self, predicate, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            await asyncio.sleep(0.02)
        self.fail("condition not reached within timeout")

    # ---------------------------------------------------------------- origins
    def reflector(self, extra: int = 0):
        """Answers with the exact request bytes it received."""
        received: list[bytes] = []

        async def handler(reader, writer):
            payload = await reader.readuntil(b"\r\n\r\n")
            if extra:
                payload += await reader.readexactly(extra)
            received.append(payload)
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % len(payload)
                + payload
            )
            await writer.drain()
            writer.close()

        handler.received = received  # type: ignore[attr-defined]
        return handler

    def responder(self, response: bytes, *, hold: float = 0.0, read_head: bool = True):
        async def handler(reader, writer):
            if read_head:
                await reader.readuntil(b"\r\n\r\n")
            writer.write(response)
            await writer.drain()
            if hold:
                await asyncio.sleep(hold)
            writer.close()

        return handler

    async def echo_port(self) -> int:
        async def handler(reader, writer):
            while True:
                data = await reader.read(65536)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
            with contextlib.suppress(Exception):
                writer.write_eof()

        return await self.serve(handler)

    # ------------------------------------------------------------ fake proxies
    async def fake_http_proxy(self, record: list[bytes]) -> int:
        async def handler(reader, writer):
            head = await reader.readuntil(b"\r\n\r\n")
            record.append(head)
            line = head.split(b"\r\n", 1)[0].decode("latin-1")
            method, target, _ = line.split(" ")
            if method == "CONNECT":
                host, _, port = target.rpartition(":")
                upstream_reader, upstream_writer = await asyncio.open_connection(
                    host.strip("[]"), int(port)
                )
                writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                await writer.drain()
            else:
                from urllib.parse import urlsplit

                parsed = urlsplit(target)
                upstream_reader, upstream_writer = await asyncio.open_connection(
                    parsed.hostname, parsed.port or 80
                )
                upstream_writer.write(head)
                await upstream_writer.drain()
            try:
                await relay_pair(reader, writer, upstream_reader, upstream_writer)
            finally:
                upstream_writer.close()

        return await self.serve(handler)

    async def fake_socks5_proxy(
        self,
        record: list[tuple],
        *,
        require_auth: tuple[str, str] | None = None,
        bound_address: tuple[str, int] | None = None,
    ) -> int:
        async def handler(reader, writer):
            version, count = await reader.readexactly(2)
            methods = await reader.readexactly(count)
            if require_auth is not None:
                assert 2 in methods
                writer.write(b"\x05\x02")
                await writer.drain()
                await reader.readexactly(1)
                ulen = (await reader.readexactly(1))[0]
                user = await reader.readexactly(ulen)
                plen = (await reader.readexactly(1))[0]
                password = await reader.readexactly(plen)
                ok = (user.decode(), password.decode()) == require_auth
                writer.write(b"\x01" + (b"\x00" if ok else b"\x01"))
                await writer.drain()
                if not ok:
                    return
            else:
                writer.write(b"\x05\x00")
                await writer.drain()
            _, command, _, atype = await reader.readexactly(4)
            if atype == 1:
                host = socket.inet_ntoa(await reader.readexactly(4))
            elif atype == 3:
                size = (await reader.readexactly(1))[0]
                host = (await reader.readexactly(size)).decode("ascii")
            else:
                host = socket.inet_ntop(socket.AF_INET6, await reader.readexactly(16))
            port = struct.unpack(">H", await reader.readexactly(2))[0]
            record.append((command, atype, host, port))
            upstream_reader, upstream_writer = await asyncio.open_connection(host, port)
            bound_host, bound_port = bound_address or ("0.0.0.0", 0)
            writer.write(
                b"\x05\x00\x00\x01" + socket.inet_aton(bound_host) + struct.pack(">H", bound_port)
            )
            await writer.drain()
            try:
                await relay_pair(reader, writer, upstream_reader, upstream_writer)
            finally:
                upstream_writer.close()

        return await self.serve(handler)

    async def fake_socks4_proxy(
        self,
        record: list[tuple],
        *,
        bound_address: tuple[str, int] | None = None,
    ) -> int:
        async def handler(reader, writer):
            version, command = await reader.readexactly(2)
            port = struct.unpack(">H", await reader.readexactly(2))[0]
            raw = await reader.readexactly(4)
            user = await reader.readuntil(b"\x00")
            if raw[:3] == b"\x00\x00\x00" and raw[3]:
                host = (await reader.readuntil(b"\x00"))[:-1].decode("ascii")
            else:
                host = socket.inet_ntoa(raw)
            record.append((command, host, port, user[:-1]))
            upstream_reader, upstream_writer = await asyncio.open_connection(host, port)
            bound_host, bound_port = bound_address or ("0.0.0.0", 0)
            writer.write(b"\x00\x5a" + struct.pack(">H", bound_port) + socket.inet_aton(bound_host))
            await writer.drain()
            try:
                await relay_pair(reader, writer, upstream_reader, upstream_writer)
            finally:
                upstream_writer.close()

        return await self.serve(handler)

    # --------------------------------------------------------- socks clients
    async def socks5_open(
        self,
        proxy: NativeProxyServer,
        host: str,
        port: int,
        atype: int = 3,
        *,
        include_bound: bool = False,
    ):
        reader, writer = await self.connect(proxy)
        writer.write(b"\x05\x01\x00")
        await writer.drain()
        self.assertEqual(b"\x05\x00", await reader.readexactly(2))
        if atype == 3:
            encoded = host.encode("ascii")
            address = b"\x03" + bytes((len(encoded),)) + encoded
        elif atype == 1:
            address = b"\x01" + socket.inet_aton(host)
        else:
            address = b"\x04" + socket.inet_pton(socket.AF_INET6, host)
        writer.write(b"\x05\x01\x00" + address + struct.pack(">H", port))
        await writer.drain()
        head = await reader.readexactly(4)
        if head[3] == 1:
            bound_host = socket.inet_ntoa(await reader.readexactly(4))
        elif head[3] == 4:
            bound_host = socket.inet_ntop(socket.AF_INET6, await reader.readexactly(16))
        elif head[3] == 3:
            bound_host = (await reader.readexactly((await reader.readexactly(1))[0])).decode(
                "ascii"
            )
        else:
            self.fail(f"invalid SOCKS5 reply address type: {head[3]}")
        bound_port = struct.unpack(">H", await reader.readexactly(2))[0]
        if include_bound:
            return reader, writer, head[1], (bound_host, bound_port)
        return reader, writer, head[1]

    async def socks4_open(
        self,
        proxy: NativeProxyServer,
        host: str,
        port: int,
        *,
        include_bound: bool = False,
    ):
        reader, writer = await self.connect(proxy)
        writer.write(
            b"\x04\x01"
            + struct.pack(">H", port)
            + b"\x00\x00\x00\x01"
            + b"tester\x00"
            + host.encode("ascii")
            + b"\x00"
        )
        await writer.drain()
        reply = await reader.readexactly(8)
        if include_bound:
            return (
                reader,
                writer,
                reply[1],
                (
                    socket.inet_ntoa(reply[4:8]),
                    struct.unpack(">H", reply[2:4])[0],
                ),
            )
        return reader, writer, reply[1]


# --------------------------------------------------------------------------- #
# pure-unit tests
# --------------------------------------------------------------------------- #
class UpstreamValidationTests(unittest.TestCase):
    def test_direct_clears_address(self):
        upstream = Upstream(name="x", proxy_type="direct", host="ignored", port=8080)
        self.assertEqual(("DIRECT", "", 0), (upstream.proxy_type, upstream.host, upstream.port))

    def test_rejects_bad_input(self):
        cases = [
            {"name": "x", "proxy_type": "socks6", "host": "h", "port": 1},
            {"name": "x", "proxy_type": "HTTP", "host": "", "port": 1},
            {"name": "x", "proxy_type": "HTTP", "host": "h", "port": 0},
            {"name": "x", "proxy_type": "HTTP", "host": "h", "port": 65536},
            {"name": "x", "proxy_type": "HTTP", "host": "h", "port": 8080.5},
            {"name": "x", "proxy_type": "HTTP", "host": "bad host", "port": 80},
            {
                "name": "x",
                "proxy_type": "SOCKS5",
                "host": "h",
                "port": 1,
                "username": "u",
            },
            {
                "name": "x",
                "proxy_type": "SOCKS4",
                "host": "h",
                "port": 1,
                "username": "a\x00b",
            },
            {
                "name": "x",
                "proxy_type": "SOCKS4",
                "host": "h",
                "port": 1,
                "password": "unsupported",
            },
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                Upstream(**case)

    def test_string_port_accepted(self):
        self.assertEqual(8080, Upstream(name="x", proxy_type="HTTP", host="h", port="8080").port)

    def test_http_credentials_are_not_limited_by_socks5_frame_size(self):
        password = "😀" * 100

        upstream = Upstream(
            name="x",
            proxy_type="HTTP",
            host="h",
            port=8080,
            username="a" * 256,
            password=password,
        )

        self.assertEqual(password, upstream.password)


class PublicApiCompatibilityTests(unittest.TestCase):
    def test_legacy_constructor_parameters_remain_usable(self):
        upstream = Upstream.direct()
        server = NativeProxyServer(
            LOCAL,
            0,
            upstream,
            connect_timeout=1.0,
            handshake_timeout=1.0,
        )

        self.assertEqual(LOCAL, server.host)
        self.assertEqual(0, server.port)
        self.assertIs(upstream, server.upstream)

    def test_specialized_protocol_errors_preserve_base_exception_api(self):
        self.assertTrue(issubclass(ClientProtocolError, ProxyProtocolError))
        self.assertTrue(issubclass(UpstreamProtocolError, ProxyProtocolError))
        self.assertTrue(issubclass(ProxyPolicyError, ProxyProtocolError))


class RequestParsingTests(unittest.TestCase):
    @staticmethod
    def parse(raw: bytes):
        return NativeProxyServer._parse_http_request(raw)

    def test_minimal_request(self):
        request = self.parse(b"GET /a?b HTTP/1.1\r\nHost: h.example\r\n\r\n")
        self.assertEqual(
            ("GET", "origin", "h.example", 80),
            (
                request.method,
                request.target_form,
                request.destination.host,
                request.destination.port,
            ),
        )
        self.assertEqual("/a?b", request.destination.origin_form)
        self.assertEqual("http://h.example/a?b", request.destination.proxy_form)

    def test_leading_crlf_ignored(self):
        request = self.parse(b"\r\nGET / HTTP/1.1\r\nHost: h\r\n\r\n")
        self.assertEqual("GET", request.method)

    def test_request_line_is_strict(self):
        bad = [
            b"GET  / HTTP/1.1\r\nHost: h\r\n\r\n",
            b"GET\t/ HTTP/1.1\r\nHost: h\r\n\r\n",
            b"GET /\x0bx HTTP/1.1\r\nHost: h\r\n\r\n",
            b"GET / HTTP/2.0\r\nHost: h\r\n\r\n",
            b"GE T / HTTP/1.1\r\nHost: h\r\n\r\n",
            b"G\x00T / HTTP/1.1\r\nHost: h\r\n\r\n",
            b"GET / HTTP/1.1 extra\r\nHost: h\r\n\r\n",
        ]
        for raw in bad:
            with self.subTest(raw=raw), self.assertRaises(ProxyProtocolError):
                self.parse(raw)

    def test_header_field_rules(self):
        bad = [
            b"GET / HTTP/1.1\r\nHost : h\r\n\r\n",
            b"GET / HTTP/1.1\r\nHost: h\r\n\tfold\r\n\r\n",
            b"GET / HTTP/1.1\r\nHost: h\nX: y\r\n\r\n",
            b"GET / HTTP/1.1\r\nHost: h\r\nX: a\x7fb\r\n\r\n",
            b"GET / HTTP/1.1\r\nNo-Colon\r\n\r\n",
        ]
        for raw in bad:
            with self.subTest(raw=raw), self.assertRaises(ProxyProtocolError):
                self.parse(raw)

    def test_target_forms(self):
        self.assertEqual(
            "absolute", self.parse(b"GET http://h/x HTTP/1.1\r\nHost: other\r\n\r\n").target_form
        )
        self.assertEqual(
            "asterisk", self.parse(b"OPTIONS * HTTP/1.1\r\nHost: h\r\n\r\n").target_form
        )
        self.assertEqual(
            "authority", self.parse(b"CONNECT h:443 HTTP/1.1\r\nHost: h:443\r\n\r\n").target_form
        )
        for raw in (
            b"GET foo/bar HTTP/1.1\r\nHost: h\r\n\r\n",
            b"GET * HTTP/1.1\r\nHost: h\r\n\r\n",
            b"GET https://h/x HTTP/1.1\r\nHost: h\r\n\r\n",
            b"connect h:443 HTTP/1.1\r\nHost: h\r\n\r\n",
            b"GET / HTTP/1.1\r\n\r\n",
            b"GET / HTTP/1.1\r\nHost: a\r\nHost: b\r\n\r\n",
        ):
            with self.subTest(raw=raw), self.assertRaises(ProxyProtocolError):
                self.parse(raw)

    def test_asterisk_proxy_form_has_empty_path(self):
        request = self.parse(b"OPTIONS * HTTP/1.1\r\nHost: h:81\r\n\r\n")
        self.assertEqual("*", request.destination.origin_form)
        self.assertEqual("http://h:81", request.destination.proxy_form)

    def test_absolute_form_drops_userinfo_and_fragment(self):
        request = self.parse(b"GET http://u:p@h:80/x#frag HTTP/1.1\r\nHost: z\r\n\r\n")
        self.assertEqual("h", request.destination.host)
        self.assertEqual("/x", request.destination.origin_form)
        self.assertEqual("http://h/x", request.destination.proxy_form)

    def test_framing_validation(self):
        bad = [
            b"POST / HTTP/1.1\r\nHost: h\r\nContent-Length: 1\r\nTransfer-Encoding: chunked\r\n\r\n",
            b"POST / HTTP/1.1\r\nHost: h\r\nContent-Length: 1\r\nContent-Length: 2\r\n\r\n",
            b"POST / HTTP/1.1\r\nHost: h\r\nContent-Length: 0x10\r\n\r\n",
            b"POST / HTTP/1.1\r\nHost: h\r\nContent-Length: +1\r\n\r\n",
            b"POST / HTTP/1.1\r\nHost: h\r\nContent-Length: \xd9\xa5\r\n\r\n",
            b"POST / HTTP/1.1\r\nHost: h\r\nContent-Length: 99999999999999999999\r\n\r\n",
            b"POST / HTTP/1.1\r\nHost: h\r\nTransfer-Encoding: chunked, gzip\r\n\r\n",
            b"POST / HTTP/1.0\r\nHost: h\r\nTransfer-Encoding: chunked\r\n\r\n",
            b"POST / HTTP/1.1\r\nHost: h\r\nTransfer-Encoding: chunked\r\nTransfer-Encoding: chunked\r\n\r\n",
            b"CONNECT h:443 HTTP/1.1\r\nHost: h\r\nContent-Length: 5\r\n\r\n",
            b"CONNECT h:443 HTTP/1.1\r\nHost: h\r\nTransfer-Encoding: chunked\r\n\r\n",
            b"GET / HTTP/1.1\r\nHost: h\r\nConnection: upgrade\r\nUpgrade: ws\r\n"
            b"Transfer-Encoding: chunked\r\n\r\n",
        ]
        for raw in bad:
            with self.subTest(raw=raw), self.assertRaises(ClientProtocolError):
                self.parse(raw)

    def test_framing_normalisation(self):
        request = self.parse(
            b"POST / HTTP/1.1\r\nHost: h\r\nContent-Length: 007\r\nContent-Length: 7\r\n\r\n"
        )
        self.assertEqual(
            ("content-length", 7), (request.framing.mode, request.framing.content_length)
        )
        self.assertEqual((("Host", "h"), ("Content-Length", "7")), request.headers)

    def test_connect_with_zero_length_body_allowed(self):
        request = self.parse(b"CONNECT h:443 HTTP/1.1\r\nHost: h\r\nContent-Length: 0\r\n\r\n")
        self.assertFalse(request.framing.has_body)

    def test_upgrade_protocol_list_is_validated(self):
        request = self.parse(
            b"GET / HTTP/1.1\r\nHost: h\r\nConnection: Upgrade\r\n"
            b"Upgrade: WebSocket, IRC/6.9\r\nUpgrade: h2c\r\n\r\n"
        )
        self.assertTrue(request.is_upgrade)
        self.assertEqual(("WebSocket", "IRC/6.9", "h2c"), request.upgrade_protocols)

        for value in (b"", b"web socket", b"/1", b"websocket/", b"a/b/c", b"ws,"):
            with self.subTest(value=value), self.assertRaises(ClientProtocolError):
                self.parse(
                    b"GET / HTTP/1.1\r\nHost: h\r\nConnection: Upgrade\r\n"
                    + b"Upgrade: "
                    + value
                    + b"\r\n\r\n"
                )

        ignored = self.parse(
            b"GET / HTTP/1.0\r\nHost: h\r\nConnection: Upgrade\r\n" b"Upgrade: websocket\r\n\r\n"
        )
        self.assertFalse(ignored.is_upgrade)


class AuthorityTests(unittest.TestCase):
    def test_valid(self):
        cases = {
            ("h.example", 80): "h.example",
            ("h.example", 8080): "h.example:8080",
            ("::1", 80): "[::1]",
            ("::1", 8080): "[::1]:8080",
            ("2001:db8::1", 80): "2001:db8::1",
            ("10.0.0.1", 443): "10.0.0.1:443",
            ("under_score.test", 80): "under_score.test",
            ("trailing.dot.", 80): "trailing.dot.",
        }
        for expected, text in cases.items():
            with self.subTest(text=text):
                self.assertEqual(expected, NativeProxyServer._parse_authority(text, 80))

    def test_invalid(self):
        for text in (
            "h:+80",
            "h:8_0",
            "h:١٢",
            "h:0",
            "h:65536",
            "h:",
            "h: 80",
            "",
            "[::1",
            "[]:80",
            "[nothex]:80",
            "h/x:80",
            "u@h:80",
            "h\x00:80",
            "a:b:c",
            "x" * 300,
        ):
            with self.subTest(text=text), self.assertRaises(ProxyProtocolError):
                NativeProxyServer._parse_authority(text, 80)

    def test_host_charset(self):
        for host in ("a b", "a/b", "é.example", "a" * 64 + ".example", "..", "a..b"):
            with self.subTest(host=host), self.assertRaises(ProxyProtocolError):
                native_proxy._validate_destination_host(host)


class RewriteTests(unittest.TestCase):
    def build(self, raw: bytes, *, upstream: Upstream | None = None) -> bytes:
        request = NativeProxyServer._parse_http_request(raw)
        headers = NativeProxyServer._replace_host_header(
            request.headers, request.destination.host, request.destination.port
        )
        target = request.destination.proxy_form if upstream else request.destination.origin_form
        return NativeProxyServer._build_http_request(
            NativeProxyServer(port=0), request, target, headers, upstream
        )

    def test_hop_by_hop_and_connection_tokens_removed(self):
        out = self.build(
            b"GET http://h.example/x HTTP/1.1\r\n"
            b"Host: wrong\r\n"
            b"Proxy-Connection: keep-alive\r\n"
            b"Proxy-Authorization: Basic zzz\r\n"
            b"TE: gzip\r\n"
            b"Connection: keep-alive, X-Drop\r\n"
            b"X-Drop: 1\r\n"
            b"X-Keep: 1\r\n\r\n"
        )
        self.assertEqual(
            b"GET /x HTTP/1.1\r\nHost: h.example\r\nX-Keep: 1\r\nConnection: close\r\n\r\n",
            out,
        )

    def test_framing_fields_survive_hostile_connection_option(self):
        out = self.build(
            b"POST / HTTP/1.1\r\nHost: h\r\n"
            b"Connection: Content-Length, Host, Transfer-Encoding, Trailer\r\n"
            b"Content-Length: 3\r\n\r\n"
        )
        self.assertIn(b"Content-Length: 3\r\n", out)
        self.assertIn(b"Host: h\r\n", out)

    def test_upgrade_is_recreated(self):
        out = self.build(
            b"GET / HTTP/1.1\r\nHost: h\r\nConnection: Upgrade\r\nUpgrade: websocket\r\n\r\n"
        )
        self.assertIn(b"Upgrade: websocket\r\n", out)
        self.assertTrue(out.endswith(b"Connection: Upgrade\r\n\r\n"))

    def test_http_upstream_gets_absolute_form_and_auth(self):
        upstream = Upstream(
            name="u",
            proxy_type="HTTP",
            host="127.0.0.1",
            port=3128,
            username="user",
            password="pw",
        )
        out = self.build(
            b"GET http://h.example/x HTTP/1.1\r\nHost: h.example\r\n\r\n", upstream=upstream
        )
        expected = base64.b64encode(b"user:pw").decode()
        self.assertTrue(out.startswith(b"GET http://h.example/x HTTP/1.1\r\n"))
        self.assertIn(f"Proxy-Authorization: Basic {expected}\r\n".encode(), out)

    def test_response_head_is_sanitised(self):
        out = NativeProxyServer._build_http_response(
            "HTTP/1.1",
            200,
            "OK",
            (
                ("Content-Length", "5"),
                ("Transfer-Encoding", "chunked"),
                ("Keep-Alive", "timeout=5"),
                ("Proxy-Authenticate", "Basic"),
                ("Connection", "keep-alive, X-Hop"),
                ("X-Hop", "1"),
                ("X-Keep", "1"),
            ),
            "close",
        )
        line, fields = parse_head(out)
        self.assertEqual("HTTP/1.1 200 OK", line)
        self.assertEqual({"transfer-encoding", "x-keep", "connection"}, set(fields))
        self.assertEqual("close", fields["connection"])

    def test_response_head_keeps_upgrade_for_101(self):
        out = NativeProxyServer._build_http_response(
            "HTTP/1.1",
            101,
            "Switching Protocols",
            (("Upgrade", "websocket"), ("Connection", "Upgrade")),
            "Upgrade",
        )
        _, fields = parse_head(out)
        self.assertEqual({"upgrade": "websocket", "connection": "Upgrade"}, fields)

    def test_bodyless_status_strips_framing_fields(self):
        for status in (100, 101, 204):
            with self.subTest(status=status):
                out = NativeProxyServer._build_http_response(
                    "HTTP/1.1",
                    status,
                    "Test",
                    (
                        ("Content-Length", "0"),
                        ("Transfer-Encoding", "chunked"),
                        ("Upgrade", "websocket"),
                    ),
                    None,
                )
                _, fields = parse_head(out)
                self.assertNotIn("content-length", fields)
                self.assertNotIn("transfer-encoding", fields)

    def test_status_line_without_reason(self):
        version, status, reason, headers = NativeProxyServer._parse_http_response_header(
            b"HTTP/1.1 204\r\n\r\n"
        )
        self.assertEqual(("HTTP/1.1", 204, "", ()), (version, status, reason, headers))

    def test_bad_status_lines(self):
        for raw in (
            b"HTTP/1.1  200 OK\r\n\r\n",
            b"HTTP/2 200 OK\r\n\r\n",
            b"HTTP/1.1 20 OK\r\n\r\n",
            b"HTTP/1.1 abc OK\r\n\r\n",
            b"HTTP/1.1 200 O\x00K\r\n\r\n",
        ):
            with self.subTest(raw=raw), self.assertRaises(UpstreamProtocolError):
                NativeProxyServer._parse_http_response_header(raw)


class ChunkTests(unittest.TestCase):
    def test_valid_sizes(self):
        cases = {
            b"0": 0,
            b"a": 10,
            b"00A": 10,
            b"1f;name": 31,
            b"1f ; name = value": 31,
            b'5;n="q\\"s"': 5,
            b"f" * 16: (1 << 64) - 1 if False else int(b"f" * 16, 16),
        }
        for line, expected in cases.items():
            with self.subTest(line=line):
                if expected > native_proxy._MAX_HTTP_BODY_LENGTH:
                    with self.assertRaises(ClientProtocolError):
                        NativeProxyServer._parse_http_chunk_size(line)
                else:
                    self.assertEqual(expected, NativeProxyServer._parse_http_chunk_size(line))

    def test_invalid_sizes(self):
        for line in (
            b"",
            b"5 ",
            b" 5",
            b"0x5",
            b"5\r",
            b"-1",
            b"g",
            b"5;",
            b"5;=v",
            b"5;n=",
            b'5;n="unterminated',
            b"1" * 17,
        ):
            with self.subTest(line=line), self.assertRaises(ClientProtocolError):
                NativeProxyServer._parse_http_chunk_size(line)


class Socks5MappingTests(unittest.TestCase):
    def test_reply_codes(self):
        cases = [
            (ProxyPolicyError("no"), 2),
            (TimeoutError(), 6),
            (socket.gaierror(-2, "name"), 4),
            (ConnectionRefusedError(native_proxy.errno.ECONNREFUSED, "x"), 5),
            (OSError(native_proxy.errno.ENETUNREACH, "x"), 3),
            (OSError(native_proxy.errno.EHOSTUNREACH, "x"), 4),
            (ProxyProtocolError("bad"), 1),
        ]
        for exc, expected in cases:
            with self.subTest(exc=exc):
                self.assertEqual(expected, NativeProxyServer._socks5_reply_for(exc))


# --------------------------------------------------------------------------- #
# lifecycle
# --------------------------------------------------------------------------- #
class LifecycleTests(unittest.TestCase):
    def test_windows_selector_caps_connection_limit(self):
        with (
            mock.patch.object(native_proxy, "_uses_windows_selector_event_loop", return_value=True),
            self.assertLogs("PyProxySwitch", level="WARNING") as logs,
        ):
            proxy = NativeProxyServer(port=0)

        self.assertEqual(200, proxy.max_connections)
        self.assertIn("Capping max_connections from 512 to 200", "\n".join(logs.output))

    @unittest.skipUnless(
        sys.platform == "win32" and sys.version_info[:2] == (3, 14),
        "Windows Python 3.14-specific event loop workaround",
    )
    def test_windows_python_314_uses_selector_event_loop(self):
        proxy = NativeProxyServer(port=0)
        try:
            proxy.start(timeout=10)
            self.assertIsInstance(proxy._loop, asyncio.SelectorEventLoop)
        finally:
            proxy.stop(timeout=10)

    def test_start_stop_cycles(self):
        proxy = NativeProxyServer(port=0)
        try:
            for _ in range(5):
                proxy.start(timeout=10)
                self.assertTrue(proxy.is_running)
                self.assertNotEqual(0, proxy.bound_port)
                self.assertTrue(proxy.stop(timeout=10))
                self.assertFalse(proxy.is_running)
                self.assertEqual(0, proxy.bound_port)
        finally:
            proxy.stop(timeout=10)

    def test_stop_before_start_is_noop(self):
        self.assertTrue(NativeProxyServer(port=0).stop())

    def test_bind_failure_is_reported(self):
        blocker = socket.socket()
        blocker.bind((LOCAL, 0))
        blocker.listen(1)
        try:
            proxy = NativeProxyServer(port=blocker.getsockname()[1])
            with self.assertRaises(RuntimeError):
                proxy.start(timeout=10)
            self.assertFalse(proxy.is_running)
        finally:
            blocker.close()

    def test_start_requires_a_bound_listener(self):
        """Regression #5: a loop that exits before binding must not look healthy."""

        class Stillborn(NativeProxyServer):
            async def _run_server(self) -> None:
                self._loop = asyncio.get_running_loop()
                self._stop_event = asyncio.Event()
                return

        proxy = Stillborn(port=0)
        with self.assertRaises(RuntimeError):
            proxy.start(timeout=10)
        self.assertFalse(proxy.is_running)

    def test_concurrent_start_stop(self):
        proxy = NativeProxyServer(port=0)
        failures: list[BaseException] = []
        thread_name = "PyProxySwitch-native-proxy"
        baseline = sum(thread.name == thread_name for thread in threading.enumerate())

        def worker():
            for _ in range(10):
                try:
                    proxy.start(timeout=10)
                except (RuntimeError, TimeoutError):
                    pass  # a racing thread owns the transition
                except BaseException as exc:  # noqa: BLE001
                    failures.append(exc)
                proxy.stop(timeout=10)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(60)
            self.assertFalse(thread.is_alive(), "lifecycle worker did not finish")
        self.assertEqual([], failures)
        self.assertTrue(proxy.stop(timeout=10))
        self.assertFalse(proxy.is_running)
        deadline = time.monotonic() + 5
        while (
            sum(thread.name == thread_name for thread in threading.enumerate()) > baseline
            and time.monotonic() < deadline
        ):
            time.sleep(0.05)
        self.assertLessEqual(
            sum(thread.name == thread_name for thread in threading.enumerate()), baseline
        )

    def test_non_loopback_bind_requires_opt_in(self):
        for host in ("0.0.0.0", "::", "192.0.2.1", ""):
            with self.subTest(host=host), self.assertRaises(ValueError):
                NativeProxyServer(host=host, port=0)
        NativeProxyServer(host="0.0.0.0", port=0, allow_remote_clients=True)

    def test_option_validation(self):
        for kwargs in (
            {"connect_timeout": 0},
            {"handshake_timeout": float("nan")},
            {"idle_timeout": -1},
            {"max_connections": 0},
            {"port": 70000},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                options = {"port": 0}
                options.update(kwargs)
                NativeProxyServer(**options)
        with self.assertRaises(TypeError):
            NativeProxyServer(port=0, destination_policy="nope")


# --------------------------------------------------------------------------- #
# end to end
# --------------------------------------------------------------------------- #
class HttpForwardTests(ProxyHarness):
    async def test_direct_get_rewrites_head(self):
        handler = self.reflector()
        origin = await self.serve(handler)
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(
            proxy,
            f"GET http://{LOCAL}:{origin}/x?y=1 HTTP/1.1\r\n".encode()
            + b"Host: wrong.example\r\nProxy-Connection: keep-alive\r\n"
            b"Connection: keep-alive, X-Drop\r\nX-Drop: yes\r\nX-Keep: yes\r\n\r\n",
        )
        self.assertIn(b"200 OK", raw.split(b"\r\n", 1)[0])
        self.assertEqual(
            f"GET /x?y=1 HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode()
            + b"X-Keep: yes\r\nConnection: close\r\n\r\n",
            handler.received[0],
        )

    async def test_content_length_body_is_forwarded(self):
        handler = self.reflector(extra=7)
        origin = await self.serve(handler)
        proxy = await self.start_proxy()
        await self.http_roundtrip(
            proxy,
            f"POST /u HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode()
            + b"Content-Length: 007\r\n\r\nabcdefg",
        )
        self.assertTrue(handler.received[0].endswith(b"abcdefg"))
        self.assertIn(b"Content-Length: 7\r\n", handler.received[0])

    async def test_chunked_body_and_trailers_are_forwarded(self):
        body = b"5\r\nhello\r\n0\r\nX-Sum: 5\r\n\r\n"
        handler = self.reflector(extra=len(body))
        origin = await self.serve(handler)
        proxy = await self.start_proxy()
        await self.http_roundtrip(
            proxy,
            f"POST /u HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode()
            + b"Transfer-Encoding: chunked\r\nTrailer: X-Sum\r\n\r\n"
            + body,
        )
        head, _, forwarded = handler.received[0].partition(b"\r\n\r\n")
        self.assertEqual(body, forwarded)
        self.assertIn(b"Transfer-Encoding: chunked\r\n", head)
        self.assertIn(b"Trailer: X-Sum\r\n", head)

    async def test_early_rejection_during_chunked_upload_never_drops_client(self):
        """A server that rejects a chunked upload early and closes must not
        leave the client with a silent reset: it either relays the early
        response or synthesizes a gateway error."""

        async def handler(reader, writer):
            await reader.readuntil(b"\r\n\r\n")
            await reader.read(256)  # consume part of the upload, then reject
            writer.write(
                b"HTTP/1.1 413 Payload Too Large\r\n"
                b"Content-Length: 6\r\nConnection: close\r\n\r\n"
                b"denied"
            )
            await writer.drain()
            writer.close()

        origin = await self.serve(handler)
        proxy = await self.start_proxy()
        chunk = b"4000\r\n" + (b"x" * 0x4000) + b"\r\n"
        request = (
            f"POST / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode()
            + b"Transfer-Encoding: chunked\r\n\r\n"
            + chunk * 64
            + b"0\r\n\r\n"
        )

        # The proxy uploads concurrently with relaying the early response.
        # Repeat so the scheduling race is exercised on every platform; the
        # client must always receive an HTTP response, never zero bytes.
        for _ in range(8):
            reader, writer = await self.connect(proxy)
            try:
                writer.write(request)
                with contextlib.suppress(ConnectionError):
                    await writer.drain()
                raw = await read_until_closed(reader)
                self.assertTrue(
                    raw.startswith(b"HTTP/1.1 413 ") or raw.startswith(b"HTTP/1.1 502 "),
                    raw[:80],
                )
            finally:
                writer.close()

    async def test_upload_reset_waits_for_inflight_early_response(self):
        """A write-side upload failure must not cancel an early response that
        the upstream has already started sending."""

        proxy = NativeProxyServer(LOCAL, 0, Upstream.direct(), idle_timeout=30.0)
        response_relayed = asyncio.Event()
        relayed = False

        class EofReader:
            """Stand-in for the client reader: the upload is mocked to fail
            before any body is consumed, so draining sees an immediate EOF."""

            async def read(self, size: int = -1) -> bytes:
                return b""

        async def failing_upload(*_args, **_kwargs):
            raise ConnectionResetError("upstream closed during upload")

        async def slow_response(*_args, **_kwargs):
            nonlocal relayed
            await response_relayed.wait()
            relayed = True
            return False

        with (
            mock.patch.object(proxy, "_forward_http_body", failing_upload),
            mock.patch.object(proxy, "_forward_http_response", slow_response),
        ):
            task = asyncio.create_task(
                proxy._relay_http_request(
                    client_reader=EofReader(),
                    client_writer=None,
                    remote_reader=None,
                    remote_writer=None,
                    request_method="POST",
                    framing=native_proxy._HttpBodyFraming("chunked"),
                    progress=native_proxy._ResponseProgress(),
                )
            )
            await asyncio.sleep(0.05)
            self.assertFalse(task.done(), "early response was cancelled by the upload reset")
            response_relayed.set()
            await asyncio.wait_for(task, 2.0)
            self.assertTrue(relayed)

    async def test_pipelined_second_request_is_not_forwarded(self):
        received: list[bytes] = []

        async def handler(reader, writer):
            first = await reader.readuntil(b"\r\n\r\n")
            first += await reader.readexactly(3)
            try:
                extra = await asyncio.wait_for(reader.read(4096), 0.2)
            except TimeoutError:
                extra = b""
            received.append(first + extra)
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok")
            await writer.drain()
            writer.close()

        origin = await self.serve(handler)
        proxy = await self.start_proxy()
        reader, writer = await self.connect(proxy)
        writer.write(
            f"POST /one HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode()
            + b"Content-Length: 3\r\n\r\none"
            + f"GET /smuggled HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode(),
        )
        await writer.drain()
        head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 2.0)
        self.assertTrue(head.startswith(b"HTTP/1.1 200 "), head[:80])
        self.assertEqual(b"ok", await asyncio.wait_for(reader.readexactly(2), 2.0))
        writer.close()
        self.assertEqual(1, len(received))
        self.assertTrue(received[0].endswith(b"\r\n\r\none"))
        self.assertNotIn(b"/smuggled", received[0])

    async def test_cl_te_smuggling_is_rejected_before_origin_connect(self):
        accepted = 0

        async def handler(reader, writer):
            nonlocal accepted
            accepted += 1

        origin = await self.serve(handler)
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(
            proxy,
            f"POST / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode()
            + b"Content-Length: 4\r\nTransfer-Encoding: chunked\r\n\r\n",
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 400 "), raw[:80])
        await asyncio.sleep(0.05)
        self.assertEqual(0, accepted)

    async def test_truncated_content_length_gets_400(self):
        origin = await self.serve(self.responder(b"", hold=5.0))
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip_eof(
            proxy,
            f"POST / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode()
            + b"Content-Length: 5\r\n\r\nabc",
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 400 "), raw[:80])

    async def test_truncated_chunk_gets_400(self):
        origin = await self.serve(self.responder(b"", hold=5.0))
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip_eof(
            proxy,
            f"POST / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode()
            + b"Transfer-Encoding: chunked\r\n\r\n5\r\nabc",
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 400 "), raw[:80])

    async def test_forbidden_trailer_is_rejected(self):
        origin = await self.serve(self.responder(b"", hold=5.0))
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(
            proxy,
            f"POST /u HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode()
            + b"Transfer-Encoding: chunked\r\n\r\n0\r\nTransfer-Encoding: chunked\r\n\r\n",
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 400 "), raw[:40])

    async def test_expect_100_continue(self):
        async def handler(reader, writer):
            await reader.readuntil(b"\r\n\r\n")
            writer.write(b"HTTP/1.1 100 Continue\r\n\r\n")
            await writer.drain()
            body = await reader.readexactly(4)
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n" % len(body) + body)
            await writer.drain()
            writer.close()

        origin = await self.serve(handler)
        proxy = await self.start_proxy()
        reader, writer = await self.connect(proxy)
        writer.write(
            f"POST / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode()
            + b"Content-Length: 4\r\nExpect: 100-continue\r\n\r\n"
        )
        await writer.drain()
        interim = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5)
        self.assertIn(b"100 Continue", interim)
        writer.write(b"ping")
        await writer.drain()
        rest = await read_until_eof(reader)
        self.assertTrue(rest.endswith(b"ping"))
        writer.close()

    async def test_options_asterisk_goes_direct_as_asterisk(self):
        handler = self.reflector()
        origin = await self.serve(handler)
        proxy = await self.start_proxy()
        await self.http_roundtrip(
            proxy, f"OPTIONS * HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode()
        )
        self.assertTrue(handler.received[0].startswith(b"OPTIONS * HTTP/1.1\r\n"))

    async def test_bad_request_gets_400(self):
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(proxy, b"GET / HTTP/1.1\r\n\r\n")
        self.assertTrue(raw.startswith(b"HTTP/1.1 400 "))

    async def test_unreachable_origin_gets_502(self):
        proxy = await self.start_proxy()
        closed = socket.socket()
        closed.bind((LOCAL, 0))
        dead_port = closed.getsockname()[1]
        closed.close()
        raw = await self.http_roundtrip(
            proxy, f"GET http://{LOCAL}:{dead_port}/ HTTP/1.1\r\nHost: x\r\n\r\n".encode()
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 502 "))


class ResponseSanitationTests(ProxyHarness):
    async def test_keep_alive_response_is_closed(self):
        """Regression #6: never let a client believe the connection is reusable."""
        origin = await self.serve(
            self.responder(
                b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: keep-alive\r\n"
                b"Keep-Alive: timeout=5\r\nProxy-Authenticate: Basic\r\n\r\nok"
            )
        )
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(
            proxy, f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode()
        )
        line, fields = parse_head(raw)
        self.assertEqual("HTTP/1.1 200 OK", line)
        self.assertEqual("close", fields["connection"])
        self.assertNotIn("keep-alive", fields)
        self.assertNotIn("proxy-authenticate", fields)
        self.assertTrue(raw.endswith(b"ok"))

    async def test_content_length_boundary_releases_kept_alive_origin(self):
        upstream_closed = asyncio.Event()

        async def handler(reader, writer):
            await reader.readuntil(b"\r\n\r\n")
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n" b"Connection: keep-alive\r\n\r\nok"
            )
            await writer.drain()
            await reader.read()
            upstream_closed.set()

        origin = await self.serve(handler)
        proxy = await self.start_proxy(idle_timeout=5.0)
        raw = await asyncio.wait_for(
            self.http_roundtrip(
                proxy, f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode()
            ),
            2.0,
        )
        self.assertTrue(raw.endswith(b"ok"))
        await self.wait_until(lambda: proxy.active_connections == 0, timeout=2.0)
        await asyncio.wait_for(upstream_closed.wait(), 2.0)

    async def test_slow_content_length_stream_refreshes_idle_timeout(self):
        async def handler(reader, writer):
            await reader.readuntil(b"\r\n\r\n")
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\n")
            await writer.drain()
            for value in range(12):
                writer.write(bytes((value,)))
                await writer.drain()
                await asyncio.sleep(0.05)

        origin = await self.serve(handler)
        proxy = await self.start_proxy(idle_timeout=0.2)
        raw = await asyncio.wait_for(
            self.http_roundtrip(
                proxy, f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode()
            ),
            2.0,
        )
        self.assertTrue(raw.endswith(bytes(range(12))), raw[-20:])

    async def test_chunked_boundary_releases_kept_alive_origin(self):
        upstream_closed = asyncio.Event()

        async def handler(reader, writer):
            await reader.readuntil(b"\r\n\r\n")
            writer.write(
                b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n"
                b"Connection: keep-alive\r\n\r\n2\r\nok\r\n0\r\nX-End: yes\r\n\r\n"
            )
            await writer.drain()
            await reader.read()
            upstream_closed.set()

        origin = await self.serve(handler)
        proxy = await self.start_proxy(idle_timeout=5.0)
        raw = await asyncio.wait_for(
            self.http_roundtrip(
                proxy, f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode()
            ),
            2.0,
        )
        self.assertTrue(raw.endswith(b"2\r\nok\r\n0\r\nX-End: yes\r\n\r\n"))
        await self.wait_until(lambda: proxy.active_connections == 0, timeout=2.0)
        await asyncio.wait_for(upstream_closed.wait(), 2.0)

    async def test_unframed_response_falls_back_to_eof(self):
        origin = await self.serve(self.responder(b"HTTP/1.0 200 OK\r\n\r\nclose-delimited"))
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(
            proxy, f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode()
        )
        self.assertTrue(raw.endswith(b"close-delimited"))

    async def test_head_and_status_without_body_do_not_wait_for_eof(self):
        for method, status in (("HEAD", 200), ("GET", 204), ("GET", 304)):
            with self.subTest(method=method, status=status):
                upstream_closed = asyncio.Event()

                async def handler(
                    reader,
                    writer,
                    status=status,
                    upstream_closed=upstream_closed,
                ):
                    await reader.readuntil(b"\r\n\r\n")
                    writer.write(f"HTTP/1.1 {status} Test\r\nContent-Length: 9\r\n\r\n".encode())
                    await writer.drain()
                    await reader.read()
                    upstream_closed.set()

                origin = await self.serve(handler)
                proxy = await self.start_proxy(idle_timeout=5.0)
                raw = await asyncio.wait_for(
                    self.http_roundtrip(
                        proxy,
                        f"{method} / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode(),
                    ),
                    2.0,
                )
                self.assertTrue(raw.endswith(b"\r\n\r\n"), raw[-40:])
                await self.wait_until(
                    lambda proxy=proxy: proxy.active_connections == 0,
                    timeout=2.0,
                )
                await asyncio.wait_for(upstream_closed.wait(), 2.0)

    async def test_response_bytes_after_content_length_are_not_forwarded(self):
        origin = await self.serve(
            self.responder(
                b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n"
                b"okHTTP/1.1 200 Smuggled\r\nContent-Length: 3\r\n\r\nbad",
                hold=5.0,
            )
        )
        proxy = await self.start_proxy(idle_timeout=5.0)
        raw = await asyncio.wait_for(
            self.http_roundtrip(
                proxy, f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode()
            ),
            2.0,
        )
        self.assertTrue(raw.endswith(b"\r\n\r\nok"), raw[-80:])
        self.assertNotIn(b"Smuggled", raw)

    async def test_identical_response_content_lengths_are_normalized(self):
        origin = await self.serve(
            self.responder(
                b"HTTP/1.1 200 OK\r\nContent-Length: 02\r\n" b"Content-Length: 2\r\n\r\nok"
            )
        )
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(
            proxy, f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode()
        )
        self.assertEqual(1, raw.count(b"Content-Length: 2\r\n"))
        self.assertTrue(raw.endswith(b"ok"))

    async def test_conflicting_response_content_lengths_get_502(self):
        origin = await self.serve(
            self.responder(
                b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n" b"Content-Length: 3\r\n\r\nok!"
            )
        )
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(
            proxy, f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode()
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 502 "), raw[:80])

    async def test_content_length_transfer_encoding_conflict_gets_502(self):
        origin = await self.serve(
            self.responder(
                b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nTransfer-Encoding: chunked\r\n\r\n"
                b"2\r\nok\r\n0\r\n\r\n"
            )
        )
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(
            proxy, f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode()
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 502 "), raw[:80])

    async def test_duplicate_response_transfer_encoding_gets_502(self):
        origin = await self.serve(
            self.responder(
                b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n"
                b"Transfer-Encoding: chunked\r\n\r\n0\r\n\r\n"
            )
        )
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(
            proxy, f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode()
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 502 "), raw[:80])

    async def test_upstream_response_timeout_gets_504(self):
        async def handler(reader, writer):
            await reader.readuntil(b"\r\n\r\n")
            await reader.read()

        origin = await self.serve(handler)
        proxy = await self.start_proxy(idle_timeout=0.2)
        raw = await self.http_roundtrip(
            proxy, f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode()
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 504 "), raw[:80])

    async def test_request_body_timeout_gets_408(self):
        async def handler(reader, writer):
            await reader.readuntil(b"\r\n\r\n")
            await reader.read()

        origin = await self.serve(handler)
        proxy = await self.start_proxy(idle_timeout=0.2)
        reader, writer = await self.connect(proxy)
        writer.write(
            f"POST / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode() + b"Content-Length: 4\r\n\r\n"
        )
        await writer.drain()
        raw = await read_until_eof(reader, limit=2.0)
        self.assertTrue(raw.startswith(b"HTTP/1.1 408 "), raw[:80])
        writer.close()

    async def test_garbage_response_gets_502(self):
        origin = await self.serve(self.responder(b"NOT-HTTP\r\n\r\n"))
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(
            proxy, f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode()
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 502 "))

    async def test_interim_responses_are_capped(self):
        flood = b"HTTP/1.1 100 Continue\r\n\r\n" * (native_proxy._MAX_INTERIM_RESPONSES + 4)
        origin = await self.serve(self.responder(flood, hold=5.0))
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(
            proxy, f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode()
        )
        self.assertEqual(native_proxy._MAX_INTERIM_RESPONSES, raw.count(b"100 Continue"))
        self.assertIn(b"HTTP/1.1 502 Bad Gateway\r\n", raw)

    async def test_interim_response_allows_final_request_error(self):
        async def handler(reader, writer):
            await reader.readuntil(b"\r\n\r\n")
            writer.write(
                b"HTTP/1.1 100 Continue\r\n"
                b"Content-Length: 0\r\nTransfer-Encoding: chunked\r\n\r\n"
            )
            await writer.drain()
            await reader.read()

        origin = await self.serve(handler)
        proxy = await self.start_proxy(idle_timeout=1.0)
        reader, writer = await self.connect(proxy)
        writer.write(
            f"POST / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode()
            + b"Expect: 100-continue\r\nTransfer-Encoding: chunked\r\n\r\n"
        )
        await writer.drain()
        interim = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 2.0)
        _, fields = parse_head(interim)
        self.assertNotIn("content-length", fields)
        self.assertNotIn("transfer-encoding", fields)

        writer.write(b"1\r\nxXX")
        await writer.drain()
        final = await read_until_eof(reader, limit=2.0)
        self.assertTrue(final.startswith(b"HTTP/1.1 400 Bad Request\r\n"), final[:80])
        writer.close()

    async def test_partial_response_chunk_terminator_times_out(self):
        upstream_closed = asyncio.Event()

        async def handler(reader, writer):
            await reader.readuntil(b"\r\n\r\n")
            writer.write(b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n" b"1\r\nx\r")
            await writer.drain()
            await reader.read()
            upstream_closed.set()

        origin = await self.serve(handler)
        proxy = await self.start_proxy(idle_timeout=0.2)
        raw = await asyncio.wait_for(
            self.http_roundtrip(
                proxy, f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode()
            ),
            2.0,
        )
        self.assertIn(b"1\r\nx", raw)
        await self.wait_until(lambda: proxy.active_connections == 0, timeout=1.0)
        await asyncio.wait_for(upstream_closed.wait(), 1.0)

    async def test_stalled_response_drain_releases_connection(self):
        response_size = 64 * 1024 * 1024

        async def handler(reader, writer):
            await reader.readuntil(b"\r\n\r\n")
            writer.write(f"HTTP/1.1 200 OK\r\nContent-Length: {response_size}\r\n\r\n".encode())
            block = b"x" * 65536
            for _ in range(response_size // len(block)):
                writer.write(block)
                await writer.drain()

        origin = await self.serve(handler)
        proxy = await self.start_proxy(idle_timeout=0.2)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sockets.append(sock)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        sock.setblocking(False)
        await asyncio.get_running_loop().sock_connect(sock, (LOCAL, proxy.bound_port))
        reader, writer = await asyncio.open_connection(sock=sock)
        writer.write(f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode())
        await writer.drain()
        await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 2.0)

        await self.wait_until(lambda: proxy.active_connections == 0, timeout=3.0)
        writer.close()


class UpgradeTests(ProxyHarness):
    async def test_websocket_style_upgrade_relays(self):
        async def handler(reader, writer):
            await reader.readuntil(b"\r\n\r\n")
            writer.write(
                b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: echo\r\n"
                b"Connection: Upgrade\r\n\r\n"
            )
            await writer.drain()
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                writer.write(data)
                await writer.drain()

        origin = await self.serve(handler)
        proxy = await self.start_proxy()
        reader, writer = await self.connect(proxy)
        writer.write(
            f"GET /ws HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode()
            + b"Connection: Upgrade\r\nUpgrade: WebSocket, Echo\r\n\r\n"
        )
        await writer.drain()
        head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5)
        line, fields = parse_head(head)
        self.assertEqual("HTTP/1.1 101 Switching Protocols", line)
        self.assertEqual("Upgrade", fields["connection"])
        writer.write(b"ping")
        await writer.drain()
        self.assertEqual(b"ping", await asyncio.wait_for(reader.readexactly(4), 5))
        writer.close()

    async def test_declined_upgrade_returns_response(self):
        origin = await self.serve(self.responder(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nno"))
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(
            proxy,
            f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode()
            + b"Connection: Upgrade\r\nUpgrade: echo\r\n\r\n",
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 200 "))
        self.assertTrue(raw.endswith(b"no"))

    async def test_unsolicited_101_is_rejected(self):
        origin = await self.serve(
            self.responder(
                b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: x\r\nConnection: Upgrade\r\n\r\n"
            )
        )
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(
            proxy, f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode()
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 502 "))

    async def test_101_must_select_a_requested_protocol(self):
        origin = await self.serve(
            self.responder(
                b"HTTP/1.1 101 Switching Protocols\r\n"
                b"Upgrade: h2c\r\nConnection: Upgrade\r\n\r\n",
                hold=5.0,
            )
        )
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(
            proxy,
            f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode()
            + b"Connection: Upgrade\r\nUpgrade: websocket\r\n\r\n",
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 502 Bad Gateway\r\n"), raw[:80])

    async def test_invalid_101_upgrade_list_is_rejected(self):
        origin = await self.serve(
            self.responder(
                b"HTTP/1.1 101 Switching Protocols\r\n"
                b"Upgrade: websocket/\r\nConnection: Upgrade\r\n\r\n",
                hold=5.0,
            )
        )
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(
            proxy,
            f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode()
            + b"Connection: Upgrade\r\nUpgrade: websocket\r\n\r\n",
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 502 Bad Gateway\r\n"), raw[:80])


class TunnelTests(ProxyHarness):
    async def test_connect_tunnel(self):
        echo = await self.echo_port()
        proxy = await self.start_proxy()
        reader, writer = await self.connect(proxy)
        writer.write(f"CONNECT {LOCAL}:{echo} HTTP/1.1\r\nHost: x\r\n\r\n".encode())
        await writer.drain()
        head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5)
        self.assertIn(b"200", head)
        writer.write(b"hello")
        await writer.drain()
        self.assertEqual(b"hello", await asyncio.wait_for(reader.readexactly(5), 5))
        writer.write_eof()
        self.assertEqual(b"", await read_until_eof(reader))
        writer.close()

    async def test_one_way_tunnel_activity_refreshes_idle_timeout(self):
        async def handler(reader, writer):
            for value in range(12):
                writer.write(bytes((value,)))
                await writer.drain()
                await asyncio.sleep(0.05)
            writer.write_eof()

        stream = await self.serve(handler)
        proxy = await self.start_proxy(idle_timeout=0.2)
        reader, writer = await self.connect(proxy)
        writer.write(f"CONNECT {LOCAL}:{stream} HTTP/1.1\r\nHost: x\r\n\r\n".encode())
        await writer.drain()
        head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 2.0)
        self.assertTrue(head.startswith(b"HTTP/1.1 200 "))
        self.assertEqual(
            bytes(range(12)),
            await asyncio.wait_for(reader.readexactly(12), 2.0),
        )
        writer.close()

    async def test_connect_refused_gets_502(self):
        closed = socket.socket()
        closed.bind((LOCAL, 0))
        dead = closed.getsockname()[1]
        closed.close()
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(
            proxy, f"CONNECT {LOCAL}:{dead} HTTP/1.1\r\nHost: x\r\n\r\n".encode()
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 502 "))

    async def test_socks5_domain_and_ipv4(self):
        echo = await self.echo_port()
        proxy = await self.start_proxy()
        for atype, host in ((3, "localhost"), (1, LOCAL)):
            with self.subTest(atype=atype):
                reader, writer, reply = await self.socks5_open(proxy, host, echo, atype)
                self.assertEqual(0, reply)
                writer.write(b"abc")
                await writer.drain()
                self.assertEqual(b"abc", await asyncio.wait_for(reader.readexactly(3), 5))
                writer.close()

    async def test_socks5_error_replies(self):
        proxy = await self.start_proxy()
        # unsupported command
        reader, writer = await self.connect(proxy)
        writer.write(b"\x05\x01\x00")
        await writer.drain()
        await reader.readexactly(2)
        writer.write(b"\x05\x02\x00\x01" + socket.inet_aton(LOCAL) + struct.pack(">H", 80))
        await writer.drain()
        self.assertEqual(7, (await reader.readexactly(4))[1])
        writer.close()
        # unsupported address type
        reader, writer = await self.connect(proxy)
        writer.write(b"\x05\x01\x00")
        await writer.drain()
        await reader.readexactly(2)
        writer.write(b"\x05\x01\x00\x09")
        await writer.drain()
        self.assertEqual(8, (await reader.readexactly(4))[1])
        writer.close()
        # empty domain name (regression #10)
        reader, writer = await self.connect(proxy)
        writer.write(b"\x05\x01\x00")
        await writer.drain()
        await reader.readexactly(2)
        writer.write(b"\x05\x01\x00\x03\x00" + struct.pack(">H", 80))
        await writer.drain()
        self.assertEqual(1, (await reader.readexactly(4))[1])
        writer.close()
        # no acceptable auth method
        reader, writer = await self.connect(proxy)
        writer.write(b"\x05\x01\x02")
        await writer.drain()
        self.assertEqual(b"\x05\xff", await reader.readexactly(2))
        writer.close()

    async def test_socks4a(self):
        echo = await self.echo_port()
        proxy = await self.start_proxy()
        reader, writer, reply = await self.socks4_open(proxy, "localhost", echo)
        self.assertEqual(0x5A, reply)
        writer.write(b"xyz")
        await writer.drain()
        self.assertEqual(b"xyz", await asyncio.wait_for(reader.readexactly(3), 5))
        writer.close()

    async def test_socks4_bind_is_rejected(self):
        proxy = await self.start_proxy()
        reader, writer = await self.connect(proxy)
        writer.write(b"\x04\x02" + struct.pack(">H", 80) + socket.inet_aton(LOCAL) + b"\x00")
        await writer.drain()
        self.assertEqual(0x5B, (await reader.readexactly(8))[1])
        writer.close()


class UpstreamChainTests(ProxyHarness):
    async def test_http_upstream_forward_and_connect(self):
        record: list[bytes] = []
        upstream_port = await self.fake_http_proxy(record)
        handler = self.reflector()
        origin = await self.serve(handler)
        echo = await self.echo_port()
        upstream = Upstream(
            name="u",
            proxy_type="HTTP",
            host=LOCAL,
            port=upstream_port,
            username="user",
            password="pw",
        )
        proxy = await self.start_proxy(upstream=upstream)

        await self.http_roundtrip(
            proxy, f"GET http://{LOCAL}:{origin}/x HTTP/1.1\r\nHost: z\r\n\r\n".encode()
        )
        self.assertIn(f"GET http://{LOCAL}:{origin}/x HTTP/1.1".encode(), record[0])
        self.assertIn(b"Proxy-Authorization: Basic " + base64.b64encode(b"user:pw"), record[0])

        reader, writer = await self.connect(proxy)
        writer.write(f"CONNECT {LOCAL}:{echo} HTTP/1.1\r\nHost: x\r\n\r\n".encode())
        await writer.drain()
        self.assertIn(b"200", await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5))
        writer.write(b"tunnel")
        await writer.drain()
        self.assertEqual(b"tunnel", await asyncio.wait_for(reader.readexactly(6), 5))
        writer.close()
        self.assertIn(b"CONNECT ", record[1])

    async def test_socks5_upstream_with_auth(self):
        record: list[tuple] = []
        upstream_port = await self.fake_socks5_proxy(record, require_auth=("u", "p"))
        echo = await self.echo_port()
        upstream = Upstream(
            name="s5",
            proxy_type="SOCKS5",
            host=LOCAL,
            port=upstream_port,
            username="u",
            password="p",
        )
        proxy = await self.start_proxy(upstream=upstream)
        reader, writer, reply = await self.socks5_open(proxy, "localhost", echo, atype=3)
        self.assertEqual(0, reply)
        writer.write(b"chain")
        await writer.drain()
        self.assertEqual(b"chain", await asyncio.wait_for(reader.readexactly(5), 5))
        writer.close()
        # the destination name is forwarded verbatim, not transcoded
        self.assertEqual((1, 3, "localhost", echo), record[0])

    async def test_socks5_upstream_bound_address_is_forwarded(self):
        record: list[tuple] = []
        expected_bound = ("198.51.100.7", 43210)
        upstream_port = await self.fake_socks5_proxy(record, bound_address=expected_bound)
        echo = await self.echo_port()
        proxy = await self.start_proxy(
            upstream=Upstream(name="s5", proxy_type="SOCKS5", host=LOCAL, port=upstream_port)
        )

        _, writer, reply, bound = await self.socks5_open(
            proxy, LOCAL, echo, atype=1, include_bound=True
        )

        self.assertEqual(0, reply)
        self.assertEqual(expected_bound, bound)
        writer.close()

    async def test_socks4_upstream(self):
        record: list[tuple] = []
        upstream_port = await self.fake_socks4_proxy(record)
        echo = await self.echo_port()
        upstream = Upstream(
            name="s4", proxy_type="SOCKS4", host=LOCAL, port=upstream_port, username="id"
        )
        proxy = await self.start_proxy(upstream=upstream)
        reader, writer = await self.connect(proxy)
        writer.write(f"CONNECT {LOCAL}:{echo} HTTP/1.1\r\nHost: x\r\n\r\n".encode())
        await writer.drain()
        self.assertIn(b"200", await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5))
        writer.close()
        self.assertEqual((1, LOCAL, echo, b"id"), record[0])

    async def test_socks4_upstream_bound_address_is_forwarded(self):
        record: list[tuple] = []
        expected_bound = ("203.0.113.9", 43211)
        upstream_port = await self.fake_socks4_proxy(record, bound_address=expected_bound)
        echo = await self.echo_port()
        proxy = await self.start_proxy(
            upstream=Upstream(name="s4", proxy_type="SOCKS4", host=LOCAL, port=upstream_port)
        )

        _, writer, reply, bound = await self.socks4_open(proxy, LOCAL, echo, include_bound=True)

        self.assertEqual(0x5A, reply)
        self.assertEqual(expected_bound, bound)
        writer.close()

    async def test_socks4_upstream_rejects_ipv6(self):
        """Regression #8: an IPv6 literal must not be smuggled as a SOCKS4a name."""
        record: list[tuple] = []
        upstream_port = await self.fake_socks4_proxy(record)
        upstream = Upstream(name="s4", proxy_type="SOCKS4", host=LOCAL, port=upstream_port)
        proxy = await self.start_proxy(upstream=upstream)
        raw = await self.http_roundtrip(proxy, b"CONNECT [::1]:80 HTTP/1.1\r\nHost: x\r\n\r\n")
        self.assertTrue(raw.startswith(b"HTTP/1.1 502 "))
        self.assertEqual([], record)

    async def test_socks4_upstream_rejects_invalid_reply_version(self):
        async def handler(reader, writer):
            head = await reader.readexactly(8)
            await reader.readuntil(b"\x00")
            if head[4:7] == b"\x00\x00\x00" and head[7]:
                await reader.readuntil(b"\x00")
            writer.write(b"\x04\x5a" + bytes(6))
            await writer.drain()

        upstream_port = await self.serve(handler)
        upstream = Upstream(name="s4", proxy_type="SOCKS4", host=LOCAL, port=upstream_port)
        proxy = await self.start_proxy(upstream=upstream)

        raw = await self.http_roundtrip(
            proxy, b"CONNECT example.test:443 HTTP/1.1\r\nHost: x\r\n\r\n"
        )

        self.assertTrue(raw.startswith(b"HTTP/1.1 502 "), raw[:64])

    async def test_oversized_upstream_connect_response_gets_502(self):
        """Regression #4: LimitOverrunError must not escape as a bare drop."""

        async def handler(reader, writer):
            await reader.readuntil(b"\r\n\r\n")
            writer.write(b"HTTP/1.1 200 OK\r\nX-Pad: " + b"a" * 70000 + b"\r\n")
            await writer.drain()
            await asyncio.sleep(5)

        upstream_port = await self.serve(handler)
        upstream = Upstream(name="u", proxy_type="HTTP", host=LOCAL, port=upstream_port)
        proxy = await self.start_proxy(upstream=upstream)
        raw = await self.http_roundtrip(
            proxy, b"CONNECT example.test:443 HTTP/1.1\r\nHost: x\r\n\r\n"
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 502 "), raw[:64])

    async def test_truncated_socks5_upstream_reply_gets_socks_failure(self):
        """Regression #4: IncompleteReadError must become a SOCKS reply."""

        async def handler(reader, writer):
            count = (await reader.readexactly(2))[1]
            await reader.readexactly(count)
            writer.write(b"\x05\x00")
            await writer.drain()
            await reader.readexactly(4)
            writer.write(b"\x05\x00")  # truncated reply frame
            await writer.drain()
            writer.close()

        upstream_port = await self.serve(handler)
        upstream = Upstream(name="s5", proxy_type="SOCKS5", host=LOCAL, port=upstream_port)
        proxy = await self.start_proxy(upstream=upstream)
        _, writer, reply = await self.socks5_open(proxy, LOCAL, 9999, atype=1)
        self.assertEqual(1, reply)
        writer.close()


class RegressionTests(ProxyHarness):
    async def test_relay_stops_when_transport_closes_during_write(self):
        """A failed send must not turn later chunks into asyncio warnings."""

        proxy = NativeProxyServer(port=0)
        reader = mock.Mock()
        reader.read = mock.AsyncMock(return_value=b"x" * 1024)
        writer = mock.Mock()
        writer.is_closing.side_effect = (False, True)

        with self.assertRaisesRegex(ConnectionResetError, "closed during write"):
            await proxy._pipe(reader, writer)

        reader.read.assert_awaited_once_with(native_proxy._BUFFER_SIZE)
        writer.write.assert_called_once_with(b"x" * 1024)

    async def test_slow_reader_is_not_truncated(self):
        """Regression #1: closing must flush, not abort after 250 ms."""
        size = 8 * 1024 * 1024

        async def handler(reader, writer):
            await reader.readuntil(b"\r\n\r\n")
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % size
            )
            writer.write(b"x" * size)
            await writer.drain()
            writer.close()

        origin = await self.serve(handler)
        proxy = await self.start_proxy()
        reader, writer = await self.connect(proxy)
        writer.write(f"GET / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n\r\n".encode())
        await writer.drain()
        await asyncio.sleep(1.0)  # stall so the proxy's buffers fill up
        head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 20)
        _, fields = parse_head(head)
        self.assertEqual(str(size), fields["content-length"])
        body = await asyncio.wait_for(reader.readexactly(size), 60)
        self.assertEqual(size, len(body))
        writer.close()

    async def test_no_error_page_after_response_started(self):
        """Regression #2: never splice a status line onto a live response."""
        origin = await self.serve(
            self.responder(
                b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n" b"2\r\nok\r\n",
                hold=5.0,
            )
        )
        proxy = await self.start_proxy()
        reader, writer = await self.connect(proxy)
        writer.write(
            f"POST / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode()
            + b"Transfer-Encoding: chunked\r\n\r\n"
        )
        await writer.drain()
        head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5)
        self.assertTrue(head.startswith(b"HTTP/1.1 200 "))
        writer.write(b"zz\r\n")  # invalid chunk size, after the response started
        await writer.drain()
        rest = await read_until_closed(reader)
        self.assertEqual(b"2\r\nok\r\n", rest)
        self.assertNotIn(b"400", rest)
        writer.close()

    async def test_error_page_sent_when_nothing_forwarded(self):
        origin = await self.serve(self.responder(b"", hold=5.0))
        proxy = await self.start_proxy()
        raw = await self.http_roundtrip(
            proxy,
            f"POST / HTTP/1.1\r\nHost: {LOCAL}:{origin}\r\n".encode()
            + b"Transfer-Encoding: chunked\r\n\r\nzz\r\n",
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 400 "))

    async def test_half_open_tunnel_is_reaped(self):
        """Regression #3: an idle half-open pair must not be pinned open."""

        async def handler(reader, writer):
            writer.write(b"hello")
            await writer.drain()
            writer.close()

        origin = await self.serve(handler)
        proxy = await self.start_proxy(idle_timeout=0.3)
        reader, writer = await self.connect(proxy)
        writer.write(f"CONNECT {LOCAL}:{origin} HTTP/1.1\r\nHost: x\r\n\r\n".encode())
        await writer.drain()
        await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5)
        self.assertEqual(b"hello", await asyncio.wait_for(reader.readexactly(5), 5))
        # client never closes its own half
        await self.wait_until(lambda: proxy.active_connections == 0, timeout=5.0)
        writer.close()

    async def test_connection_cap(self):
        """Regression #3: the cap is enforced at accept time."""
        proxy = await self.start_proxy(max_connections=1, handshake_timeout=5.0)
        first_reader, first_writer = await self.connect(proxy)  # sends nothing
        await self.wait_until(lambda: proxy.active_connections == 1)
        second_reader, second_writer = await self.connect(proxy)
        self.assertEqual(b"", await asyncio.wait_for(second_reader.read(), 5))
        second_writer.close()
        first_writer.close()

    @unittest.skipUnless(
        sys.platform == "win32" and sys.version_info[:2] == (3, 14),
        "Windows Python 3.14 SelectorEventLoop capacity regression",
    )
    async def test_windows_selector_handles_effective_connection_limit(self):
        echo = await self.echo_port()
        proxy = await self.start_proxy()
        connections = []

        async def open_tunnel(index: int) -> None:
            reader, writer = await self.connect(proxy)
            connections.append((reader, writer))
            writer.write(f"CONNECT {LOCAL}:{echo} HTTP/1.1\r\nHost: stress\r\n\r\n".encode())
            await writer.drain()
            head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 10)
            self.assertTrue(head.startswith(b"HTTP/1.1 200 "), head[:80])
            payload = index.to_bytes(4, "big")
            writer.write(payload)
            await writer.drain()
            self.assertEqual(payload, await asyncio.wait_for(reader.readexactly(len(payload)), 10))

        try:
            self.assertEqual(200, proxy.max_connections)
            for start in range(0, 200, 20):
                await asyncio.gather(*(open_tunnel(index) for index in range(start, start + 20)))
            await self.wait_until(lambda: proxy.active_connections == 200, timeout=10)
            self.assertTrue(await asyncio.to_thread(proxy.stop, 15))
            await asyncio.gather(
                *(asyncio.wait_for(reader.read(), 10) for reader, _ in connections)
            )
        finally:
            for _, writer in connections:
                writer.close()

    async def test_destination_policy(self):
        """Regression #13: policy denial is a 403 / SOCKS5 reply 2."""
        echo = await self.echo_port()
        blocked: list[tuple[str, int]] = []

        def policy(host: str, port: int) -> bool:
            blocked.append((host, port))
            return port != echo

        proxy = await self.start_proxy(destination_policy=policy)
        raw = await self.http_roundtrip(
            proxy, f"CONNECT {LOCAL}:{echo} HTTP/1.1\r\nHost: x\r\n\r\n".encode()
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 403 "))
        raw = await self.http_roundtrip(
            proxy, f"GET http://{LOCAL}:{echo}/ HTTP/1.1\r\nHost: x\r\n\r\n".encode()
        )
        self.assertTrue(raw.startswith(b"HTTP/1.1 403 "))
        _, writer, reply = await self.socks5_open(proxy, LOCAL, echo, atype=1)
        self.assertEqual(2, reply)
        writer.close()
        self.assertTrue(blocked)

    async def test_upstream_switch_is_atomic_for_live_connections(self):
        echo = await self.echo_port()
        proxy = await self.start_proxy()
        reader, writer = await self.connect(proxy)
        writer.write(f"CONNECT {LOCAL}:{echo} HTTP/1.1\r\nHost: x\r\n\r\n".encode())
        await writer.drain()
        await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5)
        proxy.set_upstream(Upstream(name="u", proxy_type="HTTP", host=LOCAL, port=1))
        writer.write(b"still-direct")
        await writer.drain()
        self.assertEqual(b"still-direct", await asyncio.wait_for(reader.readexactly(12), 5))
        writer.close()

    async def test_stop_closes_active_connections_quickly(self):
        echo = await self.echo_port()
        proxy = await self.start_proxy()
        reader, writer = await self.connect(proxy)
        writer.write(f"CONNECT {LOCAL}:{echo} HTTP/1.1\r\nHost: x\r\n\r\n".encode())
        await writer.drain()
        await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5)
        started = time.monotonic()
        self.assertTrue(await asyncio.to_thread(proxy.stop, 10.0))
        self.assertLess(time.monotonic() - started, 5.0)
        self.assertEqual(b"", await asyncio.wait_for(reader.read(), 5))
        writer.close()


if __name__ == "__main__":
    unittest.main()
