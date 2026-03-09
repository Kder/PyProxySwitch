#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2009-2026 Kder Lin
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
__copyright__ = 'Copyright 2009-2026 Kder'
__credits__ = ['Kder']

__version__ = '3.6'
__date__ = '2026-03-08'
__maintainer__ = "Kder"
__email__ = '[kderlin (#) gmail dot com]'
__url__ = 'http://www.kder.info'
__license__ = 'Apache License, Version 2.0'
__status__ = 'Beta'
__projecturl__ = 'http://pyproxyswitch.kder.info'


import sys
import os
import shlex
import subprocess
import signal
import time
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtGui import QStandardItemModel
from PyQt6.QtCore import QCoreApplication, pyqtSlot

import pps_config  # noqa: E402
LIBPATH = str(Path(pps_config.PROGRAM_PATH) / 'lib')  # noqa: F821
OSPATH = os.environ.get('PATH', '').split(os.pathsep)
if LIBPATH not in OSPATH:
    OSPATH.insert(0, LIBPATH)
    os.environ["PATH"] = os.pathsep.join(OSPATH)
#    os.execv(sys.executable, sys.argv)

sys.path.append(str(Path(pps_config.PROGRAM_PATH) / 'res'))  # noqa: F821
sys.path.append(LIBPATH)
import pps_qrc  # 初始化Qt资源  # noqa: E402, F401
from logger_config import logger  # noqa: E402
from pps_conf_ui import Ui_Dialog_Config  # noqa: E402
from add_proxy_ui import Ui_Dialog_AddProxy  # noqa: E402
from proxy_validation import ProxyValidator, ValidationError, BatchImportValidator  # noqa: E402


