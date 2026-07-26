import pytest

from pyproxyswitch.errors import (
    ConfigError,
    ErrorCode,
    ProxyError,
    ProxyStartError,
    ValidationError,
    format_cli_error,
    format_user_error,
)
from pyproxyswitch.gui.error_display import localized_error_message


def test_coded_error_exposes_stable_code_and_parameters():
    error = ConfigError(
        ErrorCode.CONFIG_LOCAL_PORT_RANGE,
        params={"port": 70000},
    )
    assert error.code == "config.local_port.range"
    assert error.params == {"port": 70000}
    assert str(error) == "Invalid local proxy port: 70000; expected 1-65535"
    assert error.user_message == str(error)
    assert error.log_message == str(error)
    assert isinstance(error, ProxyError)


def test_proxy_error_preserves_technical_log_detail():
    error = ProxyStartError(
        ErrorCode.PROXY_START_FAILED,
        detail="Port is already in use",
    )
    assert error.user_message == "Failed to start proxy service"
    assert error.log_message == "Port is already in use"
    assert isinstance(error, ProxyError)


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", "Proxy name is required"),
        ("en-US", "Proxy name is required"),
        ("zh_CN", "代理名称不能为空"),
        ("zh-TW", "代理名称不能为空"),
    ],
)
def test_error_is_translated_at_boundary(language, expected):
    error = ValidationError(ErrorCode.VALIDATION_NAME_REQUIRED)
    assert format_user_error(error, language) == expected
    assert localized_error_message(error, language) == expected


def test_batch_error_translates_nested_line_context():
    line_error = ValidationError(
        ErrorCode.VALIDATION_PORT_RANGE,
        params={"minimum": 1, "maximum": 65535},
        line=2,
    )
    error = ValidationError(
        ErrorCode.VALIDATION_BATCH_INVALID,
        errors=[line_error],
    )
    assert format_user_error(error, "en") == (
        "The batch proxy configuration contains errors:\n"
        "Line 2: Port must be between 1 and 65535"
    )
    assert format_user_error(error, "zh_CN") == (
        "批量代理配置包含错误：\n"
        "第2行：端口号必须在1-65535之间"
    )


def test_unknown_error_code_is_rejected():
    with pytest.raises(ValueError, match="Unknown application error code"):
        ValidationError("validation.not_registered")


def test_unknown_exception_is_passed_through_at_boundary():
    assert format_user_error(RuntimeError("technical detail"), "zh_CN") == (
        "technical detail"
    )


def test_cli_error_line_is_fully_localized():
    error = ProxyStartError(ErrorCode.PROXY_START_FAILED)
    assert format_cli_error(error, "en", fatal=True) == (
        "Fatal error: Failed to start proxy service"
    )
    assert format_cli_error(error, "zh_CN", fatal=True) == (
        "致命错误：代理服务启动失败"
    )
