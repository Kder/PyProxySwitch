#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2009-2026 Kder Lin
#
# Licensed under the Apache License, 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

'''
PyProxySwitch is a cross-platform proxy switcher based on 3proxy, polipo and
IP Relay to fast change proxy for browsers(Firefox,Chrome,Opera,IE, etc.) and
other internet applications, writen in Python and PySide6.

Welcom to send me your feedback if you feel it useful.
'''


__author__ = 'Kder'
__copyright__ = 'Copyright 2009-2026 Kder'
__credits__ = ['Kder']

__version__ = '3.8.0'
__date__ = '2026-03-17'
__maintainer__ = "Kder"
__email__ = '[kderlin (#) gmail dot com]'
__url__ = 'http://www.kder.info'
__license__ = 'Apache License, Version 2.0'
__status__ = 'Beta'
__projecturl__ = 'http://pyproxyswitch.kder.info'


import sys

def main(log_level=None):
    """应用程序主入口点"""
    logger = None
    # 检查必要的依赖
    try:
        import PySide6
    except ImportError as e:
        print(f"Error: PySide6 is required but not installed: {e}")
        sys.exit(1)
    try:
        # 导入必要的模块
        from PySide6 import QtWidgets
        from src.logger_config import setup_logger
        from src.gui.main_window import Window

        # 设置日志（使用传入的log_level，如果没有传入则使用默认值）
        setup_logger(log_level=log_level)
        from src.logger_config import logger

        # 检查Python版本
        if sys.version_info < (3, 9):
            print("Error: PyProxySwitch requires Python 3.9 or higher")
            sys.exit(1)


        # 设置应用程序
        app = QtWidgets.QApplication(sys.argv)
        app.setApplicationName("PyProxySwitch")
        app.setApplicationVersion(__version__)

        # 设置应用程序路径
        import src.pps_config as pps_config
        pps_config.setup_paths()

        # 创建并显示主窗口
        window = Window()

        # 启动事件循环
        sys.exit(app.exec())

    except KeyboardInterrupt:
        print("\nPyProxySwitch terminated by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        if 'logger' in locals():
            logger.exception("Fatal error occurred")
        sys.exit(1)


if __name__ == '__main__':
    main()