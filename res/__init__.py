# -*- coding: utf-8 -*-
"""
PyProxySwitch UI资源包

该包包含了PyProxySwitch应用程序的所有UI相关资源：

- Qt Designer界面文件 (.ui)
- 编译后的Python UI文件 (_ui.py)
- Qt资源文件 (图标、图片等)
- UI编译工具脚本

主要功能：
1. 提供Qt Designer设计的界面定义
2. 包含编译后的UI Python代码
3. 管理应用程序图标和其他资源
4. 提供UI文件编译和更新工具

文件说明：
- add_proxy.ui: 添加代理对话框的Qt Designer文件
- add_proxy_ui.py: 编译后的添加代理对话框Python代码
- pps_conf.ui: 主配置对话框的Qt Designer文件
- pps_conf_ui.py: 编译后的主配置对话框Python代码
- pps_qrc.py: Qt资源文件，包含程序图标等资源
- makeui.bat: UI文件编译脚本

使用方法：
    # 导入UI类
    from res.add_proxy_ui import Ui_add_proxy_dialog
    from res.pps_conf_ui import Ui_config_dialog

    # 导入资源
    import res.pps_qrc

版本: 3.8.0
"""

__version__ = "3.8.0"
__description__ = "PyProxySwitch UI资源包"

# 自动导入编译后的UI模块，便于外部使用
try:
    from .add_proxy_ui import Ui_Dialog_AddProxy
    from .pps_conf_ui import Ui_Dialog_Config
    from . import pps_qrc  # 导入资源文件
except ImportError as e:
    import warnings
    warnings.warn(f"UI模块导入失败: {e}，请确保已运行makeui.bat编译UI文件")

# 导出主要UI类
__all__ = [
    'Ui_Dialog_AddProxy',
    'Ui_Dialog_Config',
    '__version__',
    '__author__',
    '__description__'
]

def compile_ui_files():
    """编译所有UI文件

    该函数调用pyuic6来将Qt Designer的.ui文件编译为Python代码。
    通常在UI设计更新后使用此函数。

    需要: pyuic6 (PySide6的一部分)
    """
    import subprocess
    import os

    ui_files = [
        ('pps_conf.ui', 'pps_conf_ui.py'),
        ('add_proxy.ui', 'add_proxy_ui.py')
    ]

    for ui_file, py_file in ui_files:
        if os.path.exists(ui_file):
            try:
                subprocess.run(['pyuic6', '-o', py_file, ui_file], check=True)
                print(f"成功编译 {ui_file} -> {py_file}")
            except subprocess.CalledProcessError as e:
                print(f"编译 {ui_file} 失败: {e}")
            except FileNotFoundError:
                print("未找到pyuic6，请确保PySide6已正确安装")

def list_ui_resources():
    """列出所有可用的UI资源"""
    import os
    resources = []

    for file in os.listdir(os.path.dirname(__file__)):
        if file.endswith(('.ui', '_ui.py')):
            resources.append(file)

    return resources

def get_resource_path(resource_name):
    """获取资源文件的完整路径

    Args:
        resource_name: 资源文件名

    Returns:
        str: 资源的完整路径，如果不存在则返回None
    """
    import os
    resource_path = os.path.join(os.path.dirname(__file__), resource_name)
    return resource_path if os.path.exists(resource_path) else None