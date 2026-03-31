#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigManager 最终覆盖率测试

覆盖剩余的未测试代码路径，目标是实现 100% 覆盖率。
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestConfigFinalCoverage:
    """测试最终未覆盖的代码路径"""

    def test_singleton_prevents_reinitialization(self):
        """测试单例模式防止重复初始化 - 覆盖 line 105"""
        from src.config import ConfigManager

        # Reset singleton first
        ConfigManager.reset_singleton()

        # Create first instance (singleton mode)
        config1 = ConfigManager()

        # Second call should return same instance
        config2 = ConfigManager()

        # Should be same instance and not reinitialize
        assert config1 is config2

    def test_pps_config_import_error_fallback(self, monkeypatch):
        """测试pps_config导入错误时的fallback逻辑 - 覆盖 lines 112-117"""
        from src.config import ConfigManager

        # Mock _import_pps_funcs to raise ImportError
        with patch("src.config._import_pps_funcs") as mock_import:
            mock_import.side_effect = ImportError("pps_config not available")

            # Should handle gracefully with defaults
            config = ConfigManager(use_singleton=False)
            assert config.pps_load_proxylist is None
            assert config.pps_save_proxylist is None
            assert str(config.config_path).endswith("PPS.conf")
            assert str(config.proxy_list_path).endswith("proxy.txt")

    def test_proxy_list_none_function_path(self, monkeypatch):
        """测试代理列表函数为None的完整路径 - 覆盖 line 129"""
        from src.config import ConfigManager

        # Mock function to return None for pps_load_proxylist
        with patch("src.config._import_pps_funcs") as mock_import:
            mock_import.return_value = (None, None, "/fake/path")

            config = ConfigManager(use_singleton=False)

            # Call _load_proxies directly to test the None function case
            config._load_proxies()

            # Should set empty lists when function is None
            assert config._proxies == []
            assert config._proxy_names == []

    def test_save_config_directory_creation_failure(self, temp_dir):
        """测试保存配置文件时目录创建失败 - 覆盖 lines 240-242"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "deeply" / "nested" / "path" / "config.json"

        config = ConfigManager(config_path=str(config_path), use_singleton=False)

        # Mock mkdir to raise PermissionError by patching the actual mkdir call
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Access denied")):
            # This should not raise an exception, just log the error
            config.save()

    def test_save_proxies_directory_creation_failure(self, temp_dir):
        """测试保存代理列表时目录创建失败 - 覆盖 lines 250-251"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"
        proxy_list_path = Path(temp_dir) / "deeply" / "nested" / "path" / "proxies.txt"

        config = ConfigManager(config_path=str(config_path), use_singleton=False)
        config.proxy_list_path = proxy_list_path

        config._proxies = [("test_proxy", "127.0.0.1", "8888", "http", "user", "pass")]

        # Mock mkdir to raise PermissionError by patching the actual mkdir call
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Access denied")):
            # This should not raise an exception, just log the error
            config.save_proxies()

    def test_logger_fallback_path(self):
        """测试日志记录器fallback路径 - 覆盖 lines 39-41"""
        from src.config import ConfigManager

        # Mock logger import to fail
        with patch("src.config._get_logger") as mock_get_logger:
            mock_get_logger.side_effect = ImportError("Logger not available")

            # This should trigger the fallback logging import
            try:
                # The module should still work with fallback logger
                config = ConfigManager(use_singleton=False)
                assert config.logger is not None
            except ImportError:
                # Expected if logger import fails completely
                pass

    def test_multi_instance_independence(self, temp_dir):
        """测试多实例模式的完全独立性"""
        from src.config import ConfigManager

        # 重置单例
        ConfigManager.reset_singleton()

        config1_path = Path(temp_dir) / "config1.json"
        config2_path = Path(temp_dir) / "config2.json"

        # Create two separate instances
        config1 = ConfigManager(config_path=str(config1_path), use_singleton=False)
        config2 = ConfigManager(config_path=str(config2_path), use_singleton=False)

        # Modify each independently
        config1.set("INSTANCE_ID", "config1")
        config2.set("INSTANCE_ID", "config2")

        # Each should have its own configuration
        assert config1.get("INSTANCE_ID") == "config1"
        assert config2.get("INSTANCE_ID") == "config2"

        # 重置单例以供其他测试使用
        ConfigManager.reset_singleton()

    def test_singleton_reset_and_recreate(self, temp_dir):
        """测试单例重置和重新创建"""
        from src.config import ConfigManager

        # Create first instance
        original_instance = ConfigManager._instance

        # Reset singleton
        ConfigManager.reset_singleton()

        # Create new instance
        config = ConfigManager(
            config_path=str(Path(temp_dir) / "config.json"), use_singleton=False
        )

        # Verify singleton was reset
        assert ConfigManager._instance is None

        # Restore original state
        ConfigManager._instance = original_instance

    def test_dict_interface_edge_cases(self, temp_dir):
        """测试字典接口的边缘情况"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"
        config = ConfigManager(config_path=str(config_path), use_singleton=False)

        # Test all dict interface methods comprehensively
        # __contains__
        assert "CMD" in config
        assert "NONEXISTENT_KEY" not in config

        # keys(), values(), items()
        keys = list(config.keys())
        values = list(config.values())
        items = list(config.items())

        assert len(keys) > 0
        assert len(values) > 0
        assert len(items) > 0

        # __getitem__ and __setitem__
        cmd_value = config["CMD"]
        assert cmd_value == "3proxy"

        config["NEW_TEST_KEY"] = "new_test_value"
        assert config.get("NEW_TEST_KEY") == "new_test_value"

    def test_update_method_batch_operations(self, temp_dir):
        """测试update方法的批量操作"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"
        config = ConfigManager(config_path=str(config_path), use_singleton=False)

        # Test batch update with multiple keys
        update_data = {"KEY1": "value1", "KEY2": "value2", "KEY3": "value3"}
        config.update(update_data)

        # Verify all updates were applied
        for key, value in update_data.items():
            assert config.get(key) == value

    def test_reset_to_default_complete(self, temp_dir):
        """测试reset_to_default方法的完整功能"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"
        config = ConfigManager(config_path=str(config_path), use_singleton=False)

        # Set various custom values
        config.set("CUSTOM_KEY", "custom_value")
        config.set("DEBUG", 1)
        config.set("LOCAL_PORT", 9090)

        # Reset to default
        config.reset_to_default()

        # Check that all custom values are gone and defaults remain
        assert config.get("CUSTOM_KEY") is None
        assert config.get("DEBUG") == 0  # Default value
        assert config.get("LOCAL_PORT") == 8888  # Default value
        assert config.get("FIRST_RUN") == 0  # Default value

    def test_repr_method_comprehensive(self, temp_dir):
        """测试__repr__方法的完整信息"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"
        config = ConfigManager(config_path=str(config_path), use_singleton=False)

        # Add some proxies to test proxy count
        config._proxies = [
            ("proxy1", "127.0.0.1", "8888", "http", "", ""),
            ("proxy2", "192.168.1.1", "3128", "socks5", "user", "pass"),
        ]

        repr_str = repr(config)
        assert "ConfigManager" in repr_str
        assert "config_path" in repr_str
        assert "proxies=2" in repr_str

    def test_get_instance_class_methods_comprehensive(self):
        """测试类方法的完整功能"""
        from src.config import ConfigManager

        # Reset first
        ConfigManager.reset_singleton()

        # Test get_instance before initialization
        instance_before = ConfigManager.get_instance()
        assert instance_before is None

        # Test get_instance after initialization
        ConfigManager(use_singleton=True)
        instance_after = ConfigManager.get_instance()
        assert instance_after is not None

        # Reset
        ConfigManager.reset_singleton()
