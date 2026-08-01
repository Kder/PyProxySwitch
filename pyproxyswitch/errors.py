#!/usr/bin/env python

"""Stable, localizable application errors.

Core modules raise errors containing only a stable code, structured parameters,
and an optional technical detail.  User-facing text is rendered at the GUI or
CLI boundary so the same failure is presented consistently in either language.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Self


class ErrorCode(StrEnum):
    """Public error identifiers.

    Values are deliberately independent from translated text and may be used by
    callers, tests, logs, and future machine-readable interfaces.
    """

    VALIDATION_NAME_REQUIRED = "validation.name.required"
    VALIDATION_NAME_TOO_LONG = "validation.name.too_long"
    VALIDATION_NAME_INVALID = "validation.name.invalid"
    VALIDATION_NAME_RESERVED = "validation.name.reserved"
    VALIDATION_NAME_DUPLICATE = "validation.name.duplicate"
    VALIDATION_ADDRESS_REQUIRED = "validation.address.required"
    VALIDATION_ADDRESS_EMBEDDED_PORT = "validation.address.embedded_port"
    VALIDATION_ADDRESS_DANGEROUS_CHARACTER = (
        "validation.address.dangerous_character"
    )
    VALIDATION_ADDRESS_INVALID_IPV6 = "validation.address.invalid_ipv6"
    VALIDATION_ADDRESS_INVALID = "validation.address.invalid"
    VALIDATION_ADDRESS_INVALID_IPV4 = "validation.address.invalid_ipv4"
    VALIDATION_ADDRESS_INVALID_IPV4_VALUE = (
        "validation.address.invalid_ipv4_value"
    )
    VALIDATION_ADDRESS_DOMAIN_TOO_LONG = "validation.address.domain_too_long"
    VALIDATION_PORT_REQUIRED = "validation.port.required"
    VALIDATION_PORT_NUMERIC = "validation.port.numeric"
    VALIDATION_PORT_RANGE = "validation.port.range"
    VALIDATION_PROXY_TYPE_UNSUPPORTED = "validation.proxy_type.unsupported"
    VALIDATION_USERNAME_TOO_LONG = "validation.username.too_long"
    VALIDATION_USERNAME_CONTROL_CHARACTER = (
        "validation.username.control_character"
    )
    VALIDATION_USERNAME_DANGEROUS_CHARACTER = (
        "validation.username.dangerous_character"
    )
    VALIDATION_PASSWORD_TOO_LONG = "validation.password.too_long"
    VALIDATION_PASSWORD_CONTROL_CHARACTER = (
        "validation.password.control_character"
    )
    VALIDATION_SOCKS5_CREDENTIALS_PAIR = (
        "validation.socks5.credentials_pair"
    )
    VALIDATION_SOCKS5_CREDENTIALS_UNICODE = (
        "validation.socks5.credentials_unicode"
    )
    VALIDATION_SOCKS5_CREDENTIALS_TOO_LONG = (
        "validation.socks5.credentials_too_long"
    )
    VALIDATION_SOCKS4_PASSWORD_UNSUPPORTED = (
        "validation.socks4.password_unsupported"
    )
    VALIDATION_BATCH_QUOTE = "validation.batch.quote"
    VALIDATION_BATCH_FORMAT = "validation.batch.format"
    VALIDATION_BATCH_TOO_MANY_FIELDS = "validation.batch.too_many_fields"
    VALIDATION_BATCH_ADDRESS_PORT_REQUIRED = (
        "validation.batch.address_port_required"
    )
    VALIDATION_BATCH_INVALID_IPV6 = "validation.batch.invalid_ipv6"
    VALIDATION_BATCH_AUTH_OR_TYPE = "validation.batch.auth_or_type"
    VALIDATION_BATCH_AUTH_FORMAT = "validation.batch.auth_format"
    VALIDATION_BATCH_PROXY_TYPE_UNSUPPORTED = (
        "validation.batch.proxy_type_unsupported"
    )
    VALIDATION_BATCH_INVALID = "validation.batch.invalid"
    VALIDATION_BATCH_NONE_VALID = "validation.batch.none_valid"
    VALIDATION_FIELD_UNKNOWN = "validation.field.unknown"

    CONFIG_LOCAL_ADDRESS_REQUIRED = "config.local_address.required"
    CONFIG_LOCAL_PORT_INTEGER = "config.local_port.integer"
    CONFIG_LOCAL_PORT_RANGE = "config.local_port.range"
    CONFIG_PROXY_NAME_REQUIRED = "config.proxy_name.required"
    CONFIG_PROXY_NOT_FOUND = "config.proxy.not_found"
    CONFIG_PROXY_INVALID = "config.proxy.invalid"
    PROXY_START_FAILED = "proxy.start.failed"
    PROXY_RESTART_FAILED = "proxy.restart.failed"
    PROXY_RECONFIGURE_FAILED = "proxy.reconfigure.failed"


_MESSAGES: dict[ErrorCode, dict[str, str]] = {
    ErrorCode.VALIDATION_NAME_REQUIRED: {
        "en": "Proxy name is required",
        "zh_CN": "代理名称不能为空",
    },
    ErrorCode.VALIDATION_NAME_TOO_LONG: {
        "en": "Proxy name must not exceed {max_length} characters",
        "zh_CN": "代理名称长度不能超过{max_length}个字符",
    },
    ErrorCode.VALIDATION_NAME_INVALID: {
        "en": (
            "Proxy name may contain only letters, numbers, Chinese characters, "
            "underscores, and hyphens, with a length of 1-{max_length}"
        ),
        "zh_CN": (
            "代理名称只能包含字母、数字、中文、下划线和连字符，"
            "长度1-{max_length}"
        ),
    },
    ErrorCode.VALIDATION_NAME_RESERVED: {
        "en": "{name!r} is a reserved proxy name",
        "zh_CN": "{name!r}是保留名称，不能使用",
    },
    ErrorCode.VALIDATION_NAME_DUPLICATE: {
        "en": "A proxy named {name!r} already exists",
        "zh_CN": "代理名称 {name!r} 已存在",
    },
    ErrorCode.VALIDATION_ADDRESS_REQUIRED: {
        "en": "Proxy address is required",
        "zh_CN": "代理地址不能为空",
    },
    ErrorCode.VALIDATION_ADDRESS_EMBEDDED_PORT: {
        "en": "Proxy address must not include a port; use the port field",
        "zh_CN": "代理地址不能包含端口号，请使用独立的端口字段",
    },
    ErrorCode.VALIDATION_ADDRESS_DANGEROUS_CHARACTER: {
        "en": "Proxy address contains an unsafe character: {character!r}",
        "zh_CN": "域名包含危险字符：{character!r}",
    },
    ErrorCode.VALIDATION_ADDRESS_INVALID_IPV6: {
        "en": "Invalid IPv6 address",
        "zh_CN": "无效的IPv6地址格式",
    },
    ErrorCode.VALIDATION_ADDRESS_INVALID: {
        "en": "Invalid IP address or domain name",
        "zh_CN": "无效的IP地址或域名格式",
    },
    ErrorCode.VALIDATION_ADDRESS_INVALID_IPV4: {
        "en": "Invalid IPv4 address",
        "zh_CN": "无效的IP地址格式",
    },
    ErrorCode.VALIDATION_ADDRESS_INVALID_IPV4_VALUE: {
        "en": "IPv4 address contains an invalid value",
        "zh_CN": "IPv4地址包含无效数值",
    },
    ErrorCode.VALIDATION_ADDRESS_DOMAIN_TOO_LONG: {
        "en": "Domain name must not exceed {max_length} characters",
        "zh_CN": "域名长度不能超过{max_length}个字符",
    },
    ErrorCode.VALIDATION_PORT_REQUIRED: {
        "en": "Port is required",
        "zh_CN": "端口号不能为空",
    },
    ErrorCode.VALIDATION_PORT_NUMERIC: {
        "en": "Port must contain ASCII digits only",
        "zh_CN": "端口号必须是数字",
    },
    ErrorCode.VALIDATION_PORT_RANGE: {
        "en": "Port must be between {minimum} and {maximum}",
        "zh_CN": "端口号必须在{minimum}-{maximum}之间",
    },
    ErrorCode.VALIDATION_PROXY_TYPE_UNSUPPORTED: {
        "en": "Proxy type must be one of: {types}",
        "zh_CN": "代理类型必须是以下之一：{types}",
    },
    ErrorCode.VALIDATION_USERNAME_TOO_LONG: {
        "en": "Username must not exceed {max_length} characters",
        "zh_CN": "用户名长度不能超过{max_length}个字符",
    },
    ErrorCode.VALIDATION_USERNAME_CONTROL_CHARACTER: {
        "en": "Username contains a control character",
        "zh_CN": "用户名包含非法控制字符",
    },
    ErrorCode.VALIDATION_USERNAME_DANGEROUS_CHARACTER: {
        "en": "Username contains an unsafe character: {character!r}",
        "zh_CN": "用户名包含危险字符：{character!r}",
    },
    ErrorCode.VALIDATION_PASSWORD_TOO_LONG: {
        "en": "Password must not exceed {max_length} characters",
        "zh_CN": "密码长度不能超过{max_length}个字符",
    },
    ErrorCode.VALIDATION_PASSWORD_CONTROL_CHARACTER: {
        "en": "Password contains a control character",
        "zh_CN": "密码包含非法控制字符",
    },
    ErrorCode.VALIDATION_SOCKS5_CREDENTIALS_PAIR: {
        "en": "SOCKS5 authentication requires both username and password",
        "zh_CN": "SOCKS5认证必须同时提供用户名和密码",
    },
    ErrorCode.VALIDATION_SOCKS5_CREDENTIALS_UNICODE: {
        "en": "SOCKS5 credentials contain invalid Unicode characters",
        "zh_CN": "SOCKS5认证信息包含无效的Unicode字符",
    },
    ErrorCode.VALIDATION_SOCKS5_CREDENTIALS_TOO_LONG: {
        "en": (
            "SOCKS5 username and password must each be at most {max_bytes} "
            "bytes when UTF-8 encoded"
        ),
        "zh_CN": (
            "SOCKS5用户名和密码的UTF-8编码不能超过{max_bytes}字节"
        ),
    },
    ErrorCode.VALIDATION_SOCKS4_PASSWORD_UNSUPPORTED: {
        "en": "SOCKS4 supports a User ID but does not support passwords",
        "zh_CN": "SOCKS4仅支持用户ID，不支持密码",
    },
    ErrorCode.VALIDATION_BATCH_QUOTE: {
        "en": "The line contains an incomplete quote or escape sequence",
        "zh_CN": "引号或转义字符不完整",
    },
    ErrorCode.VALIDATION_BATCH_FORMAT: {
        "en": "Invalid format; proxy name and address are required",
        "zh_CN": "格式错误，至少需要代理名称和地址",
    },
    ErrorCode.VALIDATION_BATCH_TOO_MANY_FIELDS: {
        "en": "Too many fields",
        "zh_CN": "参数过多",
    },
    ErrorCode.VALIDATION_BATCH_ADDRESS_PORT_REQUIRED: {
        "en": "Address must include a port (format: address:port)",
        "zh_CN": "地址格式错误，必须包含端口（格式：地址:端口）",
    },
    ErrorCode.VALIDATION_BATCH_INVALID_IPV6: {
        "en": "Invalid IPv6 address format",
        "zh_CN": "IPv6地址格式错误",
    },
    ErrorCode.VALIDATION_BATCH_AUTH_OR_TYPE: {
        "en": (
            "Credentials must use username:password format, or specify a "
            "supported proxy type"
        ),
        "zh_CN": "认证信息必须使用用户名:密码格式，或指定受支持的代理类型",
    },
    ErrorCode.VALIDATION_BATCH_AUTH_FORMAT: {
        "en": "Credentials must use username:password format",
        "zh_CN": "认证信息必须使用用户名:密码格式",
    },
    ErrorCode.VALIDATION_BATCH_PROXY_TYPE_UNSUPPORTED: {
        "en": "Unsupported proxy type: {proxy_type}",
        "zh_CN": "不支持的代理类型 {proxy_type}",
    },
    ErrorCode.VALIDATION_BATCH_INVALID: {
        "en": "The batch proxy configuration contains errors:",
        "zh_CN": "批量代理配置包含错误：",
    },
    ErrorCode.VALIDATION_BATCH_NONE_VALID: {
        "en": "No valid proxy configuration was found",
        "zh_CN": "没有找到有效的代理配置",
    },
    ErrorCode.VALIDATION_FIELD_UNKNOWN: {
        "en": "Unknown proxy field",
        "zh_CN": "未知的代理字段",
    },
    ErrorCode.CONFIG_LOCAL_ADDRESS_REQUIRED: {
        "en": "Local proxy address is required",
        "zh_CN": "本地代理地址不能为空",
    },
    ErrorCode.CONFIG_LOCAL_PORT_INTEGER: {
        "en": "Local proxy port must be an integer",
        "zh_CN": "本地代理端口必须是整数",
    },
    ErrorCode.CONFIG_LOCAL_PORT_RANGE: {
        "en": "Invalid local proxy port: {port}; expected 1-65535",
        "zh_CN": "本地代理端口无效：{port}；必须在1-65535之间",
    },
    ErrorCode.CONFIG_PROXY_NAME_REQUIRED: {
        "en": "Proxy name must be a non-empty string",
        "zh_CN": "代理名称必须是非空字符串",
    },
    ErrorCode.CONFIG_PROXY_NOT_FOUND: {
        "en": "Proxy not found: {name}",
        "zh_CN": "未找到代理：{name}",
    },
    ErrorCode.CONFIG_PROXY_INVALID: {
        "en": "Invalid proxy configuration: {name}",
        "zh_CN": "代理配置无效：{name}",
    },
    ErrorCode.PROXY_START_FAILED: {
        "en": "Failed to start proxy service",
        "zh_CN": "代理服务启动失败",
    },
    ErrorCode.PROXY_RESTART_FAILED: {
        "en": "Failed to restart proxy service",
        "zh_CN": "代理服务重启失败",
    },
    ErrorCode.PROXY_RECONFIGURE_FAILED: {
        "en": "Failed to reconfigure proxy service",
        "zh_CN": "代理服务重新配置失败",
    },
}

if set(_MESSAGES) != set(ErrorCode):
    raise RuntimeError("The application error catalog is incomplete")
if any(set(messages) != {"en", "zh_CN"} for messages in _MESSAGES.values()):
    raise RuntimeError("Every application error must have English and Chinese text")


def normalize_language(language: str | None) -> str:
    """Return the supported locale key for a configured language value."""

    normalized = (language or "en").strip().replace("-", "_").lower()
    return "zh_CN" if normalized.startswith("zh") else "en"


class LocalizedError(Exception):
    """Base class for errors with stable codes and structured parameters."""

    def __init__(
        self,
        code: ErrorCode | str,
        *,
        params: Mapping[str, object] | None = None,
        detail: str | None = None,
        line: int | None = None,
        errors: Sequence[LocalizedError] = (),
    ) -> None:
        try:
            stable_code = ErrorCode(code)
        except ValueError as exc:
            raise ValueError(f"Unknown application error code: {code}") from exc

        self.code = stable_code.value
        self.params = dict(params or {})
        self.detail = detail
        self.line = line
        self.errors = tuple(errors)
        super().__init__(self.localized("en"))

    def localized(self, language: str | None) -> str:
        """Render this error for a supported UI/CLI language."""

        locale = normalize_language(language)
        template = _MESSAGES[ErrorCode(self.code)][locale]
        try:
            message = template.format_map(self.params)
        except KeyError as exc:
            missing = exc.args[0]
            raise ValueError(
                f"Missing parameter {missing!r} for error code {self.code}"
            ) from exc

        if self.errors:
            message += "\n" + "\n".join(
                error.localized(locale) for error in self.errors
            )
        if self.line is not None:
            prefix = (
                f"第{self.line}行：" if locale == "zh_CN" else f"Line {self.line}: "
            )
            message = prefix + message
        return message

    def with_line(self, line: int) -> Self:
        """Copy the error while attaching batch-import line context."""

        return type(self)(
            self.code,
            params=self.params,
            detail=self.detail,
            line=line,
            errors=self.errors,
        )


class ProxyError(LocalizedError):
    """Base class for user-visible proxy operation errors."""

    @property
    def user_message(self) -> str:
        """Backward-compatible default English user message."""

        return self.localized("en")

    @property
    def log_message(self) -> str:
        """Technical detail for logs, falling back to the English message."""

        return self.detail or self.localized("en")


class ProxyStartError(ProxyError):
    """Starting or replacing the proxy listener failed."""


class ConfigError(ProxyError):
    """Proxy configuration is invalid."""


class ValidationError(LocalizedError):
    """A proxy field or batch input failed validation."""


def format_user_error(error: object, language: str | None) -> str:
    """Render a coded error at a GUI/CLI boundary.

    Unknown exceptions and already-rendered strings are passed through so the
    boundary can also handle unexpected failures without hiding diagnostics.
    """

    if isinstance(error, LocalizedError):
        return error.localized(language)
    return str(error)


def format_cli_error(
    error: object,
    language: str | None,
    *,
    fatal: bool = False,
) -> str:
    """Render a complete, consistently localized CLI error line."""

    locale = normalize_language(language)
    if locale == "zh_CN":
        prefix = "致命错误：" if fatal else "错误："
    else:
        prefix = "Fatal error: " if fatal else "Error: "
    return prefix + format_user_error(error, locale)


__all__ = [
    "ConfigError",
    "ErrorCode",
    "LocalizedError",
    "ProxyError",
    "ProxyStartError",
    "ValidationError",
    "format_cli_error",
    "format_user_error",
    "normalize_language",
]
