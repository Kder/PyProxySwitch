#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2009-2011 Kder Lin
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
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
PyProxySwitch is a cross-platform proxy switcher based on polipo, 3proxy and
IP Relay to fast change proxy for browsers(Firefox,Chrome,Opera,IE, etc.) and
other internet applications, writen in Python and PyQt.

Welcom to send me your feedback if you feel it useful.
'''


__author__ = 'Kder'
__copyright__ = 'Copyright 2009-2011 Kder'
__credits__ = ['Kder']

__version__ = '3.5.2'
__date__ = '2011-03-26'
__maintainer__ = "Kder"
__email__ = '[kderlin (#) gmail dot com]'
__url__ = 'http://www.kder.info'
__license__ = 'Apache License, Version 2.0'
__status__ = 'Beta'
__projecturl__ = 'http://pyproxyswitch.kder.info'


import sys
import os
import pps_config
LIBPATH = os.path.join(pps_config.PROGRAM_PATH, 'lib')
OSPATH = os.environ.get('PATH', '').split(os.pathsep)
if LIBPATH not in OSPATH:
    OSPATH.insert(0, LIBPATH)
    os.environ["PATH"] = os.pathsep.join(OSPATH)
#    os.execv(sys.executable, sys.argv)

sys.path.append(os.path.join(pps_config.PROGRAM_PATH, 'res'))
sys.path.append(LIBPATH)

# This is only needed for Python v2 but is harmless for Python v3.
import sip
sip.setapi('QVariant', 2)

from PyQt4 import QtCore, QtGui
try:
    from PyQt4.QtCore import QString
except ImportError:
    # in Python3, QString is not defined
    QString = type("")

import time
import codecs

import pps_qrc
from pps_conf_ui import Ui_Dialog_Config
from add_proxy_ui import Ui_Dialog_AddProxy


class Window(QtGui.QDialog):
    '''主程序UI'''
    def __init__(self):
        '''初始化系统托盘图标和菜单'''
        super(Window, self).__init__()
        self.cmd = pps_config.CONFIG['CMD']
        self.r_process = QtCore.QProcess()

        self.dialog_exsit = False

        translator = QtCore.QTranslator(self)
        translator.load(os.path.join(pps_config.PROGRAM_PATH, 'i18n',
            pps_config.CONFIG['LANG']))
        QtGui.qApp.installTranslator(translator)
        # self.retranslateUi(self)

        if not QtGui.QSystemTrayIcon.isSystemTrayAvailable():
            QtGui.QMessageBox.critical(None, self.tr('System Tray'),
            self.tr('I\'ve not detected any system tray on this system.\n'
            'PyProxySwitch cannot start.'))
            sys.exit(1)

        # self.cfg = eval("pps_config.CONFIG['CFG_%s']" % self.cmd)
        self.proxy_list = pps_config.PROXIES
        self.proxy_names = [i[0] for i in self.proxy_list]

        #根据上次退出时记录的代理项目，读取对应的ip和端口
        self.item_text = pps_config.CONFIG['LAST_ITEM']
        if self.item_text not in self.proxy_names:
            self.item_text = pps_config.CONFIG['DEFAULT_ITEM']
        #
        self.item = self.item_text
        self.port = ''
        if self.cmd == 'ip_relay':
            for i in self.proxy_list:
                if i[0] == self.item_text:
                    self.item = i[1]
                    self.port = i[2]
        else:
            self.proxy_names.append('NoProxy')

        self.icon = QtGui.QIcon(':/img/pps.png')
        self.setWindowIcon(self.icon)
        self.trayIcon = QtGui.QSystemTrayIcon(self)
        self.trayIcon.setIcon(self.icon)
        self.tray_tip = " - PyProxySwitch(%s)" % self.cmd
        self.trayIcon.setToolTip(self.item_text + self.tray_tip)
        self.trayIcon.show()

        # trayiconmenu的context设置成desktop是为了使其能在失去焦点后自动消失
        # 参考了 http://fantasticinblur.javaeye.com/blog/902263
        self.trayIconMenu = QtGui.QMenu(QtGui.QApplication.desktop())
        self.aboutAction = QtGui.QAction(self.tr('&About'), self,
            triggered=self.about)
        self.quitAction = QtGui.QAction(self.tr('&Exit'), self,
            triggered=self.quit)
        self.configAction = QtGui.QAction(self.tr('&Config'), self,
            triggered=self.config)
        self.createActions()

        # self.trayIcon.activated.connect(self.refresh_menu)
        self.connect(self.trayIcon,
            QtCore.SIGNAL('activated(QSystemTrayIcon::ActivationReason)'),
            self.on_activated)

        if pps_config.CONFIG['SHOW_WELCOME'] == 1 or \
                pps_config.CONFIG['FISRT_RUN'] == 1:
            self.showWelcome()
            self.trayIcon.messageClicked.connect(self.config)
            # pps_config.CONFIG['FISRT_RUN'] = 0
        # print(self.cmd, self.item, self.port)
        self.run_cmd(self.cmd, self.item, self.port)

    def refresh_menu(self):
        '''重新读取配置文件并更新菜单'''
        pps_config.CONFIG = pps_config.pps_loadcfg(pps_config.CONF)
        self.cmd = pps_config.CONFIG['CMD']
        self.proxy_list = pps_config.pps_load_proxylist(pps_config.PROXY_LIST)
        self.proxy_names = [i[0] for i in self.proxy_list]
        if self.cmd != 'ip_relay':
            self.proxy_names.append('NoProxy')
        # self.cfg = eval("pps_config.CONFIG['CFG_%s']" % self.cmd)
        self.aboutAction.setText(self.tr('&About'))
        self.quitAction.setText(self.tr('&Exit'))
        self.configAction.setText(self.tr('&Config'))
        self.createActions()

    def on_activated(self, reason):
        '''双击系统托盘图标，弹出设置对话框'''
        if reason == QtGui.QSystemTrayIcon.DoubleClick:
            self.config()
        # elif reason == QtGui.QSystemTrayIcon.Context:
            # self.refresh_menu()
        # if reason == QtGui.QSystemTrayIcon.Trigger:
            # pass

    def createActions(self):
        '''生成托盘菜单'''
        self.ppsActionGroup = QtGui.QActionGroup(self)  # 使多个代理间互斥
        self.ppsActionList = []

        for i in self.proxy_names:
            act = QtGui.QAction(i, self)
            act.setCheckable(True)
            if QString(i) == self.item_text:
                act.setChecked(True)
            else:
                act.setChecked(False)
            self.ppsActionList.append(act)
        for i in self.ppsActionList:
            self.connect(i, QtCore.SIGNAL('triggered()'), self.switchProxy)
            self.ppsActionGroup.addAction(i)

        self.trayIconMenu.clear()
        self.trayIconMenu.addAction(self.aboutAction)
        self.trayIconMenu.addAction(self.quitAction)
        self.trayIconMenu.addAction(self.configAction)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addActions(self.ppsActionList)

        self.trayIcon.setContextMenu(self.trayIconMenu)

    def config(self):
        '''弹出配置对话框'''
        if not self.dialog_exsit:
            self.config_dialog = Config_Dialog(self)
            self.config_dialog.exec_()

        else:
            self.config_dialog.activateWindow()
            self.config_dialog.setFocus()

    def quit(self):
        '''保存配置，结束代理进程，退出主程序'''
        self.trayIcon.setVisible(False)
        pps_config.CONFIG['LAST_ITEM'] = to_str(self.item_text)
        pps_config.pps_savecfg(pps_config.CONFIG)
        self.r_process.kill()
        self.r_process.waitForFinished()
        QtGui.qApp.quit()

    def about(self):
        '''“关于”对话框'''
        msg_about = ('''PyProxySwitch &nbsp;&nbsp;&nbsp;&nbsp; %s%s<br/><br/>
        %s<br/><br/>by %s %s<br/><br/>%s<a href="%s">%s</a><br/>%s<a href="%s">
        %s</a>''') % (self.tr('Version: '),
        __version__, self.tr('''
