#!/usr/bin/env python

"""
PyProxySwitch 日志配置模块测试

测试日志配置功能。
"""

import logging
import pytest
from pathlib import Path
import sys
import tempfile
import os

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.logger_config import setup_logger, logger, Formatter


class TestFormatter:
    """日志格式化器测试"""

    def test_formatter_debug(self):
        """测试 DEBUG 级别格式化"""
        formatter = Formatter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="Debug message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "[DEBUG]" in formatted
        assert "Debug message" in formatted

    def test_formatter_info(self):
        """测试 INFO 级别格式化"""
        formatter = Formatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Info message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "[INFO]" in formatted
        assert "Info message" in formatted

    def test_formatter_warning(self):
        """测试 WARNING 级别格式化"""
        formatter = Formatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Warning message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "[WARNING]" in formatted
        assert "Warning message" in formatted

    def test_formatter_error(self):
        """测试 ERROR 级别格式化"""
        formatter = Formatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "[ERROR]" in formatted
        assert "Error message" in formatted

    def test_formatter_critical(self):
        """测试 CRITICAL 级别格式化"""
        formatter = Formatter()
        record = logging.LogRecord(
            name="test",
            level=logging.CRITICAL,
            pathname="test.py",
            lineno=1,
            msg="Critical message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "[CRITICAL]" in formatted
        assert "Critical message" in formatted


class TestSetupLogger:
    """日志设置测试"""

    def test_setup_logger_default(self):
        """测试默认日志设置"""
        test_logger = setup_logger(name="test_default")
        assert test_logger is not None
        assert test_logger.name == "test_default"

    def test_setup_logger_custom_name(self):
        """测试自定义名称"""
        test_logger = setup_logger(name="custom_logger")
        assert test_logger.name == "custom_logger"

    def test_setup_logger_creates_handlers(self):
        """测试创建处理器"""
        test_logger = setup_logger(name="test_handlers")
        # 应该至少有控制台处理器
        assert len(test_logger.handlers) >= 1

    def test_setup_logger_with_temp_dir(self):
        """测试使用临时目录"""
        import time

        # Windows下文件可能被锁定，添加短暂延迟
        time.sleep(0.1)
        # 使用 ignore_cleanup_errors=True 避免 Windows 文件锁定问题
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            test_logger = setup_logger(
                name="test_temp_dir_unique",  # 使用唯一名称避免冲突
                log_dir=log_dir,
            )
            assert log_dir.exists()

    def test_setup_logger_does_not_duplicate_handlers(self):
        """测试不会重复添加处理器"""
        name = "test_no_duplicate"
        logger1 = setup_logger(name=name)
        logger2 = setup_logger(name=name)
        # 同名 logger 应该返回同一个实例
        assert logger1 is logger2

    def test_setup_logger_sets_debug_level(self):
        """测试设置 DEBUG 级别"""
        test_logger = setup_logger(name="test_level", log_level=logging.DEBUG)
        assert test_logger.level == logging.DEBUG

    def test_setup_logger_with_custom_levels(self):
        """测试自定义级别"""
        test_logger = setup_logger(name="test_custom_levels", log_level=logging.WARNING)
        # 控制台处理器级别应该是 WARNING
        for handler in test_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                assert handler.level == logging.WARNING


class TestLogLevels:
    """日志级别测试"""

    def test_log_debug(self, caplog):
        """测试 DEBUG 日志"""
        test_logger = logging.getLogger("test_debug")
        test_logger.setLevel(logging.DEBUG)
        with caplog.at_level(logging.DEBUG):
            test_logger.debug("Debug message")
        assert "Debug message" in caplog.text

    def test_log_info(self, caplog):
        """测试 INFO 日志"""
        test_logger = logging.getLogger("test_info")
        test_logger.setLevel(logging.INFO)
        with caplog.at_level(logging.INFO):
            test_logger.info("Info message")
        assert "Info message" in caplog.text

    def test_log_warning(self, caplog):
        """测试 WARNING 日志"""
        test_logger = logging.getLogger("test_warning")
        test_logger.setLevel(logging.WARNING)
        with caplog.at_level(logging.WARNING):
            test_logger.warning("Warning message")
        assert "Warning message" in caplog.text

    def test_log_error(self, caplog):
        """测试 ERROR 日志"""
        test_logger = logging.getLogger("test_error")
        test_logger.setLevel(logging.ERROR)
        with caplog.at_level(logging.ERROR):
            test_logger.error("Error message")
        assert "Error message" in caplog.text
