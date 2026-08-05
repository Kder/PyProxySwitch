import socket

import pytest

from pyproxyswitch.native_proxy import NativeProxyServer, Upstream
from pyproxyswitch.proxy_check import check_proxy


@pytest.fixture
def direct_upstream():
    """A real native server with a DIRECT route acts as the upstream under test."""

    server = NativeProxyServer(port=0, upstream=Upstream.direct())
    server.start()
    yield server
    server.stop()


@pytest.fixture
def target_port():
    """A plain listener the probe tunnels to; no traffic is exchanged."""

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(5)
    yield listener.getsockname()[1]
    listener.close()


@pytest.fixture
def closed_port():
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


@pytest.mark.parametrize("proxy_type", ["HTTP", "SOCKS4", "SOCKS5"])
def test_reachable_upstream_passes(direct_upstream, target_port, proxy_type):
    assert check_proxy(
        "127.0.0.1",
        direct_upstream.bound_port,
        proxy_type,
        timeout=5,
        target=("127.0.0.1", target_port),
    )


def test_unreachable_upstream_fails(closed_port, target_port):
    assert not check_proxy(
        "127.0.0.1",
        closed_port,
        "SOCKS5",
        timeout=2,
        target=("127.0.0.1", target_port),
    )


def test_unreachable_target_fails(direct_upstream, closed_port):
    assert not check_proxy(
        "127.0.0.1",
        direct_upstream.bound_port,
        "SOCKS5",
        timeout=5,
        target=("127.0.0.1", closed_port),
    )
