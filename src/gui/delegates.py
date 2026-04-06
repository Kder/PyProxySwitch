#!/usr/bin/env python3

"""
UI代理类模块 - 包含tableView的各种代理类

此模块包含用于表格视图编辑的各种代理类，提供输入验证和用户界面。
"""

from PySide6 import QtCore, QtGui, QtWidgets

from src.proxy_validation import ProxyValidator


class ProxyTypeDelegate(QtWidgets.QStyledItemDelegate):
    '''tableView的combobox代理，用于设置代理类型'''
    def createEditor(self, parent, option, index):
        '''创建QComboBox'''
        editor = QtWidgets.QComboBox(parent)
        editor.addItem('HTTP')
        editor.addItem('SOCKS4')
        editor.addItem('SOCKS5')

        return editor

    def setEditorData(self, combobox, index):
        '''设置当前选择框的值'''
        value = index.model().data(index, QtCore.Qt.ItemDataRole.EditRole)
        combobox.setCurrentIndex(combobox.findText(value))
        # comboBox.setItemText(0, value)

    def setModelData(self, combobox, model, index):
        '''设置对应的model的data'''
        value = combobox.currentText()
        model.setData(index, value, QtCore.Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        '''更新Editor'''
        editor.setGeometry(option.rect)


class ProxyPortDelegate(QtWidgets.QStyledItemDelegate):
    '''tableView的lineedit代理，用于限制输入数据类型为整数'''
    def createEditor(self, parent, option, index):
        '''创建LineEdit'''
        editor = QtWidgets.QLineEdit(parent)
        editor.setValidator(QtGui.QIntValidator(0, 65535, self))

        return editor

    def setEditorData(self, line_editor, index):
        '''设置当前文本框的值'''
        value = index.model().data(index, QtCore.Qt.ItemDataRole.EditRole)
        line_editor.setText(value)

    def setModelData(self, line_editor, model, index):
        '''设置对应的model的data'''
        value = line_editor.text()
        model.setData(index, value, QtCore.Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        '''更新Editor'''
        editor.setGeometry(option.rect)


class ProxyNameDelegate(QtWidgets.QStyledItemDelegate):
    '''tableView的lineedit代理，用于限制输入数据不含特殊字符'''
    def __init__(self, parent=None, validator=None):
        '''初始化UI'''
        QtWidgets.QStyledItemDelegate.__init__(self, parent)
        self.validator = validator or ProxyValidator()

    def createEditor(self, parent, option, index):
        '''创建LineEdit'''
        editor = QtWidgets.QLineEdit(parent)
        editor.setValidator(self.validator.get_name_validator())

        return editor

    def setEditorData(self, line_editor, index):
        '''设置当前文本框的值'''
        value = index.model().data(index, QtCore.Qt.ItemDataRole.EditRole)
        line_editor.setText(value)

    def setModelData(self, line_editor, model, index):
        '''设置对应的model的data'''
        value = line_editor.text()
        model.setData(index, value, QtCore.Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        '''更新Editor'''
        editor.setGeometry(option.rect)
