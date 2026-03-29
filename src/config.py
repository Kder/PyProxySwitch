#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

"""
PyProxySwitch 配置管理模块

提供ConfigManager类用于管理应用配置和代理列表，支持单例模式和依赖注入。
与pps_config.py兼容，可逐步迁移现有代码。

使用示例:
    # 基本使用（单例模式）
    config = ConfigManager()
    cmd = config.get('CMD')
    config.set('LAST_ITEM', 'proxy1')
    config.save()
    
    # 测试环境（使用自定义配置目录）
    config = ConfigManager(config_path='/tmp/test_config.json')
    
    # 禁用单例（每次创建新实例）
    config1 = ConfigManager(use_singleton=False)
    config2 = ConfigManager(use_singleton=False)  # 不同的实例
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

__all__ = ["ConfigManager"]


# 延迟导入以避免循环依赖
def _get_logger():
    """获取日志记录器（延迟导入）"""
    try:
        from .logger_config import logger as _logger

        return _logger
    except ImportError:
        import logging

        return logging.getLogger("ConfigManager")


def _import_pps_funcs():
    """导入pps_config中的函数（延迟导入）"""
    try:
        from . import pps_config

        return (
            pps_config.pps_load_proxylist,
            pps_config.pps_save_proxylist,
            pps_config.PROGRAM_PATH,
        )
    except ImportError:
        raise ImportError("无法导入 pps_config 模块")


class ConfigManager:
    """
    配置管理器（支持单例模式）

    特点：
    - 支持单例模式（默认）或多实例（通过use_singleton=False）
    - 配置和代理列表自动加载和保存
    - 与pps_config.py兼容的API
    - 支持依赖注入用于测试

    示例：
        # 单例模式（推荐）
        config = ConfigManager()
        port = config.get('LOCAL_PORT', 8888)

        # 修改配置
        config.set('LAST_ITEM', 'my_proxy')
        config.save()

        # 获取代理列表
        proxies = config.get_proxies()
        names = config.get_proxy_names()
    """

    _instance: Optional["ConfigManager"] = None
    _initialized: bool = False

    def __new__(cls, config_path: Optional[str] = None, proxy_list_path: Optional[str] = None, backend_config_base: Optional[str] = None, use_singleton: bool = True):
        """创建或返回单例实例"""
        # 如果启用单例模式且已有实例，则返回现有实例
        if use_singleton and cls._instance is not None:
            return cls._instance

        # 创建新实例
        instance = super().__new__(cls)

        # 设置单例实例（如果启用单例模式）
        if use_singleton:
            cls._instance = instance

        return instance

    def __init__(
        self,
        config_path: Optional[str] = None,
        proxy_list_path: Optional[str] = None,
        backend_config_base: Optional[str] = None,
        use_singleton: bool = True,
    ):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，默认为 {PROGRAM_PATH}/cfg/PPS.conf
            proxy_list_path: 代理列表文件路径，默认为 {PROGRAM_PATH}/cfg/proxy.txt
            backend_config_base: 后端配置基础路径，默认为 {PROGRAM_PATH}/cfg
            use_singleton: 是否使用单例模式（默认True）
        """
        # 单例模式下，防止重复初始化
        if use_singleton and self._initialized:
            return

        # 获取日志记录器，失败时使用默认logger
        try:
            self.logger = _get_logger()
        except Exception:
            import logging

            self.logger = logging.getLogger("ConfigManager")

        # 获取pps_config中的函数和PROGRAM_PATH
        try:
            self.pps_load_proxylist, self.pps_save_proxylist, program_path = (
                _import_pps_funcs()
            )
        except ImportError as e:
            self.logger.error(f"导入pps_config失败: {e}")
            # 提供默认值以便继续工作
            program_path = str(Path(__file__).parent.parent)
            self.pps_load_proxylist = None
            self.pps_save_proxylist = None

        # 设置配置文件路径
        if config_path is None:
            self.config_path = Path(program_path) / "cfg" / "PPS.conf"
        else:
            self.config_path = Path(config_path)

        # 设置代理列表文件路径
        if proxy_list_path is None:
            self.proxy_list_path = Path(program_path) / "cfg" / "proxy.txt"
        else:
            self.proxy_list_path = Path(proxy_list_path)

        # 设置后端配置基础路径
        if backend_config_base is None:
            self.backend_config_base = Path(program_path) / "cfg"
        else:
            self.backend_config_base = Path(backend_config_base)

        # 配置数据存储
        self._config: Dict[str, Any] = {}
        self._proxies: List[Tuple[str, str, str, str, str, str]] = []
        self._proxy_names: List[str] = []

        # 加载配置和代理列表
        self.load()

        if use_singleton:
            self._initialized = True

    def load(self) -> None:
        """加载配置和代理列表"""
        try:
            # 加载配置文件
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                self.logger.debug(f"配置文件已加载: {self.config_path}")
            else:
                self._config = self._get_default_config()
                self.logger.debug(f"配置文件不存在，使用默认配置: {self.config_path}")

            # 修复向后兼容性问题（修复旧版拼写错误）
            if "FISRT_RUN" in self._config and "FIRST_RUN" not in self._config:
                self._config["FIRST_RUN"] = self._config.pop("FISRT_RUN")
                self.logger.debug("已修复配置拼写错误: FISRT_RUN -> FIRST_RUN")

            # 加载代理列表
            self._load_proxies()
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"加载配置失败: {e}")
            self._config = self._get_default_config()
            self._proxies = []
            self._proxy_names = []

    def _load_proxies(self) -> None:
        """加载代理列表"""
        try:
            if not self.proxy_list_path.exists():
                self.logger.warning(f"代理列表不存在: {self.proxy_list_path}")
                self._proxies = []
                self._proxy_names = []
            elif self.pps_load_proxylist is None:
                self.logger.error("pps_load_proxylist 函数不可用")
                self._proxies = []
                self._proxy_names = []
            else:
                self._proxies = self.pps_load_proxylist(str(self.proxy_list_path))
                self._proxy_names = [p[0] for p in self._proxies]
                self.logger.debug(
                    f"代理列表已加载: {self.proxy_list_path} ({len(self._proxies)} 个代理)"
                )
        except Exception as e:
            self.logger.error(f"加载代理列表失败: {e}")
            self._proxies = []
            self._proxy_names = []

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键名
            default: 默认值（如果键不存在）

        Returns:
            配置值或默认值
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        设置配置值

        Args:
            key: 配置键名
            value: 配置值
        """
        self._config[key] = value
        self.logger.debug(f"配置已更新: {key} = {value}")

    def get_proxies(self) -> List[Tuple[str, str, str, str, str, str]]:
        """
        获取代理列表

        Returns:
            代理列表，每个元素是 (名称, 地址, 端口, 类型, 用户名, 密码) 元组
        """
        return self._proxies

    def get_proxy_names(self) -> List[str]:
        """
        获取代理名称列表

        Returns:
            代理名称列表
        """
        return self._proxy_names

    def reload(self) -> None:
        """重新加载配置和代理列表"""
        self.load()

    def save(self) -> None:
        """保存配置到文件"""
        try:
            # 确保目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, sort_keys=True, ensure_ascii=False)

            self.logger.info(f"配置已保存: {self.config_path}")
        except IOError as e:
            self.logger.error(f"保存配置失败: {e}")

    def set_proxies(self, proxies: List[List[str]]) -> None:
        """
        设置代理列表

        Args:
            proxies: 代理列表，每个元素是 [名称, 地址, 端口, ...] 格式
        """
        # 转换为内部格式 (名称, 地址, 端口, 类型, 用户名, 密码)
        self._proxies = []
        #self.logger.info(f"config.py get proxies: {proxies}")
        for proxy in proxies:
            if len(proxy) >= 3:
                name, address, port = proxy[0], proxy[1], proxy[2]
                ptype = proxy[3] if len(proxy) > 3 and proxy[3] != "HTTP" else "HTTP"
                user = proxy[4] if len(proxy) > 4 else ""
                pwd = proxy[5] if len(proxy) > 5 else ""
                self._proxies.append((name, address, port, ptype, user, pwd))
            #self.logger.debug(f"config.py set: {proxy}")

        self.logger.info(f"代理列表已更新，共 {len(self._proxies)} 个代理")

    def save_proxies(self) -> None:
        """保存代理列表"""
        try:
            if self.pps_save_proxylist is None:
                self.logger.error("pps_save_proxylist 函数不可用")
                return

            # 确保目录存在
            self.proxy_list_path.parent.mkdir(parents=True, exist_ok=True)

            self.pps_save_proxylist(self._proxies, str(self.proxy_list_path))
            self.logger.info(f"代理列表已保存: {self.proxy_list_path}")
        except Exception as e:
            self.logger.error(f"保存代理列表失败: {e}")

    def update(self, update_dict: Dict[str, Any]) -> None:
        """
        批量更新配置

        Args:
            update_dict: 包含要更新的键值对的字典
        """
        self._config.update(update_dict)
        self.logger.debug(f"配置已批量更新: {list(update_dict.keys())}")

    def reset_to_default(self) -> None:
        """重置配置为默认值"""
        self._config = self._get_default_config()
        self.logger.info("配置已重置为默认值")

    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "CMD": "3proxy",
            "DEBUG": 0,
            "DEFAULT_ITEM": "NoProxy",
            "FIRST_RUN": 0,
            "LANG": "zh_CN",
            "LAST_ITEM": "NoProxy",
            "LOCAL_PORT": 8888,
            "SHOW_WELCOME": 0,
        }

    # ============ 字典接口兼容性方法 ============
    def __getitem__(self, key: str) -> Any:
        """支持字典访问: config['KEY']"""
        return self._config[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """支持字典赋值: config['KEY'] = value"""
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        """支持 in 操作符: 'KEY' in config"""
        return key in self._config

    def keys(self):
        """返回配置键视图"""
        return self._config.keys()

    def values(self):
        """返回配置值视图"""
        return self._config.values()

    def items(self):
        """返回配置项视图"""
        return self._config.items()

    def __repr__(self) -> str:
        """字符串表示"""
        return f"ConfigManager(config_path={self.config_path}, proxies={len(self._proxies)})"

    # ============ 路径管理方法 ============
    def get_backend_config_dir(self, backend_type: str) -> Path:
        """获取后端特定的配置目录"""
        return self.backend_config_base / backend_type

    def get_config_path(self) -> Path:
        """获取主配置文件路径"""
        return self.config_path

    def get_proxy_list_path(self) -> Path:
        """获取代理列表文件路径"""
        return self.proxy_list_path

    # ============ 单例相关方法 ============
    @classmethod
    def get_instance(cls) -> Optional["ConfigManager"]:
        """获取单例实例（如果已创建）"""
        return cls._instance

    @classmethod
    def reset_singleton(cls) -> None:
        """重置单例（用于测试）"""
        cls._instance = None
        cls._initialized = False
