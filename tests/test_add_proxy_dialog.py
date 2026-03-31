#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyProxySwitch 添加代理对话框测试

测试 AddProxy_Dialog 类的功能。
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Any

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestAddProxyDialog:
    """测试 AddProxy_Dialog 类"""

    @pytest.fixture
    def mock_qt_modules(self):
        """模拟 Qt 模块"""
        with patch.dict('sys.modules', {
            'PySide6': MagicMock(),
            'PySide6.QtGui': MagicMock(),
            'PySide6.QtWidgets': MagicMock(),
            'res': MagicMock(),
            'res.add_proxy_ui': MagicMock(),
        }) as mock_modules:
            # 模拟 Ui_Dialog_AddProxy
            mock_ui = MagicMock()
            mock_ui.setupUi = Mock()
            mock_modules['res.add_proxy_ui'].Ui_Dialog_AddProxy.return_value = mock_ui

            # 模拟 QDialog
            mock_dialog = MagicMock()
            mock_dialog.DialogCode = Mock()
            mock_dialog.DialogCode.Accepted = 1
            mock_dialog.DialogCode.Rejected = 0
            mock_modules['PySide6.QtWidgets'].QDialog = Mock(return_value=mock_dialog)
            mock_modules['PySide6.QtWidgets'].QMessageBox = Mock()
            mock_modules['PySide6.QtWidgets'].QMessageBox.warning = Mock()
            mock_modules['PySide6.QtWidgets'].QMessageBox.StandardButton = Mock()
            mock_modules['PySide6.QtWidgets'].QMessageBox.StandardButton.Ok = 1

            # 模拟 QIcon
            mock_modules['PySide6.QtGui'].QIcon = Mock()

            yield mock_modules

    @pytest.fixture
    def mock_validator(self):
        """模拟验证器"""
        with patch('src.proxy_validation.ProxyValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.get_port_validator.return_value = Mock()
            mock_validator.get_name_validator.return_value = Mock()
            mock_validator.get_username_validator.return_value = Mock()
            mock_validator.get_password_validator.return_value = Mock()
            mock_validator.validate_full_proxy = Mock()

            mock_validator_class.return_value = mock_validator
            yield mock_validator

    def test_add_proxy_dialog_initialization(self, mock_qt_modules, mock_validator):
        """测试对话框初始化 (lines 20-33)"""
        # 导入并创建对话框
        from src.gui.add_proxy_dialog import AddProxy_Dialog

        dialog = AddProxy_Dialog()

        # 验证UI设置
        mock_qt_modules['res.add_proxy_ui'].Ui_Dialog_AddSetup.setupUi.assert_called_once_with(dialog)

        # 验证验证器创建
        mock_validator.assert_called_once()

        # 验证UI元素设置
        assert dialog.validator == mock_validator
        dialog.setFixedSize.assert_called_once_with(381, 242)
        dialog.setWindowIcon.assert_called_once()
        dialog.le_proxy_name.setFocus.assert_called_once()

        # 验证输入验证器
        dialog.le_port.setValidator.assert_called_once_with(mock_validator.get_port_validator.return_value)
        dialog.le_proxy_name.setValidator.assert_called_once_with(mock_validator.get_name_validator.return_value)
        dialog.le_username.setValidator.assert_called_once_with(mock_validator.get_username_validator.return_value)
        dialog.le_password.setValidator.assert_called_once_with(mock_validator.get_password_validator.return_value)

    def test_done_with_accepted_validation_success(self, mock_qt_modules, mock_validator):
        """测试 done() 方法在验证成功时 (lines 35-53)"""
        from src.gui.add_proxy_dialog import AddProxy_Dialog
        from src.proxy_validation import ValidationError

        dialog = AddProxy_Dialog()

        # 模拟UI元素
        dialog.le_proxy_name.text.return_value = "test_proxy"
        dialog.le_address.text.return_value = "192.168.1.1"
        dialog.le_port.text.return_value = "8080"
        dialog.comboBox_type.currentText.return_value = "HTTP"
        dialog.le_username.text.return_value = ""
        dialog.le_password.text.return_value = ""

        # 模拟验证成功
        mock_validator.validate_full_proxy.return_value = None

        # 调用 done() 方法
        dialog.done(1)  # Accepted

        # 验证验证器调用
        mock_validator.validate_full_proxy.assert_called_once_with(
            "test_proxy", "192.168.1.1", "8080", "HTTP", "", ""
        )

        # 验证父类 done() 被调用
        dialog.super().done.assert_called_once_with(1)

    def test_done_with_accepted_validation_failure(self, mock_qt_modules, mock_validator):
        """测试 done() 方法在验证失败时 (lines 35-62)"""
        from src.gui.add_proxy_dialog import AddProxy_Dialog
        from src.proxy_validation import ValidationError

        dialog = AddProxy_Dialog()

        # 模拟UI元素
        dialog.le_proxy_name.text.return_value = "test_proxy"
        dialog.le_address.text.return_value = "192.168.1.1"
        dialog.le_port.text.return_value = "8080"
        dialog.comboBox_type.currentText.return_value = "HTTP"
        dialog.le_username.text.return_value = ""
        dialog.le_password.text.return_value = ""

        # 模拟验证失败
        mock_validator.validate_full_proxy.side_effect = ValidationError("Invalid proxy")

        # 调用 done() 方法
        dialog.done(1)  # Accepted

        # 验证错误消息框被显示
        mock_qt_modules['PySide6.QtWidgets'].QMessageBox.warning.assert_called_once()

        # 验证父类 done() 没有被调用
        dialog.super().done.assert_not_called()

    def test_done_with_rejected(self, mock_qt_modules, mock_validator):
        """测试 done() 方法在拒绝时 (lines 63-64)"""
        from src.gui.add_proxy_dialog import AddProxy_Dialog

        dialog = AddProxy_Dialog()

        # 调用 done() 方法
        dialog.done(0)  # Rejected

        # 验证验证器没有被调用
        mock_validator.validate_full_proxy.assert_not_called()

        # 验证父类 done() 被调用
        dialog.super().done.assert_called_once_with(0)

    def test_show_error_method(self, mock_qt_modules, mock_validator):
        """测试 show_error() 方法 (lines 66-73)"""
        from src.gui.add_proxy_dialog import AddProxy_Dialog

        dialog = AddProxy_Dialog()

        # 调用 show_error() 方法
        dialog.show_error("Test error message")

        # 验证错误消息框被显示
        mock_qt_modules['PySide6.QtWidgets'].QMessageBox.warning.assert_called_once()

        # 验证调用参数
        call_args = mock_qt_modules['PySide6.QtWidgets'].QMessageBox.warning.call_args
        assert call_args[0][0] == dialog  # 第一个参数是 self
        assert call_args[0][1] == dialog.tr('验证错误')  # 窗口标题
        assert call_args[0][2] == "Test error message"  # 错误消息
        assert call_args[0][3] == 1  # StandardButton.Ok

    def test_validation_error_handling(self, mock_qt_modules, mock_validator):
        """测试验证错误处理的各种情况"""
        from src.gui.add_proxy_dialog import AddProxy_Dialog
        from src.proxy_validation import ValidationError

        dialog = AddProxy_Dialog()

        # 测试各种验证错误
        error_messages = [
            "Invalid proxy name",
            "Invalid address format",
            "Port out of range",
            "Invalid proxy type"
        ]

        for error_msg in error_messages:
            mock_validator.validate_full_proxy.side_effect = ValidationError(error_msg)

            dialog.done(1)  # Accepted

            # 验证错误消息框被显示
            assert mock_qt_modules['PySide6.QtWidgets'].QMessageBox.warning.called

    def test_proxy_validation_parameters(self, mock_qt_modules, mock_validator):
        """测试传递给验证器的参数"""
        from src.gui.add_proxy_dialog import AddProxy_Dialog

        dialog = AddProxy_Dialog()

        # 模拟各种输入值
        test_cases = [
            ("proxy1", "192.168.1.1", "8080", "HTTP", "user", "pass"),
            ("proxy2", "example.com", "3128", "SOCKS5", "", ""),
            ("proxy3", "10.0.0.1", "1080", "SOCKS4", "admin", "secret"),
        ]

        for name, address, port, proxy_type, username, password in test_cases:
            dialog.le_proxy_name.text.return_value = name
            dialog.le_address.text.return_value = address
            dialog.le_port.text.return_value = port
            dialog.comboBox_type.currentText.return_value = proxy_type
            dialog.le_username.text.return_value = username
            dialog.le_password.text.return_value = password

            # 模拟验证成功
            mock_validator.validate_full_proxy.side_effect = None

            dialog.done(1)  # Accepted

            # 验证验证器被正确调用
            mock_validator.validate_full_proxy.assert_called_with(
                name, address, port, proxy_type, username, password
            )

    def test_dialog_inheritance(self, mock_qt_modules, mock_validator):
        """测试对话框继承关系"""
        from src.gui.add_proxy_dialog import AddProxy_Dialog

        dialog = AddProxy_Dialog()

        # 验证继承关系
        assert isinstance(dialog, mock_qt_modules['PySide6.QtWidgets'].QDialog)

    def test_tr_method_usage(self, mock_qt_modules, mock_validator):
        """测试 tr() 方法的使用"""
        from src.gui.add_proxy_dialog import AddProxy_Dialog

        dialog = AddProxy_Dialog()

        # 模拟 tr() 方法
        dialog.tr = Mock(return_value="Validation Error")

        # 触发显示错误
        dialog.show_error("Test message")

        # 验证 tr() 方法被调用
        dialog.tr.assert_called()

if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])