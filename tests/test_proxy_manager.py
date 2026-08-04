import errno
import socket

import pytest

from pyproxyswitch.errors import ConfigError, ErrorCode, ProxyStartError
from pyproxyswitch.port_diagnostics import PortOwner
from pyproxyswitch.proxy_manager import ProxyManager


class StubConfig:
    def __init__(self, proxies=None, **settings):
        self.proxies = proxies or []
        self.settings = {
            "CONNECT_TIMEOUT": 15,
            "LOCAL_ADDRESS": "127.0.0.1",
            "LOCAL_PORT": 8888,
        }
        self.settings.update(settings)

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def get_proxies(self):
        return list(self.proxies)


class FakeServer:
    instances = []
    fail_start_ports = set()

    def __init__(
        self,
        host,
        port,
        upstream,
        connect_timeout,
        allow_remote_clients=False,
    ):
        if not allow_remote_clients and host not in {
            "127.0.0.1",
            "::1",
            "localhost",
            "localhost.localdomain",
        }:
            raise ValueError("non-loopback bind rejected")
        self.host = host
        self.port = port
        self.bound_port = port
        self.upstream = upstream
        self.connect_timeout = connect_timeout
        self.allow_remote_clients = allow_remote_clients
        self.is_running = False
        self.stop_result = True
        self.stop_calls = 0
        type(self).instances.append(self)

    def start(self, timeout=5):
        if self.port in type(self).fail_start_ports:
            raise OSError("bind failed")
        self.is_running = True

    def stop(self, timeout=5):
        self.stop_calls += 1
        if self.stop_result:
            self.is_running = False
        return self.stop_result

    def set_upstream(self, upstream):
        self.upstream = upstream


@pytest.fixture
def fake_server(monkeypatch):
    FakeServer.instances.clear()
    FakeServer.fail_start_ports.clear()
    monkeypatch.setattr("pyproxyswitch.proxy_manager.NativeProxyServer", FakeServer)
    return FakeServer


def test_start_direct_proxy(fake_server):
    manager = ProxyManager(StubConfig())

    manager.start_proxy("NoProxy")

    assert manager.server is fake_server.instances[0]
    assert manager.server.upstream.proxy_type == "DIRECT"
    assert manager.server.is_running
    assert manager.server.allow_remote_clients is False


def test_failed_initial_listener_uses_start_error(fake_server):
    fake_server.fail_start_ports.add(8888)
    manager = ProxyManager(StubConfig())

    with pytest.raises(ProxyStartError) as exc_info:
        manager.start_proxy("NoProxy")

    assert exc_info.value.code == ErrorCode.PROXY_START_FAILED
    assert manager.server is None


def test_configured_non_loopback_listener_is_rejected_without_authentication(fake_server):
    manager = ProxyManager(StubConfig(LOCAL_ADDRESS="0.0.0.0"))

    with pytest.raises(ProxyStartError) as exc_info:
        manager.start_proxy("NoProxy")

    assert exc_info.value.code == ErrorCode.PROXY_START_FAILED
    assert manager.server is None


def test_switching_upstream_reuses_listener(fake_server):
    config = StubConfig(
        proxies=[
            ("one", "one.example", "8080", "HTTP", "", ""),
            ("two", "127.0.0.1", "1080", "SOCKS5", "user", "pass"),
        ]
    )
    manager = ProxyManager(config)
    manager.start_proxy("one")
    listener = manager.server

    manager.start_proxy("two")

    assert manager.server is listener
    assert len(fake_server.instances) == 1
    assert listener.upstream.name == "two"
    assert listener.upstream.proxy_type == "SOCKS5"


def test_unknown_proxy_is_rejected(fake_server):
    manager = ProxyManager(StubConfig())

    with pytest.raises(ConfigError) as exc_info:
        manager.start_proxy("missing")
    assert exc_info.value.code == ErrorCode.CONFIG_PROXY_NOT_FOUND
    assert exc_info.value.params == {"name": "missing"}


@pytest.mark.parametrize("port", [0, 65536, "invalid", 8888.9, "8888.9", True])
def test_invalid_listener_port_is_rejected(fake_server, port):
    manager = ProxyManager(StubConfig(LOCAL_PORT=port))

    with pytest.raises(ConfigError) as exc_info:
        manager.start_proxy("NoProxy")
    expected = (
        ErrorCode.CONFIG_LOCAL_PORT_INTEGER
        if port not in (0, 65536)
        else ErrorCode.CONFIG_LOCAL_PORT_RANGE
    )
    assert exc_info.value.code == expected


