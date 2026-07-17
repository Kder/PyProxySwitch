from pyproxyswitch.errors import ConfigError, ProxyError, ProxyStartError


def test_proxy_error_uses_user_message_as_default_log_message():
    error = ProxyError("Visible message")
    assert str(error) == "Visible message"
    assert error.log_message == "Visible message"


def test_proxy_error_preserves_detailed_log_message():
    error = ProxyStartError("Could not start", "Port is already in use")
    assert error.user_message == "Could not start"
    assert error.log_message == "Port is already in use"
    assert isinstance(error, ProxyError)


def test_config_error_is_a_proxy_error():
    assert isinstance(ConfigError("Invalid port"), ProxyError)
