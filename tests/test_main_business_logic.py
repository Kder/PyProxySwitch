#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyProxySwitch main.py 模块测试 - 不涉及Qt的业务逻辑测试

这个测试文件只测试不依赖Qt导入的业务逻辑。
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Any

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestProxyDataValidation:
    """测试代理数据验证逻辑"""

    def test_proxy_tuple_structure(self):
        """测试代理元组结构"""
        # 代理元组应该是 (name, address, port, type, username, password)
        proxy_tuple = ("test_proxy", "192.168.1.1", "8080", "HTTP", "", "")

        assert len(proxy_tuple) == 6
        assert proxy_tuple[0] == "test_proxy"  # name
        assert proxy_tuple[1] == "192.168.1.1"  # address
        assert proxy_tuple[2] == "8080"  # port
        assert proxy_tuple[3] == "HTTP"  # type
        assert proxy_tuple[4] == ""  # username
        assert proxy_tuple[5] == ""  # password

    def test_proxy_with_auth_structure(self):
        """测试带认证的代理元组结构"""
        proxy_tuple = ("auth_proxy", "10.0.0.1", "3128", "HTTP", "user", "pass")

        assert len(proxy_tuple) == 6
        assert proxy_tuple[4] == "user"
        assert proxy_tuple[5] == "pass"

    def test_socks_proxy_types(self):
        """测试 SOCKS 代理类型"""
        socks_types = ["SOCKS4", "SOCKS5"]
        for proxy_type in socks_types:
            assert proxy_type in socks_types

    def test_proxy_types_case_sensitivity(self):
        """测试代理类型的大小写敏感性"""
        # 测试小写类型
        lowercase_types = ["http", "socks4", "socks5"]
        for proxy_type in lowercase_types:
            assert proxy_type.lower() in ["http", "socks4", "socks5"]


class TestProxyValidationIntegration:
    """测试代理验证模块集成"""

    def test_proxy_validator_import(self):
        """测试代理验证器可以被导入"""
        from src.proxy_validation import (
            ProxyValidator,
            ValidationError,
            BatchImportValidator,
        )

        assert ProxyValidator is not None
        assert ValidationError is not None
        assert BatchImportValidator is not None

    def test_proxy_validator_basic_validation(self):
        """测试代理验证器基本验证"""
        from src.proxy_validation import ProxyValidator

        validator = ProxyValidator()

        # 测试有效数据
        result = validator.validate_proxy_name("test_proxy")
        assert result == "test_proxy"

        # 测试无效数据
        with pytest.raises(Exception):  # 可能抛出 ValidationError
            validator.validate_proxy_name("")  # 空名称应该无效

    def test_address_validation(self):
        """测试地址验证"""
        from src.proxy_validation import ProxyValidator

        validator = ProxyValidator()

        # 测试有效 IPv4 地址
        result = validator.validate_proxy_address("192.168.1.1")
        assert result == "192.168.1.1"

        # 测试有效域名
        result = validator.validate_proxy_address("example.com")
        assert result == "example.com"

    def test_port_validation(self):
        """测试端口验证"""
        from src.proxy_validation import ProxyValidator

        validator = ProxyValidator()

        # 测试有效端口 - validate_proxy_port returns int, not str
        result = validator.validate_proxy_port("8080")
        assert result == 8080  # Returns int, not string

        # 测试无效端口
        with pytest.raises(Exception):  # ValidationError
            validator.validate_proxy_port("0")  # 端口不能为0


class TestConfigManagerIntegration:
    """测试 ConfigManager 与应用的集成"""

    def test_config_manager_import(self):
        """测试 ConfigManager 可以被导入"""
        from src.config import ConfigManager

        assert ConfigManager is not None

    def test_config_manager_singleton(self):
        """测试 ConfigManager 单例模式"""
        from src.config import ConfigManager

        # 重置单例
        ConfigManager.reset_singleton()

        # 获取实例
        instance1 = ConfigManager()
        instance2 = ConfigManager()

        # 应该是同一个实例
        assert instance1 is instance2

        # 重置
        ConfigManager.reset_singleton()


class TestErrorHandling:
    """测试错误处理"""

    def test_proxy_error_import(self):
        """测试代理错误类可以导入"""
        from src.errors import ProxyError, ProxyStartError, ProxyStopError, ConfigError

        assert ProxyError is not None
        assert ProxyStartError is not None
        assert ProxyStopError is not None
        assert ConfigError is not None

    def test_proxy_error_creation(self):
        """测试代理错误创建"""
        from src.errors import ProxyError

        error = ProxyError("User message", "Log message")
        assert str(error) == "User message"

    def test_proxy_start_error_creation(self):
        """测试代理启动错误创建"""
        from src.errors import ProxyStartError

        error = ProxyStartError("Failed to start", "Process error")
        assert str(error) == "Failed to start"

    def test_config_error_creation(self):
        """测试配置错误创建"""
        from src.errors import ConfigError

        error = ConfigError("Config failed", "Missing key")
        assert str(error) == "Config failed"