PyProxySwitch is a cross-platform proxy switcher based on 3proxy, polipo and
IP Relay to fast change proxy for browsers(Firefox,Chrome,Opera,IE, etc.) and
other internet applications, writen in Python and PyQt.

Welcom to send me your feedback if you feel it useful.
'''),
        __author__, __email__, self.tr('\nAuthor website: '),
        __url__, __url__, self.tr('Project website: '),
        __projecturl__, __projecturl__)

        message = QtGui.QMessageBox(QtGui.QMessageBox.NoIcon,
                        self.tr('About'),
                        msg_about,
                        QtGui.QMessageBox.NoButton, self,
                        QtCore.Qt.Dialog)
        message.setIconPixmap(QtGui.QPixmap(':/img/PyProxySwitch.png'))
        message.setTextFormat(QtCore.Qt.RichText)
        message.show()

    def switchProxy(self):
        '''通过结束旧进程，开启新进程的方式，在多个代理间切换
        Switch among proxies by killing old subprocess then opening
         a new one.'''
        sender = self.sender()
        self.item_text = sender.text()
        self.r_process.close()

        for i in self.proxy_names:
            if QString(i) == self.item_text:
                self.item = i
                # self.item = self.cfg[i][0]
                if self.cmd == 'ip_relay':
                    i_index = self.proxy_names.index(i)
                    self.item = self.proxy_list[i_index][1]
                    self.port = self.proxy_list[i_index][2]
                    # pps_config.pps_output('%s %s' % (self.item, self.cmd))
                self.trayIcon.setToolTip(i + self.tray_tip)
        time.sleep(0.1)
        self.run_cmd(self.cmd, self.item, self.port)

    def run_cmd(self, cmd, item, port):
        '''开启代理进程'''
        if os.name == 'nt':
            cmd_bin = os.path.join(pps_config.PROGRAM_PATH, 'bin',
                self.cmd, self.cmd + '.exe')
        else:
            cmd_bin = pps_quote(os.path.join(pps_config.PROGRAM_PATH,
                'bin', self.cmd, self.cmd))
        i = item
        cmd_option = '-c'
        cmd_args = os.path.join(pps_config.PROGRAM_PATH, 'cfg',
            cmd, i + '.conf')
        cmd_args = pps_quote(cmd_args)
        # cmd_option = pps_quote(cmd_option)
        if cmd == '3proxy':
            cmd_option = ''
        elif cmd == 'ip_relay':
            cmd_option = ''
            cmd_args = ' '.join([str(pps_config.CONFIG['LOCAL_PORT']),
                item, port])
        if os.name == 'nt':
            cmd_bin = pps_quote(cmd_bin)

        cmd = '%s %s %s' % (cmd_bin, cmd_option, cmd_args)
#        print(cmd)
        self.r_process.start(cmd)
        self.r_process.waitForStarted()
        # if self.r_process.state() != 2:
        # if self.r_process.error() != 5:
            # print(self.r_process.error(), self.r_process.state())

    def showWelcome(self):
        '''在系统托盘显示欢迎信息'''
        icon = QtGui.QSystemTrayIcon.MessageIcon(1)
        self.trayIcon.showMessage('Hi',
        self.tr('I\'m here, welcome to PyProxySwitch!'), icon, 5 * 1000)


class AddProxy_Dialog(QtGui.QDialog, Ui_Dialog_AddProxy):
    '''“添加代理”对话框'''
    def __init__(self, parent=None):
        '''初始化UI'''
        QtGui.QDialog.__init__(self, parent)
        # change_language(qApp, pps_config.CONFIG['LANG'])
        self.setupUi(self)
        self.setFixedSize(381, 242)
        # self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowIcon(QtGui.QIcon(':/img/pps.png'))
        self.le_proxy_name.setFocus()
        self.le_port.setValidator(QtGui.QIntValidator(0, 65535, self))
        # self.connect(self.btn_ok, QtCore.SIGNAL("clicked()"),
            # self.validate_proxy
        # )

    def done(self, retcode):
        '''验证代理项目是否符合要求'''
        if retcode == QtGui.QDialog.Accepted:
            for i in [self.le_proxy_name, self.le_address, self.le_port]:
                try:
                    stripped = i.text().strip()
                except AttributeError:
                    stripped = i.text().trimmed()
                if stripped == QString(''):
                    QtGui.QToolTip.showText(QtCore.QPoint(
                        self.pos().x() + self.width() / 4,
                        self.pos().y() + 10),
                        self.tr('Name/Address/Port cannot be empty.'), self)
                    break
            else:
                # self.setResult(QtGui.QDialog.Accepted)
                QtGui.QDialog.done(self, retcode)
        else:
            QtGui.QDialog.done(self, retcode)


class ProxyTypeDelegate(QtGui.QItemDelegate):
    '''tableView的combobox代理，用于设置代理类型'''
    def createEditor(self, parent, option, index):
        '''创建QComboBox'''
        editor = QtGui.QComboBox(parent)
        editor.addItem('HTTP')
        editor.addItem('SOCKS4')
        editor.addItem('SOCKS5')

        return editor

    def setEditorData(self, comboBox, index):
        '''设置当前选择框的值'''
        value = index.model().data(index, QtCore.Qt.EditRole)
        comboBox.setCurrentIndex(comboBox.findText(value))
        # comboBox.setItemText(0, value)

    def setModelData(self, comboBox, model, index):
        '''设置对应的model的data'''
        value = comboBox.currentText()
        model.setData(index, value, QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        '''更新Editor'''
        editor.setGeometry(option.rect)


class ProxyPortDelegate(QtGui.QItemDelegate):
    '''tableView的lineedit代理，用于限制输入数据类型为整数'''
    def createEditor(self, parent, option, index):
        '''创建LineEdit'''
        editor = QtGui.QLineEdit(parent)
        editor.setValidator(QtGui.QIntValidator(0, 65535, self))

        return editor

    def setEditorData(self, line_editor, index):
        '''设置当前文本框的值'''
        value = index.model().data(index, QtCore.Qt.EditRole)
        line_editor.setText(value)

    def setModelData(self, line_editor, model, index):
        '''设置对应的model的data'''
        value = line_editor.text()
        model.setData(index, value, QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        '''更新Editor'''
        editor.setGeometry(option.rect)


class ProxyNameDelegate(QtGui.QItemDelegate):
    '''tableView的lineedit代理，用于限制输入数据不含特殊字符'''
    def __init__(self, parent=None, validator=None):
        '''初始化UI'''
        QtGui.QItemDelegate.__init__(self, parent)
        self.validator = validator

    def createEditor(self, parent, option, index):
        '''创建LineEdit'''
        editor = QtGui.QLineEdit(parent)
        editor.setValidator(self.validator)

        return editor

    def setEditorData(self, line_editor, index):
        '''设置当前文本框的值'''
        value = index.model().data(index, QtCore.Qt.EditRole)
        line_editor.setText(value)

    def setModelData(self, line_editor, model, index):
        '''设置对应的model的data'''
        value = line_editor.text()
        model.setData(index, value, QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        '''更新Editor'''
        editor.setGeometry(option.rect)


class Config_Dialog(QtGui.QDialog, Ui_Dialog_Config):
    '''PPS配置对话框'''
    def __init__(self, parent=None):
        '''初始化tableView及各个按钮'''
        QtGui.QDialog.__init__(self, parent)
        self.setupUi(self)
        self.setFixedSize(468, 327)
        self.setWindowIcon(QtGui.QIcon(':/img/pps.png'))
        self.parentWidget().dialog_exsit = True

        (self.proxy_name, self.proxy_address, self.proxy_port, self.proxy_type,
            self.proxy_user, self.proxy_pass) = range(6)
        self.langs = ['zh_CN', 'en']
        self.f_or_t = [False, True]
        self.cmds = ['polipo', 'ip_relay']

        self.comboBox_lang.setCurrentIndex(
            self.langs.index(pps_config.CONFIG['LANG']))
        self.checkBox_debug.setChecked(self.f_or_t[pps_config.CONFIG['DEBUG']])
        self.checkBox_show_welcome.setChecked(
            self.f_or_t[pps_config.CONFIG['SHOW_WELCOME']])
        self.comboBox_cmd.setCurrentIndex(
            self.cmds.index(pps_config.CONFIG['CMD']))

        self.le_localport.setValidator(QtGui.QIntValidator(0, 65535, self))
        self.le_localport.setText(str(pps_config.CONFIG['LOCAL_PORT']))

        self.validator = QtGui.QRegExpValidator(
            QtCore.QRegExp('[^"\\\\\/:\*\?<>\|]+'), self)

        # self.tableView.resizeSection(0, 22)
        # self.proxyModel = SortFilterProxyModel()
#        self.tableView.setRootIsDecorated(False)
        self.tableView.setAlternatingRowColors(True)
        self.tableView.setSortingEnabled(True)
        self.tableView.setModel(self.create_model(parent))
        self.data_model = self.tableView.model()
        self.tableView.setCurrentIndex(self.data_model.index(0, 0))
        self.tableView.setColumnWidth(self.proxy_name, 80)
        self.tableView.setColumnWidth(self.proxy_address, 100)
        self.tableView.setColumnWidth(self.proxy_port, 40)
        self.tableView.setColumnWidth(self.proxy_type, 60)
        self.tableView.setColumnWidth(self.proxy_user, 60)
        self.tableView.setColumnWidth(self.proxy_pass, 60)
#        for cnt in range(self.tableView.model().rowCount()):
            # verticalHeader().resizeSection(cnt, 22)
#            self.tableView.header().resizeSection(cnt, 22)
        # print(self.tableView.rootIndex().row(),
            # self.tableView.rootIndex().column())
        self.tableView.setItemDelegateForColumn(self.proxy_type,
            ProxyTypeDelegate(self))
        self.tableView.setItemDelegateForColumn(self.proxy_port,
            ProxyPortDelegate(self))
        self.tableView.setItemDelegateForColumn(self.proxy_name,
            ProxyNameDelegate(self, self.validator))
        # self.tableView.setModel(self.proxyModel)

        # self.old_values = []
        # for i in range(self.data_model.rowCount()):
            # self.old_values.append(
                # self.data_model.item(i, self.proxy_name).text())

        # self.connect(self.data_model,
            # QtCore.SIGNAL('itemChanged(QStandardItem *)'),
            # self.change_item)

        self.tableView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.m_addAction = QtGui.QAction(self.tr('Add'), self.tableView)
        self.m_modAction = QtGui.QAction(self.tr('Modify'), self.tableView)
        self.m_delAction = QtGui.QAction(self.tr('Delete'), self.tableView)
        self.m_addAction.triggered.connect(self.add_proxy)
        self.m_modAction.triggered.connect(self.mod_proxy)
        self.m_delAction.triggered.connect(self.del_proxy)
        self.connect(self.tableView,
            QtCore.SIGNAL('customContextMenuRequested(const QPoint&)'),
            self.show_context_menu)

        self.connect(self.comboBox_lang,
            QtCore.SIGNAL('currentIndexChanged(int)'),
            self.change_language)

        self.change_language(self.comboBox_lang.currentIndex())

        self.finished.connect(self.dialog_checker)
        self.buttonBox.accepted.connect(self.save_config)
        self.btn_add_proxy.clicked.connect(self.add_proxy)
        self.btn_batch.clicked.connect(self.import_proxy)
        self.btn_mod.clicked.connect(self.mod_proxy)
        self.btn_del.clicked.connect(self.del_proxy)

    # def change_item(self, item):
        # if item.column() == self.proxy_name:
            # print(item.text(), self.old_values[item.row()])

    def show_context_menu(self, pnt):
        '''显示tableView右键菜单'''
        menu = QtGui.QMenu()
        if self.tableView.indexAt(pnt).isValid():
            menu.addAction(self.m_addAction)
            menu.addAction(self.m_modAction)
            menu.addAction(self.m_delAction)
        else:
            menu.addAction(self.m_addAction)
        menu.exec_(QtGui.QCursor.pos())

    def change_language(self, idx):
        '''实时改变界面语言'''
        translator = QtCore.QTranslator(QtGui.qApp)
        translator.load(os.path.join(pps_config.PROGRAM_PATH, 'i18n',
            self.langs[idx]))
        QtGui.qApp.installTranslator(translator)
        self.retranslateUi(self)

        model = self.data_model
        model.setHeaderData(self.proxy_name, QtCore.Qt.Horizontal,
            self.tr('Name'))
        model.setHeaderData(self.proxy_address, QtCore.Qt.Horizontal,
            self.tr('Address'))
        model.setHeaderData(self.proxy_port, QtCore.Qt.Horizontal,
            self.tr('Port'))
        model.setHeaderData(self.proxy_type, QtCore.Qt.Horizontal,
            self.tr('Type'))
        model.setHeaderData(self.proxy_user, QtCore.Qt.Horizontal,
            self.tr('Username'))
        model.setHeaderData(self.proxy_pass, QtCore.Qt.Horizontal,
            self.tr('Password'))

        self.m_addAction.setText(self.tr('Add'))
        self.m_modAction.setText(self.tr('Modify'))
        self.m_delAction.setText(self.tr('Delete'))

    def add_item(self, model, proxy):
        '''添加代理项目到tableView的model'''
        model.insertRow(0)
        model.setData(model.index(0, self.proxy_name), proxy[0])
        model.setData(model.index(0, self.proxy_address), proxy[1])
        model.setData(model.index(0, self.proxy_port), proxy[2])
        model.setData(model.index(0, self.proxy_type), proxy[3])
        model.setData(model.index(0, self.proxy_user), proxy[4])
        model.setData(model.index(0, self.proxy_pass), proxy[5])

    def create_model(self, parent):
        '''创建代理项目列表的model'''
        model = QtGui.QStandardItemModel(0, 6, parent)

        model.setHeaderData(self.proxy_name, QtCore.Qt.Horizontal,
            self.tr('Name'))
        model.setHeaderData(self.proxy_address, QtCore.Qt.Horizontal,
            self.tr('Address'))
        model.setHeaderData(self.proxy_port, QtCore.Qt.Horizontal,
            self.tr('Port'))
        model.setHeaderData(self.proxy_type, QtCore.Qt.Horizontal,
            self.tr('Type'))
        model.setHeaderData(self.proxy_user, QtCore.Qt.Horizontal,
            self.tr('Username'))
        model.setHeaderData(self.proxy_pass, QtCore.Qt.Horizontal,
            self.tr('Password'))
        for proxy in pps_config.pps_load_proxylist(pps_config.PROXY_LIST):
            self.add_item(model, proxy)
        model.sort(0)
        return model

    # def setSourceModel(self, model):
        # self.proxyModel.setSourceModel(model)

    def dialog_checker(self, i):
        '''配置对话框已被关闭'''
        self.parentWidget().dialog_exsit = False

    def add_proxy(self):
        '''弹出“添加代理”对话框'''
        dialog = AddProxy_Dialog()
        dialog.le_proxy_name.setValidator(self.validator)
        dialog.exec_()
        if dialog.result() == QtGui.QDialog.Accepted:
            model = self.data_model
            proxy = [dialog.le_proxy_name.text(), dialog.le_address.text(),
            dialog.le_port.text(), dialog.comboBox_type.currentText(),
            dialog.le_username.text(), dialog.le_password.text()]
            self.add_item(model, proxy)

        # if dialog.le_username.text() == '':
            # pps_config.add_proxy([dialog.le_proxy_name.text(), '%s:%s' %
            # (dialog.le_address.text(), dialog.le_port.text())],
            # dialog.comboBox_type.currentText())
        # else:
            # pps_config.add_proxy([dialog.le_proxy_name.text(), '%s:%s' %
            # (dialog.le_address.text(), dialog.le_port.text()),
            # '%s:%s' % (dialog.le_username.text(),
            # dialog.le_password.text())], dialog.comboBox_type.currentText())

    def import_proxy(self):
        '''图形界面批量添加/修改/删除代理'''
        import_dlg = QtGui.QDialog(self)
        import_dlg.resize(400, 320)
        import_dlg.setModal(True)
        import_dlg.setWindowTitle(self.tr('Batch Add/Modify/Delete Proxy'))

        lbl_tip = QtGui.QLabel(self.tr(
        'Please use the following syntax for one proxy per line:\n\n'
        'proxy_name address:port username:password proxy_type\n\n'
        '"username" and "password" are only required when the proxy needs '
        'authorization.\n'
        '"proxy_type" can be HTTP, SOCKS4 or SOCKS5.\n\n'), import_dlg)
        lbl_tip.setWordWrap(True)
        lbl_tip.setIndent(2)

        orgin_str = codecs.open(pps_config.PROXY_LIST, 'r', 'utf-8').read()
        txt_editor = QtGui.QPlainTextEdit(orgin_str, self)

        btnbox = QtGui.QDialogButtonBox(import_dlg)
        btnbox.setStandardButtons(QtGui.QDialogButtonBox.Cancel |
            QtGui.QDialogButtonBox.Ok)
        btnbox.accepted.connect(import_dlg.accept)
        btnbox.rejected.connect(import_dlg.reject)

        layout = QtGui.QGridLayout(import_dlg)
        layout.addWidget(lbl_tip, 0, 0)
        layout.addWidget(txt_editor, 1, 0)
        layout.addWidget(btnbox, 2, 0)
        import_dlg.setLayout(layout)
        import_dlg.exec_()
        if import_dlg.result() == QtGui.QDialog.Accepted:
            with codecs.open(pps_config.PROXY_LIST, 'w', 'utf-8') as outfile:
                outfile.write(to_str(txt_editor.toPlainText()))
            self.tableView.setModel(self.create_model(self.parentWidget()))
            # self.parentWidget().refresh_menu()

    def mod_proxy(self):
        '''修改代理项目'''
        self.tableView.edit(self.tableView.currentIndex())

    def del_proxy(self):
        '''删除代理项目（仅从tableView中移除，删除操作会在点击确定按钮之后）'''
        # model = self.data_model
        # proxyname = to_str(model.data(
                # model.index(self.tableView.currentIndex().row(), 0)))
        self.data_model.removeRow(self.tableView.currentIndex().row())

        # pps_config.del_proxy([proxyname])
        # for i in self.tableView.selectedIndexes():
            # self.proxyModel.removeRow(i.row())

    def save_config(self):
        '''开始执行添加、修改、删除代理的操作，保存配置文件和代理列表文件'''
        pps_config.CONFIG['LOCAL_PORT'] = int(self.le_localport.text())

        pps_config.CONFIG['DEBUG'] = self.f_or_t.index(
            self.checkBox_debug.isChecked())
        pps_config.CONFIG['SHOW_WELCOME'] = self.f_or_t.index(
            self.checkBox_show_welcome.isChecked())
        pps_config.CONFIG['LANG'] = self.langs[
            self.comboBox_lang.currentIndex()]

        pps_config.CONFIG['CMD'] = to_str(self.comboBox_cmd.currentText())

        model = self.tableView.model()
        proxy_lst = []
        proxy_set = set()
        for item in range(model.rowCount()):
            if model.data(model.index(item, 4)) == '':
                line = '%s %s:%s ' % (
                    model.data(model.index(item, 0)),
                    model.data(model.index(item, 1)),
                    model.data(model.index(item, 2)))
            else:
                line = '%s %s:%s %s:%s ' % (
                model.data(model.index(item, 0)),
                model.data(model.index(item, 1)),
                model.data(model.index(item, 2)),
                model.data(model.index(item, 4)),
                model.data(model.index(item, 5)))
            p_type = to_str(model.data(model.index(item, 3)))
            pps_config.add_proxy(line.split(), p_type)
            proxy_lst.append(line + p_type)

            proxy_set.add(to_str(model.data(model.index(item, 0))))

        # for i in ['CFG_polipo', 'CFG_3proxy']:
            # pps_config.CONFIG[i] = list(set(pps_config.CONFIG[i]))
        to_del = set(self.parentWidget().proxy_names) - proxy_set
        try:
            to_del.remove('NoProxy')
        except KeyError:
            pass
        # to_del = set(pps_config.CONFIG['CFG_polipo'].keys()) - proxy_set
        # print(to_del)
        # sys.exit()
        pps_config.del_proxy(to_del)
        pps_config.pps_savecfg(pps_config.CONFIG)
        pps_config.pps_save_proxylist(proxy_lst, pps_config.PROXY_LIST)
        self.parentWidget().refresh_menu()


def pps_quote(string):
    '''接受一个字符串，返回加引号后的字符串'''
    return '\"%s\"' % string


def to_str(qstring):
    '''接受一个QString对象，返回相应的字符串（同时适用于Python2和3）'''
    try:
        return str(qstring)
    except UnicodeEncodeError:
        return unicode(qstring)


def main():
    '''启动主程序'''
    app = QtGui.QApplication(sys.argv)
    app.setStyle('Plastique')
    app.setStyleSheet('*{font-family: Simsun ;font-size:9pt}')
    # app.setFont(QtGui.QFont("SansSerif", 9))

    QtGui.QApplication.setQuitOnLastWindowClosed(False)
    window = Window()
    # window.show()
    window.setVisible(False)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

#vim: tabstop=4 expandtab shiftwidth=4 softtabstop=
