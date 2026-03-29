# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'add_proxy.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QLabel, QLineEdit,
    QSizePolicy, QWidget)

class Ui_Dialog_AddProxy(object):
    def setupUi(self, Dialog_AddProxy):
        if not Dialog_AddProxy.objectName():
            Dialog_AddProxy.setObjectName(u"Dialog_AddProxy")
        Dialog_AddProxy.resize(381, 242)
        self.label_user = QLabel(Dialog_AddProxy)
        self.label_user.setObjectName(u"label_user")
        self.label_user.setGeometry(QRect(20, 120, 51, 20))
        self.checkBox_proxy_auth = QCheckBox(Dialog_AddProxy)
        self.checkBox_proxy_auth.setObjectName(u"checkBox_proxy_auth")
        self.checkBox_proxy_auth.setGeometry(QRect(20, 90, 191, 18))
        self.le_username = QLineEdit(Dialog_AddProxy)
        self.le_username.setObjectName(u"le_username")
        self.le_username.setEnabled(False)
        self.le_username.setGeometry(QRect(80, 120, 113, 20))
        self.label_name = QLabel(Dialog_AddProxy)
        self.label_name.setObjectName(u"label_name")
        self.label_name.setGeometry(QRect(20, 30, 51, 20))
        self.label_pass = QLabel(Dialog_AddProxy)
        self.label_pass.setObjectName(u"label_pass")
        self.label_pass.setGeometry(QRect(20, 150, 51, 20))
        self.le_password = QLineEdit(Dialog_AddProxy)
        self.le_password.setObjectName(u"le_password")
        self.le_password.setEnabled(False)
        self.le_password.setGeometry(QRect(80, 150, 113, 20))
        self.le_password.setEchoMode(QLineEdit.Password)
        self.label_port = QLabel(Dialog_AddProxy)
        self.label_port.setObjectName(u"label_port")
        self.label_port.setGeometry(QRect(240, 60, 31, 21))
        self.le_port = QLineEdit(Dialog_AddProxy)
        self.le_port.setObjectName(u"le_port")
        self.le_port.setGeometry(QRect(280, 60, 41, 20))
        self.le_port.setMaxLength(5)
        self.le_proxy_name = QLineEdit(Dialog_AddProxy)
        self.le_proxy_name.setObjectName(u"le_proxy_name")
        self.le_proxy_name.setGeometry(QRect(80, 30, 140, 20))
        self.le_proxy_name.setMaxLength(255)
        self.label_addr = QLabel(Dialog_AddProxy)
        self.label_addr.setObjectName(u"label_addr")
        self.label_addr.setGeometry(QRect(20, 60, 51, 20))
        self.le_address = QLineEdit(Dialog_AddProxy)
        self.le_address.setObjectName(u"le_address")
        self.le_address.setGeometry(QRect(80, 60, 140, 20))
        self.le_address.setMaxLength(255)
        self.comboBox_type = QComboBox(Dialog_AddProxy)
        self.comboBox_type.addItem("")
        self.comboBox_type.addItem("")
        self.comboBox_type.addItem("")
        self.comboBox_type.setObjectName(u"comboBox_type")
        self.comboBox_type.setGeometry(QRect(280, 30, 61, 22))
        self.label_type = QLabel(Dialog_AddProxy)
        self.label_type.setObjectName(u"label_type")
        self.label_type.setGeometry(QRect(240, 30, 30, 21))
        self.buttonBox = QDialogButtonBox(Dialog_AddProxy)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setGeometry(QRect(180, 200, 156, 23))
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        QWidget.setTabOrder(self.le_proxy_name, self.comboBox_type)
        QWidget.setTabOrder(self.comboBox_type, self.le_address)
        QWidget.setTabOrder(self.le_address, self.le_port)
        QWidget.setTabOrder(self.le_port, self.checkBox_proxy_auth)
        QWidget.setTabOrder(self.checkBox_proxy_auth, self.le_username)
        QWidget.setTabOrder(self.le_username, self.le_password)

        self.retranslateUi(Dialog_AddProxy)
        self.checkBox_proxy_auth.toggled.connect(self.le_username.setEnabled)
        self.checkBox_proxy_auth.toggled.connect(self.le_password.setEnabled)
        self.buttonBox.accepted.connect(Dialog_AddProxy.accept)
        self.buttonBox.rejected.connect(Dialog_AddProxy.reject)

        QMetaObject.connectSlotsByName(Dialog_AddProxy)
    # setupUi

    def retranslateUi(self, Dialog_AddProxy):
        Dialog_AddProxy.setWindowTitle(QCoreApplication.translate("Dialog_AddProxy", u"Add Proxy", None))
        self.label_user.setText(QCoreApplication.translate("Dialog_AddProxy", u"Username", None))
        self.checkBox_proxy_auth.setText(QCoreApplication.translate("Dialog_AddProxy", u"&Authorization", None))
        self.label_name.setText(QCoreApplication.translate("Dialog_AddProxy", u"Name", u"lable_name"))
        self.label_pass.setText(QCoreApplication.translate("Dialog_AddProxy", u"Password", None))
        self.label_port.setText(QCoreApplication.translate("Dialog_AddProxy", u"Port", None))
        self.label_addr.setText(QCoreApplication.translate("Dialog_AddProxy", u"Address", None))
        self.comboBox_type.setItemText(0, QCoreApplication.translate("Dialog_AddProxy", u"HTTP", None))
        self.comboBox_type.setItemText(1, QCoreApplication.translate("Dialog_AddProxy", u"SOCKS4", None))
        self.comboBox_type.setItemText(2, QCoreApplication.translate("Dialog_AddProxy", u"SOCKS5", None))

        self.label_type.setText(QCoreApplication.translate("Dialog_AddProxy", u"Type", None))
    # retranslateUi

