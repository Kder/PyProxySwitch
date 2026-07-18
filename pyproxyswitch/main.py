#!/usr/bin/env python

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

"""
PyProxySwitch is a cross-platform proxy switcher with a native Python HTTP,
SOCKS4 and SOCKS5 server. It changes upstream routes without restarting the
local listener or interrupting existing connections.

Welcom to send me your feedback if you feel it useful.
"""

__author__ = "Kder"
__copyright__ = "Copyright 2009-2026 Kder"
__credits__ = ["Kder"]

from ._version import __version__

__date__ = "2026-07-18"
__maintainer__ = "Kder"
__email__ = "[kderlin (#) gmail dot com]"
__url__ = "http://www.kder.info"
__license__ = "Apache License, Version 2.0"
__status__ = "Beta"
__projecturl__ = "http://pyproxyswitch.kder.info"


import logging
import sys


def main(log_level: int | str | None = None) -> None:
    """应用程序主入口点"""
    logger = None
    # 检查必要的依赖
    try:
        from PySide6 import QtWidgets
    except ImportError as e:
        print(f"Error: PySide6 failed to import (maybe not installed?): {e}")
        sys.exit(1)
    try:
        # 导入必要的模块
        from pyproxyswitch.config import ConfigManager
        from pyproxyswitch.gui.main_window import Window
        from pyproxyswitch.logger_config import setup_logger

        # 命令行未覆盖时使用持久化的调试选项。
        if log_level is None:
            log_level = logging.DEBUG if ConfigManager().get("DEBUG", 0) else logging.INFO

        root_logger = logging.getLogger("PyProxySwitch")
        # 检查是否已经有logger配置，如果没有才重新配置
        if not root_logger.handlers:
            logger = setup_logger(log_level=log_level)
        else:
            # 如果已经有handler，直接使用现有logger
            logger = root_logger
            # 确保控制台处理器的级别正确
            for handler in logger.handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(
                    handler, logging.FileHandler
                ):
                    handler.setLevel(log_level)

        # 设置应用程序
        app = QtWidgets.QApplication(sys.argv)
        app.setApplicationName("PyProxySwitch")
        app.setApplicationVersion(__version__)
        app.setQuitOnLastWindowClosed(False)

        # 创建并显示主窗口
        _window = Window()

        # 启动事件循环
        sys.exit(app.exec())

    except KeyboardInterrupt:
        print("\nPyProxySwitch terminated by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        if logger is not None:
            logger.exception("Fatal error occurred")
        sys.exit(1)


if __name__ == "__main__":
    main()
