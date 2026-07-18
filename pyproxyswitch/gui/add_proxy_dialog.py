#!/usr/bin/env python3

"""
添加代理对话框模块 - 用于添加单个代理的对话框

此模块包含AddProxy_Dialog类，提供用户友好的代理添加界面。
"""

from PySide6 import QtGui, QtWidgets

from pyproxyswitch.proxy_validation import ProxyValidator, ValidationError

# 导入UI文件
from pyproxyswitch.resources.add_proxy_ui import Ui_Dialog_AddProxy


class AddProxy_Dialog(QtWidgets.QDialog, Ui_Dialog_AddProxy):
    '''"添加代理"对话框'''

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        '''初始化UI'''
        super().__init__(parent)
        self.setupUi(self)
        self.validator = ProxyValidator()
        self.setFixedSize(381, 242)
        self.setWindowIcon(QtGui.QIcon(':/img/pps.png'))
        self.le_proxy_name.setFocus()
        self.le_port.setValidator(self.validator.get_port_validator())
        self.le_proxy_name.setValidator(self.validator.get_name_validator())
        self.le_username.setValidator(self.validator.get_username_validator())
        self.le_password.setValidator(self.validator.get_password_validator())

    def done(self, retcode: int) -> None:
        '''验证代理项目是否符合要求'''
        if retcode == QtWidgets.QDialog.DialogCode.Accepted:
            try:
                # 使用增强验证器验证所有参数
                name = self.le_proxy_name.text().strip()
                address = self.le_address.text().strip()
                port = self.le_port.text().strip()
                proxy_type = self.comboBox_type.currentText()
                username = self.le_username.text()
                password = self.le_password.text()

                # 执行完整验证
                validated = self.validator.validate_full_proxy(
                    name, address, port, proxy_type, username, password
                )

                # 保存验证器产生的规范化值，避免空格、IPv6 方括号等重新进入配置。
                validated_name, validated_address, validated_port, validated_type, user, pwd = (
                    validated
                )
                self.le_proxy_name.setText(validated_name)
                self.le_address.setText(validated_address)
                self.le_port.setText(str(validated_port))
                self.comboBox_type.setCurrentText(validated_type)
                self.le_username.setText(user)
                self.le_password.setText(pwd)

                # 验证通过
                super().done(retcode)

            except ValidationError as e:
                # 显示错误信息
                QtWidgets.QMessageBox.warning(
                    self,
                    self.tr('Validation Error'),
                    str(e),
                    QtWidgets.QMessageBox.StandardButton.Ok
                )
        else:
            super().done(retcode)
