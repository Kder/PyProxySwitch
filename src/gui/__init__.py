#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GUI模块 - 包含所有用户界面相关的代码

此模块包含PyProxySwitch的所有GUI组件，包括主窗口、配置对话框等。
"""

from .main_window import Window
from .config_dialog import Config_Dialog
from .add_proxy_dialog import AddProxy_Dialog
from .delegates import ProxyTypeDelegate, ProxyPortDelegate, ProxyNameDelegate

__all__ = [
    'Window',
    'Config_Dialog',
    'AddProxy_Dialog',
    'ProxyTypeDelegate',
    'ProxyPortDelegate',
    'ProxyNameDelegate'
]