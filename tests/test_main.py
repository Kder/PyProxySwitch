#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyProxySwitch main.py 模块测试

测试主程序UI功能。
"""

import pytest
import sys
import os
import subprocess
import signal
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Any

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 检查 Qt 是否可用
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtCore import QCoreApplication

    HAS_QT = True
except ImportError:
    HAS_QT = False


@pytest.mark.skipif(not HAS_QT, reason="PySide6 not available")
class TestWindow:
    """Window 类测试"""

    @pytest.fixture
    def mock_config_manager(self):
        """创建模拟的 ConfigManager"""
        with patch("src.main.ConfigManager") as mock_class:
            mock_instance = Mock()
            mock_instance.get.return_value = "3proxy"
            mock_instance.get_proxies.return_value = [
                ("test_proxy", "192.168.1.1", "8080", "HTTP", "", ""),
                ("auth_proxy", "10.0.0.1", "3128", "HTTP", "user", "pass"),
            ]
            mock_instance.proxy_list_path = "/tmp/proxy.txt"
            mock_class.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_system_tray_available(self):
        """模拟系统托盘可用"""
        with patch("PySide6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable") as mock:
            mock.return_value = True
            yield mock

    @pytest.fixture
    def mock_system_tray_unavailable(self):
        """模拟系统托盘不可用"""
        with patch("PySide6.QtWidgets.QSystemTrayIcon.isSystemTrayAvailable") as mock:
            mock.return_value = False
            yield mock

    def test_window_init_system_tray_unavailable(self, mock_system_tray_unavailable):
        """测试系统托盘不可用时的初始化"""
        with patch("sys.exit") as mock_exit:
            from src.gui.main_window import Window

            # 应该退出程序
            Window()
            mock_exit.assert_called_with(1)

    def test_window_init_success(self, mock_config_manager, mock_system_tray_available):
        """测试成功初始化窗口"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator") as mock_translator,
            patch("src.gui.main_window.QCoreApplication.instance") as mock_app_instance,
            patch("src.gui.main_window.logger") as mock_logger,
        ):
            from src.gui.main_window import Window

            window = Window()

            # 验证基本属性设置
            assert window.cmd == "3proxy"
            assert window.r_process is None
            assert window.dialog_exsit is False
            assert window.proxy_list == [
                ("test_proxy", "192.168.1.1", "8080", "HTTP", "", ""),
                ("auth_proxy", "10.0.0.1", "3128", "HTTP", "user", "pass"),
            ]
            assert len(window.proxy_names) == 2
            assert "NoProxy" in window.proxy_names  # 应该添加 NoProxy

    def test_window_init_with_ip_relay(self, mock_system_tray_available):
        """测试使用 ip_relay 时的初始化"""
        with patch("src.main.ConfigManager") as mock_class:
            mock_instance = Mock()
            mock_instance.get.side_effect = (
                lambda key: "ip_relay" if key == "CMD" else "test_proxy"
            )
            mock_instance.get_proxies.return_value = [
                ("test_proxy", "192.168.1.1", "8080", "HTTP", "", "")
            ]
            mock_class.return_value = mock_instance

            with (
                patch("src.gui.main_window.QtCore.QTranslator"),
                patch("src.gui.main_window.QCoreApplication.instance"),
                patch("src.gui.main_window.logger"),
            ):
                from src.gui.main_window import Window

                window = Window()

                # 对于 ip_relay，应该设置 item 和 port
                assert window.item == "192.168.1.1"
                assert window.port == "8080"
                assert (
                    "NoProxy" not in window.proxy_names
                )  # ip_relay 不应该添加 NoProxy

    def test_refresh_menu(self, mock_config_manager, mock_system_tray_available):
        """测试刷新菜单功能"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
        ):
            from src.gui.main_window import Window

            window = Window()
            window.createActions = Mock()  # Mock createActions 方法

            window.refresh_menu()

            # 验证 ConfigManager 重新加载
            mock_config_manager.reload.assert_called_once()
            window.createActions.assert_called_once()

    def test_create_actions(self, mock_config_manager, mock_system_tray_available):
        """测试创建菜单动作"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
        ):
            from src.gui.main_window import Window

            window = Window()
            window.item_text = "test_proxy"

            # Mock Qt 相关对象
            window.ppsActionGroup = Mock()
            window.trayIconMenu = Mock()

            window.createActions()

            # 验证动作被创建
            assert hasattr(window, "ppsActionList")
            assert len(window.ppsActionList) > 0

    def test_on_activated_double_click(
        self, mock_config_manager, mock_system_tray_available
    ):
        """测试双击托盘图标"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
        ):
            from src.gui.main_window import Window

            window = Window()
            window.config = Mock()  # Mock config 方法

            # 模拟双击事件
            reason = QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick
            window.on_activated(reason)

            window.config.assert_called_once()

    def test_config_dialog(self, mock_config_manager, mock_system_tray_available):
        """测试配置对话框"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
            patch("src.main.Config_Dialog") as mock_dialog,
        ):
            from src.gui.main_window import Window

            window = Window()
            window.dialog_exsit = False

            window.config()

            # 验证对话框被创建和执行
            mock_dialog.assert_called_once()
            mock_dialog.return_value.exec.assert_called_once()

    def test_config_dialog_existing(
        self, mock_config_manager, mock_system_tray_available
    ):
        """测试已存在配置对话框的情况"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
            patch("src.main.Config_Dialog") as mock_dialog,
        ):
            from src.gui.main_window import Window

            window = Window()
            window.dialog_exsit = True
            window.config_dialog = Mock()

            window.config()

            # 应该激活现有对话框而不是创建新对话框
            window.config_dialog.activateWindow.assert_called_once()
            window.config_dialog.setFocus.assert_called_once()
            mock_dialog.assert_not_called()

    def test_about_dialog(self, mock_config_manager, mock_system_tray_available):
        """测试关于对话框"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
            patch("src.main.QtWidgets.QMessageBox") as mock_message_box,
            patch("src.main.QtGui.QPixmap") as mock_pixmap,
        ):
            from src.gui.main_window import Window

            window = Window()

            window.about()

            # 验证消息框被创建和显示
            mock_message_box.assert_called_once()
            mock_message_box.return_value.show.assert_called_once()

    def test_switch_proxy(self, mock_config_manager, mock_system_tray_available):
        """测试切换代理"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
            patch("src.main.QtWidgets.QMessageBox"),
        ):
            from src.gui.main_window import Window

            window = Window()
            window.terminate_process = Mock()
            window.run_cmd = Mock()

            # Mock sender 方法
            mock_action = Mock()
            mock_action.text.return_value = "test_proxy"
            window.sender = Mock(return_value=mock_action)

            window.switchProxy()

            # 验证进程终止和新命令运行
            window.terminate_process.assert_called_once_with(timeout=5)
            window.run_cmd.assert_called_once()

    def test_quit(self, mock_config_manager, mock_system_tray_available):
        """测试退出功能"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
        ):
            from src.gui.main_window import Window

            window = Window()
            window.terminate_process = Mock()
            window.trayIcon = Mock()

            window.quit()

            # 验证配置保存和进程终止
            mock_config_manager.set.assert_called_once_with(
                "LAST_ITEM", window.item_text
            )
            mock_config_manager.save.assert_called_once()
            window.terminate_process.assert_called_once_with(timeout=5)
            window.trayIcon.setVisible.assert_called_once_with(False)

    def test_terminate_process_no_process(
        self, mock_config_manager, mock_system_tray_available
    ):
        """测试终止不存在的进程"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
        ):
            from src.gui.main_window import Window

            window = Window()
            window.r_process = None

            result = window.terminate_process()

            assert result is True

    def test_terminate_process_success(
        self, mock_config_manager, mock_system_tray_available
    ):
        """测试成功终止进程"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
            patch("os.name", "nt"),
        ):  # Windows
            from src.gui.main_window import Window

            window = Window()
            mock_process = Mock()
            mock_process.wait.return_value = None
            window.r_process = mock_process

            result = window.terminate_process(timeout=5)

            # 验证进程被终止
            mock_process.terminate.assert_called_once()
            mock_process.wait.assert_called_once_with(timeout=5)
            assert result is True

    def test_terminate_process_timeout(
        self, mock_config_manager, mock_system_tray_available
    ):
        """测试进程终止超时"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
            patch("os.name", "nt"),
        ):  # Windows
            from src.gui.main_window import Window

            window = Window()
            mock_process = Mock()
            mock_process.wait.side_effect = subprocess.TimeoutExpired("cmd", 5)
            window.r_process = mock_process

            result = window.terminate_process(timeout=5)

            # 验证进程被强制杀死
            mock_process.terminate.assert_called_once()
            mock_process.kill.assert_called_once()
            mock_process.wait.assert_called()  # 应该有第二次 wait 调用
            assert result is False

    def test_terminate_process_unix(
        self, mock_config_manager, mock_system_tray_available
    ):
        """测试Unix系统上的进程终止"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
            patch("os.name", "posix"),
            patch("os.killpg") as mock_killpg,
        ):
            from src.gui.main_window import Window

            window = Window()
            mock_process = Mock()
            mock_process.wait.return_value = None
            window.r_process = mock_process

            result = window.terminate_process(timeout=5)

            # 验证使用 killpg
            mock_killpg.assert_called_once()
            assert result is True

    def test_run_cmd_valid_params(
        self, mock_config_manager, mock_system_tray_available
    ):
        """测试运行有效命令"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
            patch("src.main.subprocess.Popen") as mock_popen,
            patch("src.main.Path") as mock_path,
            patch("src.main.pps_config.PROGRAM_PATH", "/test/path"),
            patch("os.name", "nt"),
        ):
            from src.gui.main_window import Window

            window = Window()
            mock_process = Mock()
            mock_process.poll.return_value = None  # 进程正在运行
            mock_popen.return_value = mock_process

            # 创建存在的文件mock
            mock_exe_path = Mock()
            mock_exe_path.exists.return_value = True
            mock_path.return_value = mock_exe_path

            window.run_cmd("3proxy", "test_proxy", "8080")

            # 验证子进程被创建
            mock_popen.assert_called_once()
            assert window.r_process == mock_process

    def test_run_cmd_invalid_params(
        self, mock_config_manager, mock_system_tray_available
    ):
        """测试运行命令时的参数验证"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
        ):
            from src.gui.main_window import Window

            window = Window()

            # 测试无效参数
            with pytest.raises(Exception):  # 应该抛出 ConfigError
                window.run_cmd(None, "test_proxy", "8080")

    def test_run_cmd_invalid_port(
        self, mock_config_manager, mock_system_tray_available
    ):
        """测试运行命令时的端口验证"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
        ):
            from src.gui.main_window import Window

            window = Window()

            # 测试无效端口
            with pytest.raises(Exception):  # 应该抛出 ConfigError
                window.run_cmd("ip_relay", "test_proxy", "99999")

    def test_run_cmd_file_not_found(
        self, mock_config_manager, mock_system_tray_available
    ):
        """测试找不到可执行文件的情况"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
            patch("src.main.subprocess.Popen") as mock_popen,
            patch("src.main.Path") as mock_path,
            patch("src.main.pps_config.PROGRAM_PATH", "/test/path"),
            patch("os.name", "nt"),
        ):
            from src.gui.main_window import Window

            window = Window()
            mock_popen.side_effect = FileNotFoundError()

            # 创建不存在的文件mock
            mock_exe_path = Mock()
            mock_exe_path.exists.return_value = False
            mock_path.return_value = mock_exe_path

            with pytest.raises(Exception):  # 应该抛出 ProxyStartError
                window.run_cmd("3proxy", "test_proxy", "8080")

    def test_run_cmd_permission_error(
        self, mock_config_manager, mock_system_tray_available
    ):
        """测试权限错误"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
            patch("src.main.subprocess.Popen") as mock_popen,
            patch("src.main.Path") as mock_path,
            patch("src.main.pps_config.PROGRAM_PATH", "/test/path"),
            patch("os.name", "nt"),
        ):
            from src.gui.main_window import Window

            window = Window()
            mock_popen.side_effect = PermissionError()

            # 创建存在的文件mock
            mock_exe_path = Mock()
            mock_exe_path.exists.return_value = True
            mock_path.return_value = mock_exe_path

            with pytest.raises(Exception):  # 应该抛出 ProxyStartError
                window.run_cmd("3proxy", "test_proxy", "8080")

    def test_is_process_running(self, mock_config_manager, mock_system_tray_available):
        """测试进程运行状态检查"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
        ):
            from src.gui.main_window import Window

            window = Window()

            # 测试无进程
            window.r_process = None
            assert window.is_process_running() is False

            # 测试运行中的进程
            mock_process = Mock()
            mock_process.poll.return_value = None
            window.r_process = mock_process
            assert window.is_process_running() is True

            # 测试已退出的进程
            mock_process.poll.return_value = 0
            assert window.is_process_running() is False

    def test_get_process_info(self, mock_config_manager, mock_system_tray_available):
        """测试获取进程信息"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
        ):
            from src.gui.main_window import Window

            window = Window()

            # 测试无进程
            window.r_process = None
            assert window.get_process_info() == "No process"

            # 测试运行中的进程
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_process.pid = 12345
            window.r_process = mock_process
            assert "Running (PID: 12345)" in window.get_process_info()

            # 测试已退出的进程
            mock_process.poll.return_value = 0
            mock_process.returncode = 1
            assert "Exited with code: 1" in window.get_process_info()

    def test_show_welcome(self, mock_config_manager, mock_system_tray_available):
        """测试显示欢迎信息"""
        with (
            patch("src.gui.main_window.QtCore.QTranslator"),
            patch("src.gui.main_window.QCoreApplication.instance"),
            patch("src.gui.main_window.logger"),
        ):
            from src.gui.main_window import Window

            window = Window()
            window.trayIcon = Mock()

            window.showWelcome()

            # 验证显示消息
            window.trayIcon.showMessage.assert_called_once()


@pytest.mark.skipif(not HAS_QT, reason="PySide6 not available")
class TestAddProxyDialog:
    """AddProxy_Dialog 类测试"""

    def test_dialog_init(self):
        """测试对话框初始化"""
        with patch("src.main.ProxyValidator") as mock_validator:
            from src.gui.add_proxy_dialog import AddProxy_Dialog

            dialog = AddProxy_Dialog()

            # 验证验证器被设置
            mock_validator.assert_called_once()

    def test_dialog_done_accepted_valid(self):
        """测试对话框接受有效输入"""
        with (
            patch("src.main.ProxyValidator") as mock_validator_class,
            patch("src.main.QtWidgets.QMessageBox") as mock_message_box,
        ):
            mock_validator = Mock()
            mock_validator_class.return_value = mock_validator

            from src.gui.add_proxy_dialog import AddProxy_Dialog

            dialog = AddProxy_Dialog()
            dialog.le_proxy_name = Mock()
            dialog.le_proxy_name.text.return_value = "test_proxy"
            dialog.le_address = Mock()
            dialog.le_address.text.return_value = "192.168.1.1"
            dialog.le_port = Mock()
            dialog.le_port.text.return_value = "8080"
            dialog.comboBox_type = Mock()
            dialog.comboBox_type.currentText.return_value = "HTTP"
            dialog.le_username = Mock()
            dialog.le_username.text.return_value = ""
            dialog.le_password = Mock()
            dialog.le_password.text.return_value = ""

            # Mock父类的done方法
            with patch.object(
                dialog.__class__.__bases__[0], "done"
            ) as mock_parent_done:
                dialog.done(QtWidgets.QDialog.DialogCode.Accepted)

                # 验证验证器被调用
                mock_validator.validate_full_proxy.assert_called_once()
                mock_parent_done.assert_called_once_with(
                    QtWidgets.QDialog.DialogCode.Accepted
                )

    def test_dialog_done_accepted_invalid(self):
        """测试对话框接受无效输入"""
        with (
            patch("src.main.ProxyValidator") as mock_validator_class,
            patch("src.main.QtWidgets.QMessageBox") as mock_message_box,
        ):
            mock_validator = Mock()
            mock_validator.validate_full_proxy.side_effect = Exception(
                "Validation error"
            )
            mock_validator_class.return_value = mock_validator

            from src.gui.add_proxy_dialog import AddProxy_Dialog

            dialog = AddProxy_Dialog()
            dialog.le_proxy_name = Mock()
            dialog.le_proxy_name.text.return_value = ""
            dialog.le_address = Mock()
            dialog.le_address.text.return_value = "invalid"
            dialog.le_port = Mock()
            dialog.le_port.text.return_value = ""
            dialog.comboBox_type = Mock()
            dialog.comboBox_type.currentText.return_value = "HTTP"
            dialog.le_username = Mock()
            dialog.le_username.text.return_value = ""
            dialog.le_password = Mock()
            dialog.le_password.text.return_value = ""

            # Mock父类的done方法
            with patch.object(
                dialog.__class__.__bases__[0], "done"
            ) as mock_parent_done:
                dialog.done(QtWidgets.QDialog.DialogCode.Accepted)

                # 验证错误消息框被显示
                mock_message_box.warning.assert_called_once()
                mock_parent_done.assert_not_called()  # 不应该调用父类的done方法


@pytest.mark.skipif(not HAS_QT, reason="PySide6 not available")
class TestProxyDelegates:
    """代理委托类测试"""

    def test_proxy_type_delegate(self):
        """测试代理类型委托"""
        from src.gui.delegates import ProxyTypeDelegate

        delegate = ProxyTypeDelegate()

        # 测试编辑器创建
        editor = delegate.createEditor(None, None, None)
        assert isinstance(editor, QtWidgets.QComboBox)

        # 验证项目被添加
        assert editor.findText("HTTP") >= 0
        assert editor.findText("SOCKS4") >= 0
        assert editor.findText("SOCKS5") >= 0

    def test_proxy_port_delegate(self):
        """测试代理端口委托"""
        from src.gui.delegates import ProxyPortDelegate

        delegate = ProxyPortDelegate()

        # 测试编辑器创建
        editor = delegate.createEditor(None, None, None)
        assert isinstance(editor, QtWidgets.QLineEdit)

        # 验证验证器被设置
        validator = editor.validator()
        assert isinstance(validator, QtGui.QIntValidator)

    def test_proxy_name_delegate(self):
        """测试代理名称委托"""
        with patch("src.main.ProxyValidator") as mock_validator_class:
            mock_validator = Mock()
            mock_validator_class.return_value = mock_validator

            from src.gui.delegates import ProxyNameDelegate

            delegate = ProxyNameDelegate()

            # 测试编辑器创建
            editor = delegate.createEditor(None, None, None)
            assert isinstance(editor, QtWidgets.QLineEdit)

            # 验证验证器被设置
            mock_validator.get_name_validator.assert_called_once()


@pytest.mark.skipif(not HAS_QT, reason="PySide6 not available")
class TestConfigDialog:
    """Config_Dialog 类测试"""

    def test_config_dialog_init(self):
        """测试配置对话框初始化"""
        with (
            patch("src.config.ConfigManager") as mock_config_class,
            patch("src.main.ProxyValidator") as mock_validator_class,
            patch("src.main.BatchImportValidator") as mock_batch_validator_class,
        ):
            mock_config = Mock()
            mock_config.get.side_effect = lambda key: {
                "LANG": "zh_CN",
                "DEBUG": 0,
                "SHOW_WELCOME": 0,
                "CMD": "3proxy",
                "LOCAL_PORT": 8888,
            }.get(key)
            mock_config.get_proxies.return_value = []
            mock_config_class.return_value = mock_config

            from src.gui.config_dialog import Config_Dialog

            parent = Mock()
            parent.dialog_exsit = False

            dialog = Config_Dialog(parent)

            # 验证配置管理器被创建
            mock_config_class.assert_called_once()

            # 验证验证器被创建
            mock_validator_class.assert_called_once()
            mock_batch_validator_class.assert_called_once()


def test_pps_quote():
    """测试 pps_quote 函数"""
    from src.main import pps_quote

    # 测试普通字符串
    assert pps_quote("test") == '"test"'

    # 测试包含双引号的字符串
    assert pps_quote('test"quote') == '"test\\"quote"'

    # 测试包含反斜杠的字符串
    assert pps_quote("test\\path") == '"test\\\\\\\\path"'


@pytest.mark.skipif(not HAS_QT, reason="PySide6 not available")
def test_main_function():
    """测试 main 函数"""
    with (
        patch("src.main.QtWidgets.QApplication") as mock_app,
        patch("src.main.Window") as mock_window,
    ):
        from src.main import main

        main()

        # 验证应用程序被创建和执行
        mock_app.assert_called_once()
        mock_app.return_value.exec.assert_called_once()