class Window(QtWidgets.QDialog):
    '''主程序UI'''
    def __init__(self) -> None:
        '''初始化系统托盘图标和菜单'''
        super(Window, self).__init__()
        self.cmd = pps_config.CONFIG['CMD']
        self.r_process = None  # subprocess.Popen 对象

        self.dialog_exsit = False

        translator = QtCore.QTranslator(self)
        translator.load(str(Path(pps_config.PROGRAM_PATH) / 'i18n' / (pps_config.CONFIG['LANG'] + '.qm')))
        QCoreApplication.instance().installTranslator(translator)
        # self.retranslateUi(self)

        if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            QtWidgets.QMessageBox.critical(None, self.tr('System Tray'),
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
        self.trayIcon = QtWidgets.QSystemTrayIcon(self)
        self.trayIcon.setIcon(self.icon)
        self.tray_tip = f" - PyProxySwitch({self.cmd})"
        self.trayIcon.setToolTip(self.item_text + self.tray_tip)
        self.trayIcon.show()

        # trayiconmenu的context设置成desktop是为了使其能在失去焦点后自动消失
        # 参考了 http://fantasticinblur.javaeye.com/blog/902263
        self.trayIconMenu = QtWidgets.QMenu()
        self.aboutAction = QtGui.QAction(self.tr('&About'), self,
            triggered=self.about)
        self.quitAction = QtGui.QAction(self.tr('&Exit'), self,
            triggered=self.quit)
        self.configAction = QtGui.QAction(self.tr('&Config'), self,
            triggered=self.config)
        self.createActions()

        self.trayIcon.activated.connect(self.on_activated)  # PyQt6新语法

        if pps_config.CONFIG['SHOW_WELCOME'] == 1 or \
                pps_config.CONFIG['FISRT_RUN'] == 1:
            self.showWelcome()
            self.trayIcon.messageClicked.connect(self.config)  # PyQt6新语法
            # pps_config.CONFIG['FISRT_RUN'] = 0
        # print(self.cmd, self.item, self.port)
        try:
            self.run_cmd(self.cmd, self.item, self.port)
        except ValueError as e:
            # 记录错误但不显示给用户（可能暴露系统信息）
            logger.error(f"Command execution error: {e}")
            # 可以在这里添加日志记录或显示用户友好的错误信息
            #QtWidgets.QMessageBox.warning(
            #    self,
            #    self.tr('Error'),
            #    self.tr('Failed to start proxy service')
            #)

    def refresh_menu(self) -> None:
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

    def on_activated(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason) -> None:
        '''双击系统托盘图标，弹出设置对话框'''
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick:
            self.config()
        # elif reason == QtWidgets.QSystemTrayIcon.Context:
            # self.refresh_menu()
        # if reason == QtWidgets.QSystemTrayIcon.Trigger:
            # pass

    def createActions(self) -> None:
        '''生成托盘菜单'''
        self.ppsActionGroup = QtGui.QActionGroup(self)  # 使多个代理间互斥
        self.ppsActionList = []

        for i in self.proxy_names:
            act = QtGui.QAction(i, self)
            act.setCheckable(True)
            if i == self.item_text:
                act.setChecked(True)
            else:
                act.setChecked(False)
            self.ppsActionList.append(act)
        for i in self.ppsActionList:
            i.triggered.connect(self.switchProxy)  # PyQt6新语法
            self.ppsActionGroup.addAction(i)

        self.trayIconMenu.clear()
        self.trayIconMenu.addAction(self.aboutAction)
        self.trayIconMenu.addAction(self.quitAction)
        self.trayIconMenu.addAction(self.configAction)
        self.trayIconMenu.addSeparator()
        self.trayIconMenu.addActions(self.ppsActionList)

        self.trayIcon.setContextMenu(self.trayIconMenu)

    @pyqtSlot()
    def config(self) -> None:
        '''弹出配置对话框'''
        if not self.dialog_exsit:
            self.config_dialog = Config_Dialog(self)
            self.config_dialog.exec()

        else:
            self.config_dialog.activateWindow()
            self.config_dialog.setFocus()

    def quit(self) -> None:
        '''保存配置，结束代理进程，退出主程序'''
        self.trayIcon.setVisible(False)
        pps_config.CONFIG['LAST_ITEM'] = self.item_text
        pps_config.pps_savecfg(pps_config.CONFIG)

        # 使用 subprocess 终止进程
        if self.r_process is not None:
            try:
                if os.name == 'nt':
                    # Windows 上使用 terminate
                    self.r_process.terminate()
                    self.r_process.wait(timeout=5)  # 等待最多5秒
                else:
                    # Unix-like 系统上，使用 terminate 并发送信号到整个进程组
                    os.killpg(os.getpgid(self.r_process.pid), signal.SIGTERM)
                    self.r_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # 如果进程没有在5秒内终止，强制杀死
                if os.name == 'nt':
                    self.r_process.kill()
                else:
                    os.killpg(os.getpgid(self.r_process.pid), signal.SIGKILL)
                self.r_process.wait()
            except Exception as e:
                logger.error(f"Error terminating process: {e}")

        QCoreApplication.instance().quit()

    @pyqtSlot()
    def about(self):
        '''”关于”对话框'''
        msg_about = f'''PyProxySwitch &nbsp;&nbsp;&nbsp;&nbsp; {self.tr('Version: ')}{__version__}<br/><br/>
        {self.tr('''
PyProxySwitch is a cross-platform proxy switcher based on 3proxy, polipo and
IP Relay to fast change proxy for browsers(Firefox,Chrome,Opera,IE, etc.) and
other internet applications, writen in Python and PyQt.

Welcom to send me your feedback if you feel it useful.
''')}
        <br/><br/>by {__author__} {__email__}<br/><br/>{self.tr('\nAuthor website: ')}
        <a href="{__url__}">{__url__}</a><br/>{self.tr('Project website: ')}
        <a href="{__projecturl__}">{__projecturl__}</a>'''

        message = QtWidgets.QMessageBox(self)
        message.setWindowTitle(self.tr('About'))
        message.setText(msg_about)
        message.setTextFormat(QtCore.Qt.TextFormat.RichText)
        message.setIconPixmap(QtGui.QPixmap(':/img/PyProxySwitch.png'))
        message.show()

    @pyqtSlot()
    def switchProxy(self) -> None:
        '''通过结束旧进程，开启新进程的方式，在多个代理间切换
        Switch among proxies by killing old subprocess then opening
         a new one.'''
        sender = self.sender()
        self.item_text = sender.text()

        # 先终止现有的代理进程
        if self.r_process is not None:
            try:
                if os.name == 'nt':
                    self.r_process.terminate()
                    self.r_process.wait(timeout=3)
                else:
                    os.killpg(os.getpgid(self.r_process.pid), signal.SIGTERM)
                    self.r_process.wait(timeout=3)
            except Exception:
                # 如果终止失败，强制杀死
                if os.name == 'nt':
                    self.r_process.kill()
                else:
                    os.killpg(os.getpgid(self.r_process.pid), signal.SIGKILL)
                self.r_process.wait()

        for i in self.proxy_names:
            if i == self.item_text:
                self.item = i
                # self.item = self.cfg[i][0]
                if self.cmd == 'ip_relay':
                    i_index = self.proxy_names.index(i)
                    self.item = self.proxy_list[i_index][1]
                    self.port = self.proxy_list[i_index][2]
                self.trayIcon.setToolTip(i + self.tray_tip)
        time.sleep(0.1)
        try:
            self.run_cmd(self.cmd, self.item, self.port)
        except ValueError as e:
            # 记录错误但不显示给用户（可能暴露系统信息）
            logger.error(f"Command execution error: {e}")
            # 可以在这里添加日志记录或显示用户友好的错误信息
            #QtWidgets.QMessageBox.warning(
            #    self,
            #    self.tr('Error'),
            #    self.tr('Failed to start proxy service')
            #)

    def run_cmd(self, cmd, item, port):
        '''开启代理进程'''
        # 验证参数
        if not isinstance(cmd, str) or not isinstance(item, str) or port is None:
            raise ValueError("Invalid command parameters")

        # 验证端口
        if cmd == 'ip_relay':
            try:
                port_int = int(port)
                if port_int < 1 or port_int > 65535:
                    raise ValueError("Invalid port number "+str(port))
            except (ValueError, TypeError):
                raise ValueError("Invalid port number "+str(port))

        # 验证代理名称，只允许字母、数字、中文、下划线、连字符
        import re
        #if not re.match(r'^[a-zA-Z0-9\u4e00-\u9fa5_\-]{1,50}$', item):
        #    raise ValueError("Invalid proxy name: "+item)

        # 构建命令二进制路径
        if os.name == 'nt':
            cmd_bin = Path(pps_config.PROGRAM_PATH) / 'bin' / self.cmd / (self.cmd + '.exe')
        else:
            cmd_bin = Path(pps_config.PROGRAM_PATH) / 'bin' / self.cmd / self.cmd

        # 使用 shlex.quote 进行最安全的参数引用
        cmd_bin = shlex.quote(str(cmd_bin))

        cmd_option = '-c'

        # 构建配置文件路径
        # 验证文件名，防止路径遍历
        safe_filename = re.sub(r'[^\w\-\.]', '_', item)
        conf_path = Path(pps_config.PROGRAM_PATH) / 'cfg' / cmd / (safe_filename + '.conf')
        cmd_args = shlex.quote(str(conf_path))

        # 3proxy 和 ip_relay 的特殊处理
        if cmd == '3proxy':
            cmd_option = ''
        elif cmd == 'ip_relay':
            cmd_option = ''
            # 使用 shlex.quote 安全地拼接 ip_relay 的所有参数
            cmd_args = ' '.join([
                shlex.quote(str(pps_config.CONFIG['LOCAL_PORT'])),
                shlex.quote(item),
                str(port_int)  # 端口已经是数字，且由系统执行，不需要引号
            ])

        # 最终命令拼接 - 不再需要额外的 pps_quote，因为 shlex.quote 已经处理
        cmd = f'{cmd_bin} {cmd_option} {cmd_args}'
        # print(cmd)  # 调试时可以取消注释

        # 使用 subprocess.Popen 替代 QProcess
        try:
            # 将命令分割为参数列表
            cmd_parts = []

            # cmd_bin 已经被 shlex.quote 过，可以直接使用
            # 如果 cmd_bin 包含空格，需要先解析
            cmd_bin_parts = shlex.split(cmd_bin)
            cmd_parts.extend(cmd_bin_parts)

            # 添加选项和参数
            if cmd_option:
                cmd_parts.append(cmd_option)
            if cmd_args:
                # 如果 cmd_args 是带引号的字符串，需要解析
                cmd_args_parts = shlex.split(cmd_args)
                cmd_parts.extend(cmd_args_parts)

            # 如果开启了调试模式，打印命令
            if pps_config.CONFIG.get('DEBUG', 0) == 1:
                logger.info(f"Executing command: {' '.join(cmd_parts)}")

            # 在 Windows 和 Unix-like 系统上使用不同的启动方式
            if os.name == 'nt':
                # Windows 上 Popen 接受列表
                self.r_process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    shell=False
                )
            else:
                # Unix-like 系统
                self.r_process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid  # 创建新的会话组，便于终止整个进程树
                )

            # 检查进程是否成功启动
            if self.r_process.poll() is not None:
                # 如果进程已经退出，读取错误输出
                stderr_output = self.r_process.stderr.read().decode('utf-8', errors='ignore')
                raise RuntimeError(f"Process exited immediately. Error: {stderr_output}")

            # 等待进程启动
            # subprocess.Popen 立即返回，所以我们需要短暂等待
            import time
            time.sleep(0.1)

        except Exception as e:
            logger.error(f"Failed to start process: {e}")
            # 在调试模式下，打印更多信息
            if pps_config.CONFIG.get('DEBUG', 0) == 1:
                import traceback
                traceback.print_exc()
            raise

    def is_process_running(self) -> bool:
        """检查代理进程是否正在运行"""
        return self.r_process is not None and self.r_process.poll() is None

    def get_process_info(self) -> str:
        """获取进程信息"""
        if self.r_process is None:
            return "No process"

        if self.r_process.poll() is None:
            return f"Running (PID: {self.r_process.pid})"
        else:
            # 进程已退出，获取退出码
            return f"Exited with code: {self.r_process.returncode}"

    @pyqtSlot()
    def showWelcome(self) -> None:
        '''在系统托盘显示欢迎信息'''
        icon = QtWidgets.QSystemTrayIcon.MessageIcon.Information
        self.trayIcon.showMessage('Hi',
        self.tr('I\'m here, welcome to PyProxySwitch!'), icon, 5 * 1000)


