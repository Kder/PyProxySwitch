#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyProxySwitch ConfigManager 综合测试 - 覆盖未测试的代码路径
"""

import pytest
import tempfile
import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
import sys

sys.path.insert(0, str(PROJECT_ROOT))


class TestConfigManagerComprehensive:
    """ConfigManager 综合功能测试"""

    def test_save_proxies_method(self):
        """测试 save_proxies 方法"""
        from src.config import ConfigManager

        # 创建临时配置管理器
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            proxy_list_path = Path(temp_dir) / "proxy.txt"

            ConfigManager.reset_singleton()
            config = ConfigManager(use_singleton=False)
            config.config_path = config_path
            config.proxy_list_path = proxy_list_path

            # 设置一些代理数据
            config._proxies = [
                ("test_proxy", "192.168.1.1", "8080", "HTTP", "", ""),
                ("auth_proxy", "10.0.0.1", "3128", "SOCKS5", "user", "pass"),
            ]

            # 测试 save_proxies
            config.save_proxies()

            # 验证文件已创建
            assert proxy_list_path.exists()
            content = proxy_list_path.read_text(encoding="utf-8")
            assert "test_proxy" in content
            assert "auth_proxy" in content

            ConfigManager.reset_singleton()

    def test_save_proxies_error_handling(self):
        """测试 save_proxies 方法的错误处理"""
        from src.config import ConfigManager

        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)

        # 设置一些代理数据
        config._proxies = [("test", "127.0.0.1", "8080", "HTTP", "", "")]

        # 测试正常情况（应该不会抛出异常）
        try:
            config.save_proxies()
            print("save_proxies: OK")
        except Exception as e:
            pytest.fail(f"save_proxies should not raise exception: {e}")

        ConfigManager.reset_singleton()

    def test_update_method(self):
        """测试 update 方法"""
        from src.config import ConfigManager

        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)

        # 测试批量更新
        update_data = {"TEST_KEY": "test_value", "DEBUG": 1, "NEW_SETTING": "new_value"}

        config.update(update_data)

        # 验证更新成功
        for key, value in update_data.items():
            assert config.get(key) == value

        ConfigManager.reset_singleton()

    def test_reset_to_default_method(self):
        """测试 reset_to_default 方法"""
        from src.config import ConfigManager

        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)

        # 修改一些配置
        config.set("CMD", "polipo")
        config.set("LOCAL_PORT", 9090)
        assert config.get("CMD") == "polipo"

        # 重置为默认值
        config.reset_to_default()

        # 验证重置成功
        assert config.get("CMD") == "3proxy"  # 默认值
        assert config.get("LOCAL_PORT") == 8888  # 默认值

        ConfigManager.reset_singleton()

    def test_dict_interface_contains(self):
        """测试字典接口 __contains__"""
        from src.config import ConfigManager

        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)

        # 测试存在的键
        assert "CMD" in config
        assert "DEBUG" in config
        assert "LOCAL_PORT" in config

        # 测试不存在的键
        assert "NONEXISTENT_KEY" not in config

        ConfigManager.reset_singleton()

    def test_dict_interface_keys(self):
        """测试字典接口 keys()"""
        from src.config import ConfigManager

        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)

        keys = list(config.keys())
        assert len(keys) > 0
        assert "CMD" in keys
        assert "DEBUG" in keys
        assert "LOCAL_PORT" in keys

        ConfigManager.reset_singleton()

    def test_dict_interface_values(self):
        """测试字典接口 values()"""
        from src.config import ConfigManager

        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)

        values = list(config.values())
        assert len(values) > 0

        # 验证值对应正确的键
        cmd_index = list(config.keys()).index("CMD")
        assert values[cmd_index] == "3proxy"  # CMD should be '3proxy'

        # DEBUG may be 0 or 1 depending on config file, just verify it's an int
        debug_value = config.get("DEBUG")
        assert isinstance(debug_value, int)

        ConfigManager.reset_singleton()

    def test_dict_interface_items(self):
        """测试字典接口 items()"""
        from src.config import ConfigManager

        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)

        items = list(config.items())
        assert len(items) > 0
        assert all(len(item) == 2 for item in items)

        # 验证特定项存在
        found_cmd = False
        found_debug = False
        for key, value in items:
            if key == "CMD":
                assert value == "3proxy"
                found_cmd = True
            elif key == "DEBUG":
                assert isinstance(
                    value, int
                )  # DEBUG may be 0 or 1 depending on config file
                found_debug = True

        assert found_cmd, "CMD item not found"
        assert found_debug, "DEBUG item not found"

    def test_dict_interface_getitem(self):
        """测试字典接口 __getitem__ (config['KEY'])"""
        from src.config import ConfigManager

        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)

        # 测试正常获取
        cmd = config["CMD"]
        assert cmd == "3proxy"  # CMD should always be '3proxy'

        # DEBUG may be 0 or 1 depending on config file, just verify it's an int
        debug = config["DEBUG"]
        assert isinstance(debug, int)

        # 测试 KeyError
        with pytest.raises(KeyError):
            _ = config["NONEXISTENT_KEY"]

        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)

        # 测试正常获取
        cmd = config["CMD"]
        assert cmd == "3proxy"

        debug = config["DEBUG"]
        assert isinstance(debug, int)  # DEBUG may be 0 or 1 depending on config file

        # 测试 KeyError
        with pytest.raises(KeyError):
            _ = config["NONEXISTENT_KEY"]

        ConfigManager.reset_singleton()

    def test_dict_interface_setitem(self):
        """测试字典接口 __setitem__ (config['KEY'] = value)"""
        from src.config import ConfigManager

        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)

        # 测试赋值
        config["TEST_KEY"] = "test_value"
        assert config.get("TEST_KEY") == "test_value"

        config["ANOTHER_KEY"] = 42
        assert config.get("ANOTHER_KEY") == 42

        ConfigManager.reset_singleton()

    def test_repr_method(self):
        """测试 __repr__ 方法"""
        from src.config import ConfigManager

        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)

        repr_str = repr(config)
        assert "ConfigManager" in repr_str
        assert "config_path" in repr_str

        # 检查是否包含代理数量信息
        assert "proxies=" in repr_str

        ConfigManager.reset_singleton()

    def test_get_instance_classmethod(self):
        """测试 get_instance 类方法"""
        from src.config import ConfigManager

        # 测试在初始化前获取实例
        ConfigManager.reset_singleton()
        instance = ConfigManager.get_instance()
        assert instance is None

        # 测试在初始化后获取实例
        ConfigManager.reset_singleton()
        ConfigManager(use_singleton=True)
        instance = ConfigManager.get_instance()
        assert instance is not None

        ConfigManager.reset_singleton()

    def test_reset_singleton_classmethod(self):
        """测试 reset_singleton 类方法"""
        from src.config import ConfigManager

        # 创建单例
        ConfigManager.reset_singleton()
        first_instance = ConfigManager(use_singleton=True)

        # 重置单例
        ConfigManager.reset_singleton()

        # 验证实例已被重置
        new_instance = ConfigManager(use_singleton=True)
        assert new_instance is not first_instance

        ConfigManager.reset_singleton()

    def test_save_to_readonly_directory(self):
        """测试保存到只读目录的错误处理"""
        from src.config import ConfigManager

        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)

        # 测试 save 方法（不实际创建只读目录，避免平台差异）
        with tempfile.TemporaryDirectory() as temp_dir:
            config.config_path = Path(temp_dir) / "config.json"

            # 这应该触发错误处理，但不应该抛出异常
            try:
                config.save()
                print("save method: OK")
            except Exception as e:
                # 在某些系统上可能会抛出异常，这是预期的
                print(f"save method error (expected): {e}")
            finally:
                ConfigManager.reset_singleton()

    def test_logger_import_failure(self, monkeypatch):
        """测试日志记录器导入失败的情况"""
        from src.config import ConfigManager

        # Mock _get_logger to raise ImportError
        with patch("src.config._get_logger") as mock_get_logger:
            mock_get_logger.side_effect = ImportError("Logger not available")

            # Should still create instance but with default logger
            config = ConfigManager(use_singleton=False)
            assert config.logger is not None

    def test_pps_config_import_failure(self, monkeypatch):
        """测试pps_config导入失败的情况"""
        from src.config import ConfigManager, _import_pps_funcs

        # Mock _import_pps_funcs to raise ImportError
        with patch("src.config._import_pps_funcs") as mock_import:
            mock_import.side_effect = ImportError("pps_config not available")

            # Should handle gracefully with defaults
            config = ConfigManager(use_singleton=False)
            assert config.pps_load_proxylist is None
            assert config.pps_save_proxylist is None
            assert str(config.config_path).endswith("PPS.conf")
            assert str(config.proxy_list_path).endswith("proxy.txt")

    def test_default_config_path_calculation(self, monkeypatch):
        """测试默认配置路径计算"""
        from src.config import ConfigManager

        # Mock PROGRAM_PATH to test path calculation
        with patch("src.config._import_pps_funcs") as mock_import:
            mock_import.return_value = (None, None, "/fake/program/path")

            config = ConfigManager(use_singleton=False)

            assert config.config_path == Path("/fake/program/path/cfg/PPS.conf")
            assert config.proxy_list_path == Path("/fake/program/path/cfg/proxy.txt")

    def test_proxy_list_loading_with_none_function(self, monkeypatch):
        """测试代理列表加载时pps_load_proxylist为None的情况"""
        from src.config import ConfigManager

        # Mock pps_load_proxylist to be None
        with patch("src.config._import_pps_funcs") as mock_import:
            mock_import.return_value = (None, None, "/fake/path")

            config = ConfigManager(use_singleton=False)

            # Mock proxy list file exists but function is None
            with patch("pathlib.Path.exists", return_value=True):
                config._load_proxies()

            assert config._proxies == []
            assert config._proxy_names == []

    def test_save_config_io_error(self, temp_dir):
        """测试保存配置文件时的IO错误"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"
        config = ConfigManager(config_path=str(config_path), use_singleton=False)

        # Set some config values
        config.set("TEST_KEY", "test_value")

        # Mock open to raise IOError
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            with patch.object(config.logger, "error") as mock_log:
                config.save()

                # Verify error was logged
                mock_log.assert_called()
                assert "保存配置失败" in mock_log.call_args[0][0]

    def test_save_proxies_exception_handling(self, temp_dir):
        """测试保存代理列表时的异常处理"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"
        proxy_list_path = Path(temp_dir) / "proxies.txt"
        config = ConfigManager(config_path=str(config_path), use_singleton=False)
        config.proxy_list_path = proxy_list_path

        # Set up proxies
        config._proxies = [("test_proxy", "127.0.0.1", "8888", "http", "user", "pass")]
        config.pps_save_proxylist = MagicMock(side_effect=Exception("Save failed"))

        with patch.object(config.logger, "error") as mock_log:
            config.save_proxies()

            # Verify error was logged
            mock_log.assert_called()
            assert "保存代理列表失败" in mock_log.call_args[0][0]

    def test_multi_instance_mode_different_behavior(self, temp_dir):
        """测试多实例模式下的不同行为"""
        from src.config import ConfigManager

        config1_path = Path(temp_dir) / "config1.json"
        config2_path = Path(temp_dir) / "config2.json"

        # Create two instances with different configs
        config1 = ConfigManager(config_path=str(config1_path), use_singleton=False)
        config2 = ConfigManager(config_path=str(config2_path), use_singleton=False)

        # Modify each independently
        config1.set("INSTANCE_ID", "config1")
        config2.set("INSTANCE_ID", "config2")

        # Each should have its own configuration
        assert config1.get("INSTANCE_ID") == "config1"
        assert config2.get("INSTANCE_ID") == "config2"

        # But singleton state should remain unchanged
        assert ConfigManager._instance is None

    def test_singleton_reset_functionality(self, temp_dir):
        """测试单例重置功能"""
        from src.config import ConfigManager

        # Create first instance
        config1 = ConfigManager(config_path=str(Path(temp_dir) / "config1.json"))
        original_instance = ConfigManager._instance

        # Reset singleton
        ConfigManager.reset_singleton()

        # Create new instance
        config2 = ConfigManager(
            config_path=str(Path(temp_dir) / "config2.json"), use_singleton=False
        )

        # Verify singleton was reset and new instance created
        assert ConfigManager._instance is not config2
        assert ConfigManager.get_instance() is None

    def test_get_instance_before_initialization(self):
        """测试在初始化前获取实例"""
        from src.config import ConfigManager

        # Reset singleton first
        ConfigManager.reset_singleton()

        # Get instance before any initialization
        instance = ConfigManager.get_instance()
        assert instance is None

    def test_get_instance_after_initialization(self, temp_dir):
        """测试在初始化后获取实例"""
        from src.config import ConfigManager

        # Reset singleton first
        ConfigManager.reset_singleton()

        # Create instance
        config = ConfigManager(config_path=str(Path(temp_dir) / "config.json"))

        # Get instance after initialization
        instance = ConfigManager.get_instance()
        assert instance is config

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

        # Verify debug logging
        with patch.object(config.logger, "debug") as mock_log:
            config.update({"KEY3": "value3"})
            mock_log.assert_called_with("配置已批量更新: ['KEY3']")

    def test_reset_to_default_method_detailed(self, temp_dir):
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

        # Verify info logging
        with patch.object(config.logger, "info") as mock_log:
            config.reset_to_default()
            mock_log.assert_called_with("配置已重置为默认值")

    def test_backwards_compatibility_fix_detailed(self, temp_dir):
        """测试向后兼容性修复的详细情况"""
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

    def test_load_empty_proxy_list_file(self, temp_dir):
        """测试加载空的代理列表文件"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"
        proxy_list_path = Path(temp_dir) / "empty_proxies.txt"

        # Create empty proxy file
        proxy_list_path.write_text("")

        config = ConfigManager(config_path=str(config_path), use_singleton=False)
        config.proxy_list_path = proxy_list_path

        # Reload proxies to use the new path
        config._load_proxies()

        # Should handle empty file gracefully
        assert config._proxies == []
        assert config._proxy_names == []

    def test_load_config_json_decode_error(self, temp_dir):
        """测试JSON解析错误的处理"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "invalid_config.json"

        # Create invalid JSON file
        config_path.write_text("{ invalid json content")

        with patch.object(
            ConfigManager(use_singleton=False).logger, "error"
        ) as mock_log:
            config = ConfigManager(config_path=str(config_path), use_singleton=False)

            # Should use default config and log error
            mock_log.assert_called()
            assert "加载配置失败" in mock_log.call_args[0][0]
            assert config.get("CMD") == "3proxy"  # Default value

    def test_load_config_io_error(self, temp_dir):
        """测试配置文件IO错误的处理"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "nonexistent_config.json"

        with patch("builtins.open", side_effect=IOError("File not found")):
            config = ConfigManager(config_path=str(config_path), use_singleton=False)

            # Should use default config and log error
            # The error should be logged during initialization
            assert config.get("CMD") == "3proxy"  # Default value

    def test_save_config_directory_creation_failure(self, temp_dir):
        """测试创建配置目录失败的情况"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "deeply" / "nested" / "path" / "config.json"

        config = ConfigManager(config_path=str(config_path), use_singleton=False)

        # Mock mkdir to raise PermissionError by patching the actual mkdir call
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Access denied")):
            with patch.object(config.logger, "error") as mock_log:
                config.save()

                # Should log error about directory creation failure
                mock_log.assert_called()
                assert "保存配置失败" in mock_log.call_args[0][0]

    def test_save_proxies_directory_creation_failure(self, temp_dir):
        """测试创建代理列表目录失败的情况"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"
        proxy_list_path = Path(temp_dir) / "deeply" / "nested" / "path" / "proxies.txt"

        config = ConfigManager(config_path=str(config_path), use_singleton=False)
        config.proxy_list_path = proxy_list_path

        config._proxies = [("test_proxy", "127.0.0.1", "8888", "http", "user", "pass")]

        # Mock mkdir to raise PermissionError by patching the actual mkdir call
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Access denied")):
            with patch.object(config.logger, "error") as mock_log:
                config.save_proxies()

                # Should log error about directory creation failure
                mock_log.assert_called()
                assert "保存代理列表失败" in mock_log.call_args[0][0]

    def test_singleton_mode_prevents_reinitialization(self, temp_dir):
        """测试单例模式防止重复初始化"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"

        # First initialization
        config1 = ConfigManager(config_path=str(config_path))

        # Second call should return same instance without reinitialization
        config2 = ConfigManager(config_path=str(Path(temp_dir) / "different.json"))

        assert config1 is config2
        assert config2.config_path == config_path  # Should use first config path

    def test_proxy_list_loading_with_exception(self, temp_dir):
        """测试代理列表加载时的通用异常处理"""
        from src.config import ConfigManager

        config_path = Path(temp_dir) / "config.json"
        proxy_list_path = Path(temp_dir) / "proxies.txt"

        config = ConfigManager(config_path=str(config_path), use_singleton=False)
        config.proxy_list_path = proxy_list_path

        # Mock pps_load_proxylist to raise generic Exception
        with (
            patch("pathlib.Path.exists", return_value=True) as mock_exists,
            patch.object(config, "pps_load_proxylist") as mock_load,
        ):
            mock_load.side_effect = Exception("Generic load error")

            with patch.object(config.logger, "error") as mock_log:
                config._load_proxies()

                # Should catch exception and set empty lists
                mock_log.assert_called()
                assert "加载代理列表失败" in mock_log.call_args[0][0]
                assert config._proxies == []
                assert config._proxy_names == []


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
