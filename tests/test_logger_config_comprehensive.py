#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyProxySwitch 日志配置模块全面测试

这个测试文件专门用于覆盖 logger_config.py 中未覆盖的代码路径，
目标是实现 100% 的测试覆盖率。
"""

import logging
import logging.handlers
import pytest
import sys
import tempfile
import warnings
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Generator

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestLoggerConfigComprehensive:
    """日志配置模块全面测试"""

    @pytest.fixture
    def temp_dir(self) -> Generator[Path, None, None]:
        """创建临时目录用于测试"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_setup_logger_with_existing_handlers(self):
        """测试 setup_logger 在已有处理器时的行为 (lines 56-61)"""
        logger_name = "test_existing_handlers"
        logger = logging.getLogger(logger_name)

        # 清除现有处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # 添加一个现有的控制台处理器
        existing_handler = logging.StreamHandler()
        existing_handler.setLevel(logging.WARNING)
        logger.addHandler(existing_handler)

        # 调用 setup_logger
        from src.logger_config import setup_logger
        setup_logger(name=logger_name, log_level=logging.DEBUG)

        # 验证现有处理器的级别被更新
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                assert handler.level == logging.DEBUG

    def test_setup_logger_config_manager_exception(self):
        """测试 setup_logger 中配置管理器异常的处理 (lines 77-87)"""
        from src.logger_config import setup_logger

        with patch.dict('sys.modules', {'src.config': None}):
            # 这应该触发异常处理路径
            logger = setup_logger(name="test_config_exception")
            assert logger is not None
            assert logger.name == "test_config_exception"

    def test_setup_logger_with_custom_config_path(self):
        """测试 setup_logger 使用自定义配置路径 (lines 77-87)"""
        from src.logger_config import setup_logger

        temp_config = {"LOG_PATH": "/custom/path"}
        mock_config_manager = MagicMock()
        mock_config_manager.get.return_value = "/custom/path"

        with patch('src.config.ConfigManager', return_value=mock_config_manager):
            with patch('pathlib.Path.mkdir') as mock_mkdir:
                logger = setup_logger(name="test_custom_config_path")
                assert logger is not None

    def test_setup_logger_cannot_create_log_dir(self):
        """测试无法创建日志目录时的回退机制 (lines 90-97)"""
        from src.logger_config import setup_logger

        with patch('pathlib.Path.mkdir', side_effect=Exception("Permission denied")):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                logger = setup_logger(name="test_cannot_create_dir")

                # 应该发出警告
                assert len(w) > 0
                assert "无法创建日志目录" in str(w[0].message)

    def test_setup_logger_with_none_log_dir_and_config_exception(self):
        """测试 log_dir 为 None 且配置管理器抛出异常的情况 (lines 75-87)"""
        from src.logger_config import setup_logger

        # 模拟配置管理器抛出异常
        with patch('src.config.ConfigManager', side_effect=Exception("Config error")):
            logger = setup_logger(name="test_config_exception_fallback")

            # 应该成功创建 logger，使用默认路径
            assert logger is not None
            assert logger.name == "test_config_exception_fallback"

    def test_update_log_path_function(self):
        """测试 update_log_path 函数 (lines 113-161)"""
        from src.logger_config import update_log_path

        logger_name = "PyProxySwitch"
        logger = logging.getLogger(logger_name)

        # 清除现有处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # 添加一个文件处理器
        temp_handler = logging.handlers.RotatingFileHandler(
            "temp.log", maxBytes=1024, backupCount=1
        )
        logger.addHandler(temp_handler)

        # 确保至少有一个文件处理器
        assert len([h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]) > 0

        with tempfile.TemporaryDirectory() as tmpdir:
            new_log_dir = Path(tmpdir) / "new_logs"

            # 更新日志路径
            update_log_path(new_log_dir)

            # 验证新的文件处理器被添加
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
            assert len(file_handlers) > 0

            # 验证新的日志文件路径
            new_log_file = new_log_dir / "PyProxySwitch.log"
            assert any(str(new_log_file) in str(handler.baseFilename) for handler in file_handlers)

    def test_update_log_path_with_config_manager(self):
        """测试 update_log_path 使用配置管理器 (lines 129-139)"""
        from src.logger_config import update_log_path

        mock_config_manager = MagicMock()
        mock_config_manager.get.return_value = "/custom/log/path"

        with patch('src.config.ConfigManager', return_value=mock_config_manager):
            with patch('pathlib.Path.mkdir'):
                update_log_path()  # new_log_dir is None, should use config

    def test_update_log_path_config_manager_exception(self):
        """测试 update_log_path 中配置管理器异常 (lines 129-139)"""
        from src.logger_config import update_log_path

        with patch('src.config.ConfigManager', side_effect=Exception("Config error")):
            # 这应该触发异常处理路径
            update_log_path()  # Should not raise exception

    def test_update_log_path_cannot_create_dir(self):
        """测试 update_log_path 无法创建目录时的回退 (lines 141-148)"""
        from src.logger_config import update_log_path

        with patch('pathlib.Path.mkdir', side_effect=Exception("Permission denied")):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                update_log_path(Path("/invalid/path"))

                # 应该发出警告
                assert len(w) > 0
                assert "无法创建日志目录" in str(w[0].message)

    def test_setup_logger_file_handler_properties(self):
        """测试文件处理器的属性设置"""
        from src.logger_config import setup_logger

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "test_logs"
            logger = setup_logger(
                name="test_file_handler_props",
                log_dir=log_dir,
                max_bytes=1024,
                backup_count=5
            )

            # 查找文件处理器
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
            assert len(file_handlers) > 0

            file_handler = file_handlers[0]
            assert file_handler.maxBytes == 1024
            assert file_handler.backupCount == 5
            assert file_handler.level == logging.DEBUG
            assert file_handler.encoding == 'utf-8'

    def test_formatter_with_unknown_level(self):
        """测试格式化器处理未知日志级别"""
        from src.logger_config import Formatter

        formatter = Formatter()

        # 创建一个自定义级别的日志记录
        custom_level = 25  # 介于 INFO (20) 和 WARNING (30) 之间
        record = logging.LogRecord(
            name="test",
            level=custom_level,
            pathname="test.py",
            lineno=1,
            msg="Custom level message",
            args=(),
            exc_info=None,
        )

        # 这应该使用默认格式或第一个可用的格式
        formatted = formatter.format(record)
        assert "Custom level message" in formatted

    def test_setup_logger_with_all_custom_parameters(self):
        """测试 setup_logger 使用所有自定义参数"""
        from src.logger_config import setup_logger

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "custom_logs"

            logger = setup_logger(
                name="test_all_params",
                log_dir=log_dir,
                log_level=logging.WARNING,
                max_bytes=2048,
                backup_count=7
            )

            assert logger.name == "test_all_params"
            assert logger.level == logging.DEBUG  # 内部设置为 DEBUG

            # 检查控制台处理器级别
            console_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
            assert len(console_handlers) > 0
            assert console_handlers[0].level == logging.WARNING

    def test_logger_hierarchy_and_propagation(self):
        """测试日志器层次结构和传播"""
        from src.logger_config import setup_logger

        # 创建父子日志器
        parent_logger = setup_logger(name="test_parent")
        child_logger = logging.getLogger("test_parent.child")

        # 验证层次结构
        assert child_logger.parent == parent_logger

    def test_multiple_setup_logger_calls_same_name(self):
        """测试多次调用 setup_logger 使用相同名称"""
        from src.logger_config import setup_logger

        logger1 = setup_logger(name="test_same_name", log_level=logging.INFO)
        logger2 = setup_logger(name="test_same_name", log_level=logging.DEBUG)

        # 应该是同一个实例
        assert logger1 is logger2

        # 级别应该被更新
        console_handlers = [h for h in logger1.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
        if console_handlers:
            assert console_handlers[0].level == logging.DEBUG


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])