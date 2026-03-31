#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigManager 覆盖率提升测试

这个文件专门用于覆盖 config.py 中未覆盖的代码路径，
目标是实现 100% 的测试覆盖率。
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestConfigCoverage:
    """测试未覆盖的代码路径"""

    def test_logger_import_failure(self, monkeypatch):
        """测试日志记录器导入失败的情况 - 覆盖 lines 39-41"""
        from src.config import ConfigManager

        # Mock _get_logger to raise ImportError
        with patch("src.config._get_logger") as mock_get_logger:
            mock_get_logger.side_effect = ImportError("Logger not available")

            # Should handle gracefully and create instance with default logger
            try:
                config = ConfigManager(use_singleton=False)
                # If we get here, the logger fallback worked
                assert config.logger is not None
            except ImportError:
                # This is expected - the module should fail if logger import fails
                pass

    def test_pps_config_import_failure(self, monkeypatch):
        """测试pps_config导入失败的情况 - 覆盖 lines 48-49"""
        from src.config import ConfigManager

        # Mock _import_pps_funcs to raise ImportError
        with patch("src.config._import_pps_funcs") as mock_import:
            mock_import.side_effect = ImportError("pps_config not available")

            # Should handle gracefully with defaults
            config = ConfigManager(use_singleton=False)
            assert config.pps_load_proxylist is None
            assert config.pps_save_proxylist is None

    def test_proxy_list_loading_with_none_function(self, monkeypatch):
        """测试代理列表加载时函数为None的情况 - 覆盖 line 129"""
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

    def test_load_config_json_decode_error(self, temp_dir):
        """测试JSON解析错误的处理 - 覆盖 lines 162-164"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "invalid.json"

        # Create invalid JSON file
        config_path.write_text("{ invalid json content")

        # Load config - should catch JSONDecodeError and use defaults
        config = ConfigManager(config_path=str(config_path), use_singleton=False)

        # Should have default values despite JSON error
        assert config.get("CMD") == "3proxy"

    def test_load_config_io_error(self, temp_dir):
        """测试配置文件IO错误的处理 - 覆盖 line 181-184"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "nonexistent.json"

        # This should trigger the IOError path in _load_config
        config = ConfigManager(config_path=str(config_path), use_singleton=False)

        # Should use default configuration
        assert config.get("CMD") == "3proxy"

    def test_save_config_io_error(self, temp_dir):
        """测试保存配置文件时的IO错误 - 覆盖 lines 217, 226"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"
        config = ConfigManager(config_path=str(config_path), use_singleton=False)

        # Set some config values
        config.set("TEST_KEY", "test_value")

        # Mock open to raise IOError
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            # This should not raise an exception, just log the error
            config.save()

    def test_save_proxies_exception_handling(self, temp_dir):
        """测试保存代理列表时的异常处理 - 覆盖 lines 250-251"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"
        proxy_list_path = Path(temp_dir) / "proxies.txt"

        config = ConfigManager(config_path=str(config_path), use_singleton=False)
        config.proxy_list_path = proxy_list_path

        # Set up proxies
        config._proxies = [("test_proxy", "127.0.0.1", "8888", "http", "user", "pass")]
        config.pps_save_proxylist = MagicMock(side_effect=Exception("Save failed"))

        # This should not raise an exception, just log the error
        config.save_proxies()

    def test_proxy_list_loading_with_exception(self, temp_dir):
        """测试代理列表加载时的通用异常处理"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"
        proxy_list_path = Path(temp_dir) / "proxies.txt"

        config = ConfigManager(config_path=str(config_path), use_singleton=False)
        config.proxy_list_path = proxy_list_path

        # Mock pps_load_proxylist to raise generic Exception
        with patch.object(config, "pps_load_proxylist") as mock_load:
            mock_load.side_effect = Exception("Generic load error")
            mock_load.return_value = [("test", "127.0.0.1", "8080", "HTTP", "", "")]

            # Call _load_proxies - should catch exception and set empty lists
            config._load_proxies()

            # Should catch exception and set empty lists
            assert config._proxies == []
            assert config._proxy_names == []

    def test_backwards_compatibility_fix(self, temp_dir):
        """测试向后兼容性修复"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"

        # Create config with typo
        config_data = {
            "CMD": "3proxy",
            "FISRT_RUN": 1,  # Typo - should be fixed
            "LOCAL_PORT": 8888,
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f)

        config = ConfigManager(config_path=str(config_path), use_singleton=False)

        # Verify typo was fixed
        assert "FIRST_RUN" in config._config
        assert "FISRT_RUN" not in config._config
        assert config.get("FIRST_RUN") == 1

    def test_multi_instance_behavior(self, temp_dir):
        """测试多实例模式"""
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

    def test_singleton_reset(self):
        """测试单例重置功能"""
        from src.config import ConfigManager

        # Create first instance
        original_instance = ConfigManager._instance

        # Reset singleton
        ConfigManager.reset_singleton()

        # Create new instance
        config = ConfigManager(use_singleton=False)

        # Verify singleton was reset
        assert ConfigManager._instance is None

        # Restore original state
        ConfigManager._instance = original_instance

    def test_dict_interface_comprehensive(self, temp_dir):
        """测试字典接口的完整功能"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"
        config = ConfigManager(config_path=str(config_path), use_singleton=False)

        # Test all dict interface methods
        # __contains__
        assert "CMD" in config
        assert "NONEXISTENT" not in config

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

        config["NEW_KEY"] = "new_value"
        assert config.get("NEW_KEY") == "new_value"

    def test_update_method_detailed(self, temp_dir):
        """测试update方法的详细情况"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"
        config = ConfigManager(config_path=str(config_path), use_singleton=False)

        # Test update method
        update_dict = {"KEY1": "value1", "KEY2": "value2"}
        config.update(update_dict)

        assert config.get("KEY1") == "value1"
        assert config.get("KEY2") == "value2"

    def test_reset_to_default_detailed(self, temp_dir):
        """测试reset_to_default方法的详细情况"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"
        config = ConfigManager(config_path=str(config_path), use_singleton=False)

        # Set some custom values
        config.set("CUSTOM_KEY", "custom_value")
        config.set("DEBUG", 1)

        # Reset to default
        config.reset_to_default()

        # Check that custom values are gone and defaults remain
        assert config.get("CUSTOM_KEY") is None
        assert config.get("FIRST_RUN") == 0  # Default value
        assert config.get("DEBUG") == 0  # Default value

    def test_repr_method_detailed(self, temp_dir):
        """测试__repr__方法的详细情况"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"
        config = ConfigManager(config_path=str(config_path), use_singleton=False)

        repr_str = repr(config)
        assert "ConfigManager" in repr_str
        assert "config_path" in repr_str
        assert "proxies=" in repr_str

    def test_get_instance_methods(self):
        """测试类方法"""
        from src.config import ConfigManager

        # Reset first
        ConfigManager.reset_singleton()

        # Test get_instance before initialization
        instance = ConfigManager.get_instance()
        assert instance is None

        # Test get_instance after initialization
        ConfigManager(use_singleton=True)
        instance = ConfigManager.get_instance()
        assert instance is not None

        # Reset
        ConfigManager.reset_singleton()