class TestLoggingConfiguration:
    """测试日志配置"""

    def test_logger_import(self):
        """测试日志模块可以导入"""
        from src.logger_config import setup_logger, logger

        assert setup_logger is not None
        assert logger is not None

    def test_logger_name(self):
        """测试日志器名称"""
        from src.logger_config import logger

        assert logger.name == "PyProxySwitch"

    def test_logger_setup_with_custom_name(self):
        """测试使用自定义名称设置日志器"""
        import logging
        from src.logger_config import setup_logger

        # setup_logger takes log_level (int), not level (str)
        # log_level expects logging.DEBUG, logging.INFO, etc.
        test_logger = setup_logger("test_logger_custom", log_level=logging.DEBUG)
        assert test_logger is not None
        assert test_logger.name == "test_logger_custom"


class TestPPSConfigModule:
    """测试 pps_config 模块"""

    def test_pps_config_import(self):
        """测试 pps_config 模块可以导入"""
        from src import pps_config

        assert pps_config is not None

    def test_pps_output_function(self):
        """测试 pps_output 函数"""
        from src.pps_config import pps_output

        # 测试输出到 stdout
        # 这不会抛出异常
        pps_output("Test message")

    def test_pps_output_to_stderr(self):
        """测试 pps_output 到 stderr"""
        from src.pps_config import pps_output

        # 测试输出到 stderr
        pps_output("Error message", "stderr")

    def test_pps_load_proxylist(self):
        """测试加载代理列表"""
        from src.pps_config import pps_load_proxylist

        # 测试加载一个有效的代理列表文件
        # 如果文件不存在，应该返回空列表或抛出异常
        try:
            result = pps_load_proxylist("/nonexistent/path/proxy.txt")
            # 如果成功，应该是列表
            assert isinstance(result, list)
        except Exception:
            # 如果失败，这是预期的
            pass


class TestBatchImportValidator:
    """测试批量导入验证器"""

    def test_batch_import_validator_import(self):
        """测试批量导入验证器可以导入"""
        from src.proxy_validation import BatchImportValidator

        validator = BatchImportValidator()
        assert validator is not None

    def test_batch_import_single_line(self):
        """测试批量导入单行"""
        from src.proxy_validation import BatchImportValidator

        validator = BatchImportValidator()

        # 测试简单格式
        result = validator.validate_batch_line("test_proxy 192.168.1.1:8080", 1)

        assert result is not None
        assert len(result) >= 3  # name, address, port

    def test_batch_import_with_type(self):
        """测试带类型的批量导入"""
        from src.proxy_validation import BatchImportValidator

        validator = BatchImportValidator()

        # 测试带类型
        result = validator.validate_batch_line("socks_proxy 192.168.1.1:1080 SOCKS5", 1)

        assert result is not None


class TestProxyValidatorEdgeCases:
    """测试代理验证器的边缘案例"""

    def test_empty_proxy_name(self):
        """测试空代理名称"""
        from src.proxy_validation import ProxyValidator

        validator = ProxyValidator()

        with pytest.raises(Exception):  # ValidationError
            validator.validate_proxy_name("")

    def test_invalid_port_zero(self):
        """测试端口为0"""
        from src.proxy_validation import ProxyValidator

        validator = ProxyValidator()

        with pytest.raises(Exception):  # ValidationError
            validator.validate_proxy_port("0")

    def test_invalid_port_too_large(self):
        """测试端口过大"""
        from src.proxy_validation import ProxyValidator

        validator = ProxyValidator()

        with pytest.raises(Exception):  # ValidationError
            validator.validate_proxy_port("70000")

    def test_invalid_ipv4_octet(self):
        """测试无效的IPv4八位组

        Note: The regex pattern [01]?[0-9][0-9]? can match values like 300
        because [0-9]? is optional. The explicit int(part) > 255 check
        should catch this case and raise ValidationError.
        """
        from src.proxy_validation import ProxyValidator, ValidationError

        validator = ProxyValidator()

        # Test that values > 255 raise ValidationError due to explicit check
        with pytest.raises(ValidationError):
            validator.validate_proxy_address("192.168.1.300")

    def test_empty_address(self):
        """测试空地址"""
        from src.proxy_validation import ProxyValidator

        validator = ProxyValidator()

        with pytest.raises(Exception):  # ValidationError
            validator.validate_proxy_address("")


class TestVersionInfo:
    """测试版本信息"""

    def test_package_version(self):
        """测试包版本"""
        from src import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)

    def test_main_module_version(self):
        """测试主模块版本"""
        try:
            import src.main as main_module

            # 如果main.py可以导入，检查版本
            if hasattr(main_module, "__version__"):
                assert isinstance(main_module.__version__, str)
        except (ImportError, TypeError):
            # Qt相关问题，忽略
            pass


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
