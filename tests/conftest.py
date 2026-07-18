import os

import pytest

from pyproxyswitch.config import ConfigManager

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def reset_config_singleton():
    ConfigManager.reset_singleton()
    yield
    ConfigManager.reset_singleton()


@pytest.fixture(scope="session")
def qapp():
    from PySide6 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


@pytest.fixture
def proxy_validator():
    from pyproxyswitch.proxy_validation import ProxyValidator

    return ProxyValidator()


@pytest.fixture
def batch_validator():
    from pyproxyswitch.proxy_validation import BatchImportValidator

    return BatchImportValidator()


@pytest.fixture
def sample_proxy_content():
    return (
        "# Test proxy list\n"
        "test_proxy 192.168.1.1:8080\n"
        "auth_proxy 10.0.0.1:3128 user:pass\n"
        "socks_proxy 203.0.113.5:1080 SOCKS5\n"
        "invalid_port_proxy test.example.com:99999\n"
    )
