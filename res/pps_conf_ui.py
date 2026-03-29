# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'pps_conf.ui'
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
    QDialog, QDialogButtonBox, QHeaderView, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QTabWidget,
    QTableView, QWidget)

class Ui_Dialog_Config(object):
    def setupUi(self, Dialog_Config):
        if not Dialog_Config.objectName():
            Dialog_Config.setObjectName(u"Dialog_Config")
        Dialog_Config.resize(468, 327)
        font = QFont()
        font.setFamilies([u"SimSun"])
        font.setPointSize(9)
        Dialog_Config.setFont(font)
        self.buttonBox = QDialogButtonBox(Dialog_Config)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setGeometry(QRect(90, 290, 341, 32))
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Close)
        self.tabWidget = QTabWidget(Dialog_Config)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setGeometry(QRect(10, 20, 441, 261))
        self.tab_proxy = QWidget()
        self.tab_proxy.setObjectName(u"tab_proxy")
        self.btn_del = QPushButton(self.tab_proxy)
        self.btn_del.setObjectName(u"btn_del")
        self.btn_del.setGeometry(QRect(200, 200, 75, 23))
        self.btn_add_proxy = QPushButton(self.tab_proxy)
        self.btn_add_proxy.setObjectName(u"btn_add_proxy")
        self.btn_add_proxy.setGeometry(QRect(20, 200, 75, 23))
        self.tableView = QTableView(self.tab_proxy)
        self.tableView.setObjectName(u"tableView")
        self.tableView.setGeometry(QRect(15, 10, 401, 181))
        self.btn_mod = QPushButton(self.tab_proxy)
        self.btn_mod.setObjectName(u"btn_mod")
        self.btn_mod.setGeometry(QRect(110, 200, 75, 23))
        self.btn_batch = QPushButton(self.tab_proxy)
        self.btn_batch.setObjectName(u"btn_batch")
        self.btn_batch.setGeometry(QRect(290, 200, 121, 23))
        self.tabWidget.addTab(self.tab_proxy, "")
        self.tab_advanced = QWidget()
        self.tab_advanced.setObjectName(u"tab_advanced")
        self.label_cmd = QLabel(self.tab_advanced)
        self.label_cmd.setObjectName(u"label_cmd")
        self.label_cmd.setGeometry(QRect(20, 60, 81, 20))
        self.comboBox_cmd = QComboBox(self.tab_advanced)
        self.comboBox_cmd.addItem("")
        self.comboBox_cmd.addItem("")
        self.comboBox_cmd.addItem("")
        self.comboBox_cmd.setObjectName(u"comboBox_cmd")
        self.comboBox_cmd.setGeometry(QRect(100, 60, 91, 22))
        self.label_localport = QLabel(self.tab_advanced)
        self.label_localport.setObjectName(u"label_localport")
        self.label_localport.setGeometry(QRect(20, 100, 81, 20))
        self.le_localport = QLineEdit(self.tab_advanced)
        self.le_localport.setObjectName(u"le_localport")
        self.le_localport.setGeometry(QRect(100, 100, 61, 20))
        self.le_localport.setInputMethodHints(Qt.ImhDigitsOnly)
        self.le_localport.setMaxLength(5)
        self.label_debug = QLabel(self.tab_advanced)
        self.label_debug.setObjectName(u"label_debug")
        self.label_debug.setGeometry(QRect(20, 180, 71, 20))
        self.checkBox_debug = QCheckBox(self.tab_advanced)
        self.checkBox_debug.setObjectName(u"checkBox_debug")
        self.checkBox_debug.setGeometry(QRect(100, 180, 251, 21))
        self.label_lang = QLabel(self.tab_advanced)
        self.label_lang.setObjectName(u"label_lang")
        self.label_lang.setGeometry(QRect(20, 20, 51, 20))
        self.comboBox_lang = QComboBox(self.tab_advanced)
        self.comboBox_lang.addItem("")
        self.comboBox_lang.addItem("")
        self.comboBox_lang.setObjectName(u"comboBox_lang")
        self.comboBox_lang.setGeometry(QRect(100, 20, 141, 22))
        self.label_2 = QLabel(self.tab_advanced)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(200, 60, 211, 31))
        self.label_2.setWordWrap(True)
        self.label_show_welcome = QLabel(self.tab_advanced)
        self.label_show_welcome.setObjectName(u"label_show_welcome")
        self.label_show_welcome.setGeometry(QRect(20, 140, 71, 20))
        self.checkBox_show_welcome = QCheckBox(self.tab_advanced)
        self.checkBox_show_welcome.setObjectName(u"checkBox_show_welcome")
        self.checkBox_show_welcome.setGeometry(QRect(100, 140, 251, 21))
        self.tabWidget.addTab(self.tab_advanced, "")
        QWidget.setTabOrder(self.btn_add_proxy, self.btn_mod)
        QWidget.setTabOrder(self.btn_mod, self.btn_del)
        QWidget.setTabOrder(self.btn_del, self.btn_batch)
        QWidget.setTabOrder(self.btn_batch, self.tableView)
        QWidget.setTabOrder(self.tableView, self.comboBox_lang)
        QWidget.setTabOrder(self.comboBox_lang, self.comboBox_cmd)
        QWidget.setTabOrder(self.comboBox_cmd, self.le_localport)
        QWidget.setTabOrder(self.le_localport, self.checkBox_show_welcome)
        QWidget.setTabOrder(self.checkBox_show_welcome, self.checkBox_debug)
        QWidget.setTabOrder(self.checkBox_debug, self.buttonBox)
        QWidget.setTabOrder(self.buttonBox, self.tabWidget)

        self.retranslateUi(Dialog_Config)
        self.buttonBox.accepted.connect(Dialog_Config.accept)
        self.buttonBox.rejected.connect(Dialog_Config.reject)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(Dialog_Config)
    # setupUi

    def retranslateUi(self, Dialog_Config):
        Dialog_Config.setWindowTitle(QCoreApplication.translate("Dialog_Config", u"PPS Settings", None))
        self.btn_del.setText(QCoreApplication.translate("Dialog_Config", u"&Delete", None))
        self.btn_add_proxy.setText(QCoreApplication.translate("Dialog_Config", u"&Add", None))
        self.btn_mod.setText(QCoreApplication.translate("Dialog_Config", u"&Modify", None))
        self.btn_batch.setText(QCoreApplication.translate("Dialog_Config", u"&Batch Add/Mod/Del", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_proxy), QCoreApplication.translate("Dialog_Config", u"Proxy List", None))
        self.label_cmd.setText(QCoreApplication.translate("Dialog_Config", u"Proxy Tool", None))
        self.comboBox_cmd.setItemText(0, QCoreApplication.translate("Dialog_Config", u"3proxy", None))
        self.comboBox_cmd.setItemText(1, QCoreApplication.translate("Dialog_Config", u"polipo", None))
        self.comboBox_cmd.setItemText(2, QCoreApplication.translate("Dialog_Config", u"ip_relay", None))

        self.label_localport.setText(QCoreApplication.translate("Dialog_Config", u"Local Port", None))
        self.le_localport.setText(QCoreApplication.translate("Dialog_Config", u"8888", None))
        self.label_debug.setText(QCoreApplication.translate("Dialog_Config", u"Debug Mode", None))
        self.checkBox_debug.setText(QCoreApplication.translate("Dialog_Config", u"Show &debug info in console", None))
        self.label_lang.setText(QCoreApplication.translate("Dialog_Config", u"Language", None))
        self.comboBox_lang.setItemText(0, QCoreApplication.translate("Dialog_Config", u"\u7b80\u4f53\u4e2d\u6587", None))
        self.comboBox_lang.setItemText(1, QCoreApplication.translate("Dialog_Config", u"English", None))

        self.label_2.setText(QCoreApplication.translate("Dialog_Config", u"(Don't change this in normal use)", None))
        self.label_show_welcome.setText(QCoreApplication.translate("Dialog_Config", u"Show Welcome", None))
        self.checkBox_show_welcome.setText(QCoreApplication.translate("Dialog_Config", u"Show &welcome info when program start", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_advanced), QCoreApplication.translate("Dialog_Config", u"Advanced", None))
    # retranslateUi

