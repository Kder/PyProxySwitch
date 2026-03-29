#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
添加代理对话框模块 - 用于添加单个代理的对话框

此模块包含AddProxy_Dialog类，提供用户友好的代理添加界面。
"""

from PySide6 import QtGui, QtWidgets

from src.proxy_validation import ProxyValidator, ValidationError

# 导入UI文件
from res.add_proxy_ui import Ui_Dialog_AddProxy


class AddProxy_Dialog(QtWidgets.QDialog, Ui_Dialog_AddProxy):
    '''"添加代理"对话框'''
    def __init__(self, parent=None):
        '''初始化UI'''
        super().__init__(parent)
        # change_language(qApp, pps_config.CONFIG['LANG'])
        self.setupUi(self)
        self.validator = ProxyValidator()
        self.setFixedSize(381, 242)
        # self.setAttribute(Qt.WA_DeleteOnClose)
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
                username = self.le_username.text().strip()
                password = self.le_password.text().strip()

                # 执行完整验证
                self.validator.validate_full_proxy(
                    name, address, port, proxy_type, username, password
                )

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

    def show_error(self, message: str):
        '''显示验证错误信息'''
        QtWidgets.QMessageBox.warning(
            self,
            self.tr('验证错误'),
            message,
            QtWidgets.QMessageBox.StandardButton.Ok
        )