class AddProxy_Dialog(QtWidgets.QDialog, Ui_Dialog_AddProxy):
    '''”添加代理”对话框'''
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
        # 传统信号槽连接语法已更新为PyQt6新语法
        # self.connect(self.btn_ok, QtCore.SIGNAL("clicked()"),
            # self.validate_proxy
        # )

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
                    self.tr('验证错误'),
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


class ProxyTypeDelegate(QtWidgets.QStyledItemDelegate):
    '''tableView的combobox代理，用于设置代理类型'''
    def createEditor(self, parent, option, index):
        '''创建QComboBox'''
        editor = QtWidgets.QComboBox(parent)
        editor.addItem('HTTP')
        editor.addItem('SOCKS4')
        editor.addItem('SOCKS5')

        return editor

    def setEditorData(self, comboBox, index):
        '''设置当前选择框的值'''
        value = index.model().data(index, QtCore.Qt.ItemDataRole.EditRole)
        comboBox.setCurrentIndex(comboBox.findText(value))
        # comboBox.setItemText(0, value)

    def setModelData(self, comboBox, model, index):
        '''设置对应的model的data'''
        value = comboBox.currentText()
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
        self.validator = validator

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


class Config_Dialog(QtWidgets.QDialog, Ui_Dialog_Config):
    '''PPS配置对话框'''
    def __init__(self, parent=None):
        '''初始化tableView及各个按钮'''
        super().__init__(parent)
        self.setupUi(self)
        self.setFixedSize(468, 327)
        self.setWindowIcon(QtGui.QIcon(':/img/pps.png'))
        self.parentWidget().dialog_exsit = True

        (self.proxy_name, self.proxy_address, self.proxy_port, self.proxy_type,
            self.proxy_user, self.proxy_pass) = range(6)
        self.langs = ['zh_CN', 'en']
        self.f_or_t = [False, True]
        self.cmds = ['3proxy', 'polipo', 'ip_relay']

        self.comboBox_lang.setCurrentIndex(
            self.langs.index(pps_config.CONFIG['LANG']))
        self.checkBox_debug.setChecked(self.f_or_t[pps_config.CONFIG['DEBUG']])
        self.checkBox_show_welcome.setChecked(
            self.f_or_t[pps_config.CONFIG['SHOW_WELCOME']])
        self.comboBox_cmd.setCurrentIndex(
            self.cmds.index(pps_config.CONFIG['CMD']))

        self.le_localport.setValidator(QtGui.QIntValidator(0, 65535, self))
        self.le_localport.setText(str(pps_config.CONFIG['LOCAL_PORT']))

        # 使用增强的验证器
        # 使用增强的验证器
        self.validator = ProxyValidator(self)
        self.validator.validation_error.connect(self.show_error)

        # 为批量导入准备验证器
        self.batch_validator = BatchImportValidator()

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

        # 传统信号槽连接语法已更新为PyQt6新语法
        # self.connect(self.data_model,
            # QtCore.SIGNAL('itemChanged(QStandardItem *)'),
            # self.change_item)

        self.tableView.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.m_addAction = QtGui.QAction(self.tr('Add'), self.tableView)
        self.m_modAction = QtGui.QAction(self.tr('Modify'), self.tableView)
        self.m_delAction = QtGui.QAction(self.tr('Delete'), self.tableView)
        self.m_addAction.triggered.connect(self.add_proxy)  # PyQt6新语法
        self.m_modAction.triggered.connect(self.mod_proxy)  # PyQt6新语法
        self.m_delAction.triggered.connect(self.del_proxy)  # PyQt6新语法
        self.tableView.customContextMenuRequested.connect(self.show_context_menu)  # PyQt6新语法

        self.comboBox_lang.currentIndexChanged.connect(self.change_language)  # PyQt6新语法

        self.change_language(self.comboBox_lang.currentIndex())

        self.finished.connect(self.dialog_checker)  # PyQt6新语法
        self.buttonBox.accepted.connect(self.save_config)  # PyQt6新语法
        self.btn_add_proxy.clicked.connect(self.add_proxy)  # PyQt6新语法
        self.btn_batch.clicked.connect(self.import_proxy)  # PyQt6新语法
        self.btn_mod.clicked.connect(self.mod_proxy)  # PyQt6新语法
        self.btn_del.clicked.connect(self.del_proxy)  # PyQt6新语法

    # def change_item(self, item):
        # if item.column() == self.proxy_name:
            # print(item.text(), self.old_values[item.row()])

    @pyqtSlot(QtCore.QPoint)
    def show_context_menu(self, pnt):
        '''显示tableView右键菜单'''
        menu = QtWidgets.QMenu()
        if self.tableView.indexAt(pnt).isValid():
            menu.addAction(self.m_addAction)
            menu.addAction(self.m_modAction)
            menu.addAction(self.m_delAction)
        else:
            menu.addAction(self.m_addAction)
        menu.exec(QtGui.QCursor.pos())

    def show_error(self, message: str):
        '''显示验证错误信息'''
        QtWidgets.QMessageBox.warning(
            self,
            self.tr('验证错误'),
            message,
            QtWidgets.QMessageBox.StandardButton.Ok
        )

    @pyqtSlot(int)
    def change_language(self, idx):
        '''实时改变界面语言'''
        translator = QtCore.QTranslator(QCoreApplication.instance())
        translator.load(str(Path(pps_config.PROGRAM_PATH) / 'i18n' / (self.langs[idx] + '.qm')))
        QCoreApplication.instance().installTranslator(translator)
        self.retranslateUi(self)

        model = self.data_model
        model.setHeaderData(self.proxy_name, QtCore.Qt.Orientation.Horizontal,
            self.tr('Name', 'Config_Dialog'))
        model.setHeaderData(self.proxy_address, QtCore.Qt.Orientation.Horizontal,
            self.tr('Address', 'Config_Dialog'))
        model.setHeaderData(self.proxy_port, QtCore.Qt.Orientation.Horizontal,
            self.tr('Port', 'Config_Dialog'))
        model.setHeaderData(self.proxy_type, QtCore.Qt.Orientation.Horizontal,
            self.tr('Type', 'Config_Dialog'))
        model.setHeaderData(self.proxy_user, QtCore.Qt.Orientation.Horizontal,
            self.tr('Username', 'Config_Dialog'))
        model.setHeaderData(self.proxy_pass, QtCore.Qt.Orientation.Horizontal,
            self.tr('Password', 'Config_Dialog'))

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
        model = QStandardItemModel(0, 6, parent)

        model.setHeaderData(self.proxy_name, QtCore.Qt.Orientation.Horizontal,
            self.tr('Name', 'Config_Dialog'))
        model.setHeaderData(self.proxy_address, QtCore.Qt.Orientation.Horizontal,
            self.tr('Address', 'Config_Dialog'))
        model.setHeaderData(self.proxy_port, QtCore.Qt.Orientation.Horizontal,
            self.tr('Port', 'Config_Dialog'))
        model.setHeaderData(self.proxy_type, QtCore.Qt.Orientation.Horizontal,
            self.tr('Type', 'Config_Dialog'))
        model.setHeaderData(self.proxy_user, QtCore.Qt.Orientation.Horizontal,
            self.tr('Username', 'Config_Dialog'))
        model.setHeaderData(self.proxy_pass, QtCore.Qt.Orientation.Horizontal,
            self.tr('Password', 'Config_Dialog'))
        for proxy in pps_config.pps_load_proxylist(pps_config.PROXY_LIST):
            self.add_item(model, proxy)
        model.sort(0)
        return model

    # def setSourceModel(self, model):
        # self.proxyModel.setSourceModel(model)

    @pyqtSlot(int)
    def dialog_checker(self, i):
        '''配置对话框已被关闭'''
        self.parentWidget().dialog_exsit = False

    @pyqtSlot()
    def add_proxy(self):
        '''弹出”添加代理”对话框'''
        dialog = AddProxy_Dialog()
        dialog.le_proxy_name.setValidator(self.validator.get_name_validator())
        dialog.exec()
        if dialog.result() == QtWidgets.QDialog.DialogCode.Accepted:
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

    @pyqtSlot()
    def import_proxy(self):
        '''图形界面批量添加/修改/删除代理'''
        import_dlg = QtWidgets.QDialog(self)
        import_dlg.resize(600, 400)
        import_dlg.setModal(True)
        import_dlg.setWindowTitle(self.tr('Batch Add/Modify/Delete Proxy'))

        # 创建提示信息
        # 使用与翻译文件中相同的字符串
        lbl_text = self.tr(
        'Please use the following syntax for one proxy per line:\n\n'
        'proxy_name address:port username:password proxy_type\n\n'
        '"username" and "password" are only required when the proxy needs '
        'authorization.\n'
        '"proxy_type" can be HTTP, SOCKS4 or SOCKS5.\n\n'
        )
        # 添加示例代码（不需要翻译）
        lbl_text += (
        'Example:\n'
        'my_proxy 192.168.1.100:8080\n'
        'auth_proxy 10.0.0.1:3120 user:pass HTTP\n'
        'socks_proxy 203.0.113.5:1080 SOCKS5\n\n'
        )
        
        lbl_tip = QtWidgets.QLabel(lbl_text, import_dlg)
        lbl_tip.setWordWrap(True)
        lbl_tip.setIndent(2)

        # 创建错误信息显示区域
        lbl_error = QtWidgets.QLabel(import_dlg)
        lbl_error.setStyleSheet("color: red;")
        lbl_error.setWordWrap(True)
        lbl_error.hide()

        # 读取原始内容
        try:
            with open(pps_config.PROXY_LIST, 'r', encoding='utf-8') as f:
                orgin_str = f.read()
        except Exception as e:
            orgin_str = ""
            error_msg = self.tr('Failed to read proxy list file:') + ' ' + str(e)
            lbl_error.setText(error_msg)
            lbl_error.show()

        txt_editor = QtWidgets.QPlainTextEdit(orgin_str, self)

        # 添加预览按钮
        btn_preview = QtWidgets.QPushButton(self.tr('Preview'))
        btn_preview.clicked.connect(lambda: self.preview_import(txt_editor.toPlainText(), lbl_error))

        btnbox = QtWidgets.QDialogButtonBox(import_dlg)
        btnbox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel |
            QtWidgets.QDialogButtonBox.StandardButton.Ok)
        btnbox.accepted.connect(lambda: self.confirm_import(txt_editor.toPlainText(), import_dlg))
        btnbox.rejected.connect(import_dlg.reject)

        layout = QtWidgets.QGridLayout(import_dlg)
        layout.addWidget(lbl_tip, 0, 0, 1, 2)
        layout.addWidget(txt_editor, 1, 0, 1, 2)
        layout.addWidget(lbl_error, 2, 0, 1, 2)
        layout.addWidget(btn_preview, 3, 0)
        layout.addWidget(btnbox, 3, 1)
        import_dlg.setLayout(layout)
        import_dlg.exec()

    def preview_import(self, content: str, error_label: QtWidgets.QLabel):
        """预览批量导入的代理配置"""
        error_label.hide()

        try:
            # 验证批量内容
            valid_proxies = self.batch_validator.validate_batch_content(content)

            # 显示预览信息
            preview_text = self.tr('Valid proxies found:')
            preview_text += '\n\n'
            for i, proxy in enumerate(valid_proxies[:10], 1):  # 最多显示10个
                preview_text += f'{i}. {proxy[0]} - {proxy[1]}:{proxy[2]} ({proxy[3]})\n'

            if len(valid_proxies) > 10:
                preview_text += '\n... and ' + str(len(valid_proxies) - 10) + ' ' + self.tr('more')

            QtWidgets.QMessageBox.information(
                self,
                self.tr('Import Preview'),
                preview_text,
                QtWidgets.QMessageBox.StandardButton.Ok
            )

        except ValidationError as e:
            error_label.setText(str(e))
            error_label.show()

    def confirm_import(self, content: str, dialog: QtWidgets.QDialog):
        """确认导入代理配置"""
        try:
            # 验证并获取有效的代理
            valid_proxies = self.batch_validator.validate_batch_content(content)

            if not valid_proxies:
                QtWidgets.QMessageBox.warning(
                    self,
                    self.tr('Import Failed'),
                    self.tr('No valid proxies found.'),
                    QtWidgets.QMessageBox.StandardButton.Ok
                )
                return

            # 保存到文件
            with open(pps_config.PROXY_LIST, 'w', encoding='utf-8') as outfile:
                for proxy in valid_proxies:
                    # 格式: name address:port type username password
                    if proxy[4] and proxy[5]:  # 有用户名和密码
                        line = f'{proxy[0]} {proxy[1]}:{proxy[2]} {proxy[4]}:{proxy[5]} {proxy[3]}\n'
                    elif proxy[3] != 'HTTP':  # 特殊类型
                        line = f'{proxy[0]} {proxy[1]}:{proxy[2]} {proxy[3]}\n'
                    else:  # 普通HTTP
                        line = f'{proxy[0]} {proxy[1]}:{proxy[2]}\n'
                    outfile.write(line)

            # 更新界面
            self.tableView.setModel(self.create_model(self.parentWidget()))
            dialog.accept()

            # 刷新菜单
            self.parentWidget().refresh_menu()

        except ValidationError as e:
            QtWidgets.QMessageBox.warning(
                self,
                self.tr('Import Failed'),
                str(e),
                QtWidgets.QMessageBox.StandardButton.Ok
            )

    @pyqtSlot()
    def mod_proxy(self):
        '''修改代理项目'''
        self.tableView.edit(self.tableView.currentIndex())

    @pyqtSlot()
    def del_proxy(self):
        '''删除代理项目（仅从tableView中移除，删除操作会在点击确定按钮之后）'''
        # model = self.data_model
        # proxyname = to_str(model.data(
                # model.index(self.tableView.currentIndex().row(), 0)))
        self.data_model.removeRow(self.tableView.currentIndex().row())

        # pps_config.del_proxy([proxyname])
        # for i in self.tableView.selectedIndexes():
            # self.proxyModel.removeRow(i.row())

    @pyqtSlot()
    def save_config(self):
        '''开始执行添加、修改、删除代理的操作，保存配置文件和代理列表文件'''
        pps_config.CONFIG['LOCAL_PORT'] = int(self.le_localport.text())

        pps_config.CONFIG['DEBUG'] = self.f_or_t.index(
            self.checkBox_debug.isChecked())
        pps_config.CONFIG['SHOW_WELCOME'] = self.f_or_t.index(
            self.checkBox_show_welcome.isChecked())
        pps_config.CONFIG['LANG'] = self.langs[
            self.comboBox_lang.currentIndex()]

        pps_config.CONFIG['CMD'] = self.comboBox_cmd.currentText()

        model = self.tableView.model()
        proxy_lst = []
        proxy_set = set()

        # 获取验证器
        validator = ProxyValidator()

        for item in range(model.rowCount()):
            try:
                name = model.data(model.index(item, 0))
                address = model.data(model.index(item, 1))
                port = model.data(model.index(item, 2))
                p_type = model.data(model.index(item, 3))
                username = model.data(model.index(item, 4))
                password = model.data(model.index(item, 5))

                # 使用验证器验证每一行
                validated_proxy = validator.validate_full_proxy(
                    name, address, port, p_type, username, password
                )

                # 格式化保存
                if username and password:
                    line = f'{validated_proxy[0]} {validated_proxy[1]}:{validated_proxy[2]} {username}:{password} {validated_proxy[3]}'
                else:
                    line = f'{validated_proxy[0]} {validated_proxy[1]}:{validated_proxy[2]} {validated_proxy[3]}'

                pps_config.add_proxy(shlex.split(line), validated_proxy[3])
                proxy_lst.append(line)
                proxy_set.add(validated_proxy[0])

            except ValidationError as e:
                # 显示警告但不中断整个保存过程
                error_msg = self.tr('Proxy configuration error, skipped:') + '\n' + str(e)
                QtWidgets.QMessageBox.warning(
                    self,
                    self.tr('Configuration Save Warning'),
                    error_msg,
                    QtWidgets.QMessageBox.StandardButton.Ok
                )
                continue

        # for i in ['CFG_polipo', 'CFG_3proxy']:
            # pps_config.CONFIG[i] = list(set(pps_config.CONFIG[i]))
        to_del = set(self.parentWidget().proxy_names) - proxy_set
        try:
            to_del.remove('NoProxy')
        except KeyError:
            logger.error("NoProxy not found in proxy set, skipping removal from deletion list.")
        # to_del = set(pps_config.CONFIG['CFG_polipo'].keys()) - proxy_set
        # print(to_del)
        # sys.exit()
        pps_config.del_proxy(to_del)
        pps_config.pps_savecfg(pps_config.CONFIG)
        pps_config.pps_save_proxylist(proxy_lst, pps_config.PROXY_LIST)
        self.parentWidget().refresh_menu()


def pps_quote(string):
    '''接受一个字符串，返回安全加引号后的字符串'''
    # 转义字符串中的双引号
    escaped = string.replace('"', '\\"')
    # 转义字符串中的反斜杠
    escaped = escaped.replace('\\', '\\\\')
    return f'"{escaped}"'




def main():
    '''启动主程序'''
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Plastique')
    app.setStyleSheet('*{font-family: Simsun ;font-size:9pt}')
    # app.setFont(QtGui.QFont("SansSerif", 9))

    QtWidgets.QApplication.setQuitOnLastWindowClosed(False)
    window = Window()
    # window.show()
    window.setVisible(False)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

#vim: tabstop=4 expandtab shiftwidth=4 softtabstop=
