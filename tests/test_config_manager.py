#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyProxySwitch ConfigManager 测试

测试配置管理器的功能。
"""

import json
import pytest
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ConfigManager

# 条件导入 pps_config，用于测试
try:
    import src.pps_config as pps_config

    HAS_PPS_CONFIG = True
except ImportError:
    HAS_PPS_CONFIG = False


class TestConfigManagerInit:
    """ConfigManager 初始化测试"""

    def test_singleton_mode(self):
        """测试单例模式"""
        ConfigManager.reset_singleton()
        config1 = ConfigManager(use_singleton=True)
        config2 = ConfigManager(use_singleton=True)
        assert config1 is config2
        ConfigManager.reset_singleton()

    def test_multi_instance_mode(self):
        """测试多实例模式"""
        ConfigManager.reset_singleton()
        config1 = ConfigManager(use_singleton=False)
        config2 = ConfigManager(use_singleton=False)
        assert config1 is not config2
        ConfigManager.reset_singleton()

    def test_custom_config_path(self, temp_config_dir):
        """测试自定义配置路径"""
        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)
        config.config_path = temp_config_dir["config_file"]
        config.proxy_list_path = temp_config_dir["proxy_file"]
        config.load()
        assert config.config_path == temp_config_dir["config_file"]
        ConfigManager.reset_singleton()

    def test_default_config_path(self):
        """测试默认配置路径"""
        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)
        assert "PPS.conf" in str(config.config_path)
        ConfigManager.reset_singleton()


class TestConfigManagerLoad:
    """配置加载测试"""

    def test_load_existing_config(self, temp_config_dir):
        """测试加载已存在的配置"""
        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)
        config.config_path = temp_config_dir["config_file"]
        config.proxy_list_path = temp_config_dir["proxy_file"]
        config.load()

        assert config.get("CMD") == "3proxy"
        assert config.get("LOCAL_PORT") == 8888
        assert config.get("LANG") == "en"
        ConfigManager.reset_singleton()

    def test_load_proxy_list(self, temp_config_dir):
        """测试加载代理列表"""
        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)
        config.config_path = temp_config_dir["config_file"]
        config.proxy_list_path = temp_config_dir["proxy_file"]
        config.load()

        proxies = config.get_proxies()
        assert len(proxies) >= 3
        assert len(config.get_proxy_names()) >= 3
        ConfigManager.reset_singleton()

    def test_load_nonexistent_config(self, temp_dir):
        """测试加载不存在的配置文件"""
        ConfigManager.reset_singleton()
        nonexistent = temp_dir / "nonexistent.json"
        config = ConfigManager(use_singleton=False)
        config.config_path = nonexistent
        config.proxy_list_path = nonexistent
        config.load()

        # 应该使用默认配置
        assert config.get("CMD") == "3proxy"
        assert config.get("LOCAL_PORT") == 8888
        ConfigManager.reset_singleton()

    def test_fix_old_typo_fisrt_run(self, config_file_with_typo):
        """测试修复旧版本的 FISRT_RUN 拼写错误"""
        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)
        config.config_path = config_file_with_typo
        config.load()

        # 应该修复为 FIRST_RUN
        assert "FIRST_RUN" in config.keys()
        assert config.get("FIRST_RUN") == 1
        ConfigManager.reset_singleton()


class TestConfigManagerGet:
    """配置获取测试"""

    def test_get_existing_key(self, config_manager_with_temp):
        """测试获取已存在的键"""
        assert config_manager_with_temp.get("CMD") == "3proxy"
        assert config_manager_with_temp.get("LOCAL_PORT") == 8888

    def test_get_nonexistent_key_with_default(self, config_manager_with_temp):
        """测试获取不存在的键（带默认值）"""
        assert config_manager_with_temp.get("NONEXISTENT", "default") == "default"
        assert config_manager_with_temp.get("NONEXISTENT", 123) == 123

    def test_get_nonexistent_key_without_default(self, config_manager_with_temp):
        """测试获取不存在的键（无默认值）"""
        assert config_manager_with_temp.get("NONEXISTENT") is None

    def test_dict_access(self, config_manager_with_temp):
        """测试字典式访问"""
        assert config_manager_with_temp["CMD"] == "3proxy"
        assert config_manager_with_temp["LOCAL_PORT"] == 8888

    def test_dict_contains(self, config_manager_with_temp):
        """测试 in 操作符"""
        assert "CMD" in config_manager_with_temp
        assert "NONEXISTENT" not in config_manager_with_temp

    def test_dict_keys(self, config_manager_with_temp):
        """测试 keys() 方法"""
        keys = list(config_manager_with_temp.keys())
        assert "CMD" in keys
        assert "LOCAL_PORT" in keys


class TestConfigManagerSet:
    """配置设置测试"""

    def test_set_new_key(self, config_manager_with_temp):
        """测试设置新键"""
        config_manager_with_temp.set("NEW_KEY", "new_value")
        assert config_manager_with_temp.get("NEW_KEY") == "new_value"

    def test_set_existing_key(self, config_manager_with_temp):
        """测试设置已存在的键"""
        config_manager_with_temp.set("CMD", "new_cmd")
        assert config_manager_with_temp.get("CMD") == "new_cmd"

    def test_dict_assignment(self, config_manager_with_temp):
        """测试字典式赋值"""
        config_manager_with_temp["NEW_KEY"] = "dict_value"
        assert config_manager_with_temp["NEW_KEY"] == "dict_value"


class TestConfigManagerUpdate:
    """配置批量更新测试"""

    def test_update_multiple_keys(self, config_manager_with_temp):
        """测试批量更新"""
        config_manager_with_temp.update(
            {"KEY1": "value1", "KEY2": "value2", "KEY3": 123}
        )

        assert config_manager_with_temp.get("KEY1") == "value1"
        assert config_manager_with_temp.get("KEY2") == "value2"
        assert config_manager_with_temp.get("KEY3") == 123


class TestConfigManagerSave:
    """配置保存测试"""

    def test_save_config(self, config_manager_with_temp, temp_config_dir):
        """测试保存配置"""
        config_manager_with_temp.set("TEST_SAVE", "saved_value")
        config_manager_with_temp.save()

        # 重新加载验证
        ConfigManager.reset_singleton()
        config2 = ConfigManager(use_singleton=False)
        config2.config_path = temp_config_dir["config_file"]
        config2.proxy_list_path = temp_config_dir["proxy_file"]
        config2.load()

        assert config2.get("TEST_SAVE") == "saved_value"
        ConfigManager.reset_singleton()

    def test_save_creates_directory(self, temp_dir):
        """测试保存时创建目录"""
        ConfigManager.reset_singleton()
        config = ConfigManager(use_singleton=False)
        config.config_path = temp_dir / "new_dir" / "config.json"
        config.proxy_list_path = temp_dir / "new_dir" / "proxy.txt"
        config.load()

        config.set("TEST", "value")
        config.save()

        assert (temp_dir / "new_dir" / "config.json").exists()
        ConfigManager.reset_singleton()


class TestConfigManagerReload:
    """配置重载测试"""

    def test_reload(self, config_manager_with_temp, temp_config_dir):
        """测试重载配置"""
        # 先修改文件
        with open(temp_config_dir["config_file"], "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["RELOADED"] = "yes"
        with open(temp_config_dir["config_file"], "w", encoding="utf-8") as f:
            json.dump(cfg, f)

        # 重载
        config_manager_with_temp.reload()

        assert config_manager_with_temp.get("RELOADED") == "yes"


class TestConfigManagerReset:
    """配置重置测试"""

    def test_reset_to_default(self, config_manager_with_temp):
        """测试重置为默认配置"""
        config_manager_with_temp.set("CUSTOM", "value")
        config_manager_with_temp.reset_to_default()

        # 默认值应该存在
        assert config_manager_with_temp.get("CMD") == "3proxy"
        assert config_manager_with_temp.get("LOCAL_PORT") == 8888
        # 自定义值应该被清除
        assert config_manager_with_temp.get("CUSTOM") is None


class TestConfigManagerProxy:
    """代理列表管理测试"""

    def test_get_proxies(self, config_manager_with_temp):
        """测试获取代理列表"""
        proxies = config_manager_with_temp.get_proxies()
        assert isinstance(proxies, list)
        if proxies:
            assert len(proxies[0]) == 6  # 6元组

    def test_get_proxy_names(self, config_manager_with_temp):
        """测试获取代理名称列表"""
        names = config_manager_with_temp.get_proxy_names()
        assert isinstance(names, list)
        assert all(isinstance(n, str) for n in names)


class TestConfigManagerSaveProxies:
    """代理保存测试"""

    def test_save_proxies(self, config_manager_with_temp, temp_dir):
        """测试保存代理列表"""
        if not HAS_PPS_CONFIG:
            pytest.skip("pps_config not available")

        # 设置 pps_save_proxylist 函数
        config_manager_with_temp.pps_save_proxylist = pps_config.pps_save_proxylist

        proxy_file = temp_dir / "saved_proxy.txt"
        config_manager_with_temp.proxy_list_path = proxy_file

        config_manager_with_temp.save_proxies()
        assert proxy_file.exists()

    def test_save_proxies_without_function(self, config_manager_with_temp):
        """测试 pps_save_proxylist 函数不可用时的处理"""
        config_manager_with_temp.pps_save_proxylist = None
        # 不应抛出异常，只记录日志
        config_manager_with_temp.save_proxies()


class TestConfigManagerGetItem:
    """字典访问测试"""

    def test_getitem_keyerror(self, config_manager_with_temp):
        """测试获取不存在的键引发 KeyError"""
        with pytest.raises(KeyError):
            _ = config_manager_with_temp["NONEXISTENT_KEY_12345"]


class TestConfigManagerItems:
    """字典遍历测试"""

    def test_items(self, config_manager_with_temp):
        """测试 items() 方法"""
        items_list = list(config_manager_with_temp.items())
        assert len(items_list) > 0
        assert all(len(item) == 2 for item in items_list)

    def test_values(self, config_manager_with_temp):
        """测试 values() 方法"""
        values_list = list(config_manager_with_temp.values())
        assert len(values_list) > 0


class TestConfigManagerGetInstance:
    """单例获取测试"""

    def test_get_instance_before_init(self):
        """测试在初始化前获取单例"""
        ConfigManager.reset_singleton()
        instance = ConfigManager.get_instance()
        assert instance is None

    def test_get_instance_after_init(self):
        """测试在初始化后获取单例"""
        ConfigManager.reset_singleton()
        ConfigManager(use_singleton=True)
        instance = ConfigManager.get_instance()
        assert instance is not None
        ConfigManager.reset_singleton()


class TestConfigManagerRepr:
    """字符串表示测试"""

    def test_repr(self, config_manager_with_temp):
        """测试 __repr__ 方法"""
        repr_str = repr(config_manager_with_temp)
        assert "ConfigManager" in repr_str
        assert "config_path" in repr_str


class TestConfigManagerErrorHandling:
    """错误处理测试"""

    def test_load_invalid_json_config(self, temp_dir):
        """测试加载无效JSON配置文件时的错误处理"""
        ConfigManager.reset_singleton()

        # 创建无效的JSON文件
        invalid_config = temp_dir / "invalid.json"
        invalid_config.write_text("{ invalid json", encoding="utf-8")

        config = ConfigManager(use_singleton=False)
        config.config_path = invalid_config
        config.proxy_list_path = temp_dir / "proxy.txt"
        config.load()

        # 应该使用默认配置
        assert config.get("CMD") == "3proxy"
        assert config.get("LOCAL_PORT") == 8888
        ConfigManager.reset_singleton()

    def test_load_nonexistent_proxy_list(self, temp_dir):
        """测试加载不存在的代理列表文件"""
        ConfigManager.reset_singleton()

        config = ConfigManager(use_singleton=False)
        config.config_path = temp_dir / "config.json"
        config.proxy_list_path = temp_dir / "nonexistent_proxy.txt"
        config.load()

        # 应该有空代理列表
        assert config.get_proxies() == []
        assert config.get_proxy_names() == []
        ConfigManager.reset_singleton()

    def test_save_to_readonly_location(self, config_manager_with_temp, temp_dir):
        """测试保存到只读位置的错误处理"""
        # 模拟只读目录
        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # 只读权限

        config_manager_with_temp.config_path = readonly_dir / "config.json"

        try:
            # 这应该触发错误处理，但不应该抛出异常
            config_manager_with_temp.save()
        except (PermissionError, OSError):
            # 在某些系统上可能会抛出异常，这是预期的
            pass
        finally:
            # 恢复权限以便清理
            readonly_dir.chmod(0o755)

    def test_save_proxies_without_function(self, config_manager_with_temp):
        """测试保存代理列表但函数不可用的情况"""
        # 设置 pps_save_proxylist 为 None
        config_manager_with_temp.pps_save_proxylist = None

        # 这应该记录错误但不抛出异常
        config_manager_with_temp.save_proxies()

    def test_load_proxies_without_function(self, temp_dir):
        """测试加载代理列表但函数不可用的情况"""
        ConfigManager.reset_singleton()

        config = ConfigManager(use_singleton=False)
        config.config_path = temp_dir / "config.json"
        config.proxy_list_path = temp_dir / "proxy.txt"

        # 设置 pps_load_proxylist 为 None
        config.pps_load_proxylist = None

        # 这应该记录错误但继续工作
        config._load_proxies()

        assert config.get_proxies() == []
        assert config.get_proxy_names() == []
        ConfigManager.reset_singleton()

    def test_load_corrupted_proxy_list(self, temp_dir):
        """测试加载损坏的代理列表文件"""
        ConfigManager.reset_singleton()

        # 创建损坏的代理列表文件
        corrupted_proxy = temp_dir / "corrupted_proxy.txt"
        corrupted_proxy.write_text("invalid proxy data\n", encoding="utf-8")

        config = ConfigManager(use_singleton=False)
        config.config_path = temp_dir / "config.json"
        config.proxy_list_path = corrupted_proxy

        # 设置一个会抛出异常的 pps_load_proxylist
        def mock_load_proxylist(path):
            raise Exception("Mock proxy load error")

        config.pps_load_proxylist = mock_load_proxylist

        # 这应该处理异常并继续
        config._load_proxies()

        assert config.get_proxies() == []
        assert config.get_proxy_names() == []
        ConfigManager.reset_singleton()
