import pytest

from pyproxyswitch.errors import ConfigError, ErrorCode, ProxyStartError
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


def test_failed_initial_listener_uses_start_error(fake_server):
    fake_server.fail_start_ports.add(8888)
    manager = ProxyManager(StubConfig())

    with pytest.raises(ProxyStartError) as exc_info:
        manager.start_proxy("NoProxy")

    assert exc_info.value.code == ErrorCode.PROXY_START_FAILED
    assert manager.server is None


def test_configured_listener_address_is_an_explicit_remote_bind_opt_in(fake_server):
    manager = ProxyManager(StubConfig(LOCAL_ADDRESS="0.0.0.0"))

    manager.start_proxy("NoProxy")

    assert manager.server.host == "0.0.0.0"
    assert manager.server.allow_remote_clients is True


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


@pytest.mark.parametrize("port", [0, 65536, "invalid"])
def test_invalid_listener_port_is_rejected(fake_server, port):
    manager = ProxyManager(StubConfig(LOCAL_PORT=port))

    with pytest.raises(ConfigError) as exc_info:
        manager.start_proxy("NoProxy")
    expected = (
        ErrorCode.CONFIG_LOCAL_PORT_INTEGER
        if port == "invalid"
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
