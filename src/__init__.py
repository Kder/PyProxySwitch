# -*- coding: utf-8 -*-
"""
PyProxySwitch 包初始化文件

该包包含了PyProxySwitch代理切换器应用程序的所有核心组件：

- main.py: 主应用程序，包含系统托盘界面和核心逻辑
- pps_config.py: 配置管理模块，处理JSON配置和命令行接口
- proxy_validation.py: 输入验证模块，提供代理参数验证和Qt验证器集成
- logger_config.py: 日志配置模块，提供统一的日志处理

"""

__version__ = "3.9.0"
__description__ = "PyProxySwitch - 跨平台代理切换器"

# 包级别的导入，便于外部使用
from .logger_config import setup_logger
from .proxy_validation import ProxyValidator, BatchImportValidator

# 从pps_config导入主要函数
from .pps_config import (
    pps_loadcfg, pps_savecfg, pps_output, pps_exc_handle,
    pps_load_proxylist, pps_save_proxylist, add_proxy, del_proxy
)

# 导出主要组件
__all__ = [
    'setup_logger',
    'ProxyValidator',
    'BatchImportValidator',
    'pps_loadcfg',
    'pps_savecfg',
    'pps_output',
    'pps_exc_handle',
    'pps_load_proxylist',
    'pps_save_proxylist',
    'add_proxy',
    'del_proxy',
    '__version__',
    '__author__',
    '__description__'
]