# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'add_proxy.ui'
#
# Created: Tue Mar 01 22:13:07 2011
#      by: PyQt4 UI code generator 4.8.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_Dialog_AddProxy(object):
    def setupUi(self, Dialog_AddProxy):
        Dialog_AddProxy.setObjectName(_fromUtf8("Dialog_AddProxy"))
        Dialog_AddProxy.resize(381, 242)
        self.label_user = QtGui.QLabel(Dialog_AddProxy)
        self.label_user.setGeometry(QtCore.QRect(20, 120, 51, 20))
        self.label_user.setObjectName(_fromUtf8("label_user"))
        self.checkBox_proxy_auth = QtGui.QCheckBox(Dialog_AddProxy)
        self.checkBox_proxy_auth.setGeometry(QtCore.QRect(20, 90, 191, 18))
        self.checkBox_proxy_auth.setObjectName(_fromUtf8("checkBox_proxy_auth"))
        self.le_username = QtGui.QLineEdit(Dialog_AddProxy)
        self.le_username.setEnabled(False)
        self.le_username.setGeometry(QtCore.QRect(80, 120, 113, 20))
        self.le_username.setObjectName(_fromUtf8("le_username"))
        self.label_name = QtGui.QLabel(Dialog_AddProxy)
        self.label_name.setGeometry(QtCore.QRect(20, 30, 51, 20))
        self.label_name.setObjectName(_fromUtf8("label_name"))
        self.label_pass = QtGui.QLabel(Dialog_AddProxy)
        self.label_pass.setGeometry(QtCore.QRect(20, 150, 51, 20))
        self.label_pass.setObjectName(_fromUtf8("label_pass"))
        self.le_password = QtGui.QLineEdit(Dialog_AddProxy)
        self.le_password.setEnabled(False)
        self.le_password.setGeometry(QtCore.QRect(80, 150, 113, 20))
        self.le_password.setEchoMode(QtGui.QLineEdit.Password)
        self.le_password.setObjectName(_fromUtf8("le_password"))
        self.label_port = QtGui.QLabel(Dialog_AddProxy)
        self.label_port.setGeometry(QtCore.QRect(240, 60, 31, 21))
        self.label_port.setObjectName(_fromUtf8("label_port"))
        self.le_port = QtGui.QLineEdit(Dialog_AddProxy)
        self.le_port.setGeometry(QtCore.QRect(280, 60, 41, 20))
        self.le_port.setMaxLength(5)
        self.le_port.setObjectName(_fromUtf8("le_port"))
        self.le_proxy_name = QtGui.QLineEdit(Dialog_AddProxy)
        self.le_proxy_name.setGeometry(QtCore.QRect(80, 30, 140, 20))
        self.le_proxy_name.setMaxLength(255)
        self.le_proxy_name.setObjectName(_fromUtf8("le_proxy_name"))
        self.label_addr = QtGui.QLabel(Dialog_AddProxy)
        self.label_addr.setGeometry(QtCore.QRect(20, 60, 51, 20))
        self.label_addr.setObjectName(_fromUtf8("label_addr"))
        self.le_address = QtGui.QLineEdit(Dialog_AddProxy)
        self.le_address.setGeometry(QtCore.QRect(80, 60, 140, 20))
        self.le_address.setMaxLength(255)
        self.le_address.setObjectName(_fromUtf8("le_address"))
        self.comboBox_type = QtGui.QComboBox(Dialog_AddProxy)
        self.comboBox_type.setGeometry(QtCore.QRect(280, 30, 61, 22))
        self.comboBox_type.setObjectName(_fromUtf8("comboBox_type"))
        self.comboBox_type.addItem(_fromUtf8(""))
        self.comboBox_type.addItem(_fromUtf8(""))
        self.comboBox_type.addItem(_fromUtf8(""))
        self.label_type = QtGui.QLabel(Dialog_AddProxy)
        self.label_type.setGeometry(QtCore.QRect(240, 30, 30, 21))
        self.label_type.setObjectName(_fromUtf8("label_type"))
        self.buttonBox = QtGui.QDialogButtonBox(Dialog_AddProxy)
        self.buttonBox.setGeometry(QtCore.QRect(180, 200, 156, 23))
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))

        self.retranslateUi(Dialog_AddProxy)
        QtCore.QObject.connect(self.checkBox_proxy_auth, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), self.le_username.setEnabled)
        QtCore.QObject.connect(self.checkBox_proxy_auth, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), self.le_password.setEnabled)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), Dialog_AddProxy.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), Dialog_AddProxy.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog_AddProxy)
        Dialog_AddProxy.setTabOrder(self.le_proxy_name, self.comboBox_type)
        Dialog_AddProxy.setTabOrder(self.comboBox_type, self.le_address)
        Dialog_AddProxy.setTabOrder(self.le_address, self.le_port)
        Dialog_AddProxy.setTabOrder(self.le_port, self.checkBox_proxy_auth)
        Dialog_AddProxy.setTabOrder(self.checkBox_proxy_auth, self.le_username)
        Dialog_AddProxy.setTabOrder(self.le_username, self.le_password)

    def retranslateUi(self, Dialog_AddProxy):
        Dialog_AddProxy.setWindowTitle(QtGui.QApplication.translate("Dialog_AddProxy", "Add Proxy", None, QtGui.QApplication.UnicodeUTF8))
        self.label_user.setText(QtGui.QApplication.translate("Dialog_AddProxy", "Username", None, QtGui.QApplication.UnicodeUTF8))
        self.checkBox_proxy_auth.setText(QtGui.QApplication.translate("Dialog_AddProxy", "&Authorization", None, QtGui.QApplication.UnicodeUTF8))
        self.label_name.setText(QtGui.QApplication.translate("Dialog_AddProxy", "Name", "lable_name", QtGui.QApplication.UnicodeUTF8))
        self.label_pass.setText(QtGui.QApplication.translate("Dialog_AddProxy", "Password", None, QtGui.QApplication.UnicodeUTF8))
        self.label_port.setText(QtGui.QApplication.translate("Dialog_AddProxy", "Port", None, QtGui.QApplication.UnicodeUTF8))
        self.label_addr.setText(QtGui.QApplication.translate("Dialog_AddProxy", "Address", None, QtGui.QApplication.UnicodeUTF8))
        self.comboBox_type.setItemText(0, QtGui.QApplication.translate("Dialog_AddProxy", "HTTP", None, QtGui.QApplication.UnicodeUTF8))
        self.comboBox_type.setItemText(1, QtGui.QApplication.translate("Dialog_AddProxy", "SOCKS4", None, QtGui.QApplication.UnicodeUTF8))
        self.comboBox_type.setItemText(2, QtGui.QApplication.translate("Dialog_AddProxy", "SOCKS5", None, QtGui.QApplication.UnicodeUTF8))
        self.label_type.setText(QtGui.QApplication.translate("Dialog_AddProxy", "Type", None, QtGui.QApplication.UnicodeUTF8))

