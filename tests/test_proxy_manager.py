import pytest

from pyproxyswitch.errors import ConfigError
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

    def __init__(self, host, port, upstream, connect_timeout):
        self.host = host
        self.port = port
        self.bound_port = port
        self.upstream = upstream
        self.connect_timeout = connect_timeout
        self.is_running = False
        self.stop_result = True
        type(self).instances.append(self)

    def start(self, timeout=5):
        self.is_running = True

    def stop(self, timeout=5):
        if self.stop_result:
            self.is_running = False
        return self.stop_result

    def set_upstream(self, upstream):
        self.upstream = upstream


@pytest.fixture
def fake_server(monkeypatch):
    FakeServer.instances.clear()
    monkeypatch.setattr("pyproxyswitch.proxy_manager.NativeProxyServer", FakeServer)
    return FakeServer


def test_start_direct_proxy(fake_server):
    manager = ProxyManager(StubConfig())

    manager.start_proxy("NoProxy")

    assert manager.server is fake_server.instances[0]
    assert manager.server.upstream.proxy_type == "DIRECT"
    assert manager.server.is_running


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

    with pytest.raises(ConfigError, match="Proxy not found"):
        manager.start_proxy("missing")


@pytest.mark.parametrize("port", [0, 65536, "invalid"])
def test_invalid_listener_port_is_rejected(fake_server, port):
    manager = ProxyManager(StubConfig(LOCAL_PORT=port))

    with pytest.raises(ConfigError):
        manager.start_proxy("NoProxy")


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
