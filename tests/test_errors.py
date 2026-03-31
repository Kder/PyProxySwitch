#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyProxySwitch 异常模块测试

测试自定义异常类的功能。
"""

import pytest
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.errors import ProxyError, ProxyStartError, ProxyStopError, ConfigError


class TestProxyError:
    """基础代理异常测试"""

    def test_create_with_user_message(self):
        """测试使用用户消息创建异常"""
        err = ProxyError("User friendly message")
        assert str(err) == "User friendly message"
        assert err.user_message == "User friendly message"
        assert err.log_message == "User friendly message"

    def test_create_with_both_messages(self):
        """测试使用用户消息和日志消息创建异常"""
        err = ProxyError("User message", "Log details")
        assert err.user_message == "User message"
        assert err.log_message == "Log details"

    def test_inherits_from_exception(self):
        """测试继承自 Exception"""
        err = ProxyError("test")
        assert isinstance(err, Exception)

    def test_can_be_caught(self):
        """测试可以被捕获"""
        with pytest.raises(ProxyError):
            raise ProxyError("test error")


class TestProxyStartError:
    """代理启动错误测试"""

    def test_create(self):
        """测试创建异常"""
        err = ProxyStartError("Failed to start proxy")
        assert str(err) == "Failed to start proxy"

    def test_inherits_from_proxy_error(self):
        """测试继承自 ProxyError"""
        err = ProxyStartError("test")
        assert isinstance(err, ProxyError)
        assert isinstance(err, Exception)

    def test_can_catch_as_proxy_error(self):
        """测试可以捕获为 ProxyError"""
        with pytest.raises(ProxyError):
            raise ProxyStartError("start error")

    def test_has_user_and_log_messages(self):
        """测试用户和日志消息"""
        err = ProxyStartError("Cannot find command", "File not found at path")
        assert err.user_message == "Cannot find command"
        assert err.log_message == "File not found at path"


class TestProxyStopError:
    """代理停止错误测试"""

    def test_create(self):
        """测试创建异常"""
        err = ProxyStopError("Failed to stop proxy")
        assert str(err) == "Failed to stop proxy"

    def test_inherits_from_proxy_error(self):
        """测试继承自 ProxyError"""
        err = ProxyStopError("test")
        assert isinstance(err, ProxyError)
        assert isinstance(err, Exception)

    def test_can_catch_as_proxy_error(self):
        """测试可以捕获为 ProxyError"""
        with pytest.raises(ProxyError):
            raise ProxyStopError("stop error")


class TestConfigError:
    """配置错误测试"""

    def test_create(self):
        """测试创建异常"""
        err = ConfigError("Invalid config")
        assert str(err) == "Invalid config"

    def test_inherits_from_proxy_error(self):
        """测试继承自 ProxyError"""
        err = ConfigError("test")
        assert isinstance(err, ProxyError)
        assert isinstance(err, Exception)

    def test_can_catch_as_proxy_error(self):
        """测试可以捕获为 ProxyError"""
        with pytest.raises(ProxyError):
            raise ConfigError("config error")

    def test_multiple_messages(self):
        """测试多种消息组合"""
        err = ConfigError(
            "Config value invalid", "Key 'port' must be between 1 and 65535"
        )
        assert err.user_message == "Config value invalid"
        assert err.log_message == "Key 'port' must be between 1 and 65535"


class TestExceptionInheritance:
    """异常继承层次测试"""

    def test_all_inherit_from_base(self):
        """测试所有异常都继承自 ProxyError"""
        errors = [ProxyStartError("test"), ProxyStopError("test"), ConfigError("test")]
        for err in errors:
            assert isinstance(err, ProxyError)

    def test_catch_base_catches_all(self):
        """测试捕获基类可以捕获所有子类"""
        caught_count = 0

        try:
            raise ProxyStartError("start")
        except ProxyError:
            caught_count += 1

        try:
            raise ProxyStopError("stop")
        except ProxyError:
            caught_count += 1

        try:
            raise ConfigError("config")
        except ProxyError:
            caught_count += 1

        assert caught_count == 3

    def test_catch_specific_only(self):
        """测试只捕获特定异常"""
        # ProxyStartError 不应该被 ProxyStopError 捕获
        with pytest.raises(ProxyStartError):
            try:
                raise ProxyStartError("start")
            except ProxyStopError:
                pass

        # ConfigError 不应该被 ProxyStartError 捕获
        with pytest.raises(ConfigError):
            try:
                raise ConfigError("config")
            except ProxyStartError:
                pass