def test_restart_listener_preserves_upstream(fake_server):
    config = StubConfig(proxies=[("one", "one.example", "8080", "HTTP", "", "")])
    manager = ProxyManager(config)
    manager.start_proxy("one")
    original = manager.server
    config.settings["LOCAL_PORT"] = 9999

    manager.restart_listener()

    assert manager.server is not original
    assert manager.server.port == 9999
    assert manager.server.upstream.name == "one"


def test_stop_proxy_clears_server(fake_server):
    manager = ProxyManager(StubConfig())
    manager.start_proxy("NoProxy")

    assert manager.stop_proxy()
    assert manager.server is None


def test_non_running_server_is_cleaned_up_before_replacement(fake_server):
    manager = ProxyManager(StubConfig())
    manager.start_proxy("NoProxy")
    stale = manager.server
    stale.is_running = False

    manager.start_proxy("NoProxy")

    assert stale.stop_calls == 1
    assert manager.server is not stale
    assert manager.server.is_running


def test_failed_listener_change_restores_previous_address(fake_server):
    config = StubConfig()
    manager = ProxyManager(config)
    manager.start_proxy("NoProxy")
    config.settings["LOCAL_PORT"] = 9999
    fake_server.fail_start_ports.add(9999)

    with pytest.raises(ProxyStartError) as exc_info:
        manager.restart_listener()
    assert exc_info.value.code == ErrorCode.PROXY_RESTART_FAILED

    assert manager.server is not None
    assert manager.server.port == 8888
    assert manager.server.is_running


def test_failed_listener_change_restores_previous_upstream(fake_server):
    config = StubConfig(
        proxies=[
            ("one", "one.example", "8080", "HTTP", "", ""),
            ("two", "two.example", "1080", "SOCKS5", "", ""),
        ]
    )
    manager = ProxyManager(config)
    manager.start_proxy("one")
    config.settings["LOCAL_PORT"] = 9999
    fake_server.fail_start_ports.add(9999)

    with pytest.raises(ProxyStartError) as exc_info:
        manager.start_proxy("two")
    assert exc_info.value.code == ErrorCode.PROXY_RECONFIGURE_FAILED

    assert manager.server is not None
    assert manager.server.port == 8888
    assert manager.server.upstream.name == "one"
    assert manager.server.is_running


class AddrInUseServer(FakeServer):
    """Simulate a listener whose bind fails with EADDRINUSE."""

    def start(self, timeout=5):
        error = OSError(errno.EADDRINUSE, "Address already in use")
        raise RuntimeError("Cannot start native proxy: [Errno 98]") from error


@pytest.fixture
def addr_in_use_server(monkeypatch):
    AddrInUseServer.instances.clear()
    monkeypatch.setattr("pyproxyswitch.proxy_manager.NativeProxyServer", AddrInUseServer)
    return AddrInUseServer


def test_addr_in_use_reports_port_owner(addr_in_use_server, monkeypatch):
    monkeypatch.setattr(
        "pyproxyswitch.proxy_manager.find_port_owner",
        lambda port, host=None: PortOwner(4321, "fakeproc"),
    )
    manager = ProxyManager(StubConfig())

    with pytest.raises(ProxyStartError) as exc_info:
        manager.start_proxy("NoProxy")

    assert exc_info.value.code == ErrorCode.PROXY_PORT_IN_USE
    assert exc_info.value.params == {
        "host": "127.0.0.1",
        "port": 8888,
        "process": "fakeproc (PID 4321)",
    }
    assert "fakeproc (PID 4321)" in exc_info.value.localized("zh_CN")
    assert "fakeproc (PID 4321)" in exc_info.value.localized("en")


def test_addr_in_use_without_identifiable_owner(addr_in_use_server, monkeypatch):
    monkeypatch.setattr("pyproxyswitch.proxy_manager.find_port_owner", lambda port, host=None: None)
    manager = ProxyManager(StubConfig())

    with pytest.raises(ProxyStartError) as exc_info:
        manager.start_proxy("NoProxy")

    assert exc_info.value.code == ErrorCode.PROXY_PORT_IN_USE_UNKNOWN
    assert exc_info.value.params == {"host": "127.0.0.1", "port": 8888}
    assert "8888" in exc_info.value.localized("zh_CN")


def test_real_listener_reports_occupied_port():
    """Bind a real socket and let the real native server hit EADDRINUSE."""

    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    blocker.bind(("127.0.0.1", 0))
    blocker.listen(1)
    port = blocker.getsockname()[1]
    try:
        manager = ProxyManager(StubConfig(LOCAL_PORT=port))
        with pytest.raises(ProxyStartError) as exc_info:
            manager.start_proxy("NoProxy")
    finally:
        blocker.close()

    assert exc_info.value.code in (
        ErrorCode.PROXY_PORT_IN_USE,
        ErrorCode.PROXY_PORT_IN_USE_UNKNOWN,
    )
    assert exc_info.value.params["port"] == port
