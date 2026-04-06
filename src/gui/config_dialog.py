#!/usr/bin/env python3

"""
配置对话框模块 - 包含代理配置和应用程序设置界面

此模块包含Config_Dialog类，负责代理列表管理和应用程序配置。
"""


from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel

import src.pps_config as pps_config

# 导入UI文件
from res.pps_conf_ui import Ui_Dialog_Config
from src.config import ConfigManager
from src.logger_config import logger
from src.proxy_validation import BatchImportValidator, ProxyValidator

from .batch_import_dialog import BatchImportDialog

# 导入代理类
from .delegates import ProxyNameDelegate, ProxyPortDelegate, ProxyTypeDelegate


class Config_Dialog(QtWidgets.QDialog, Ui_Dialog_Config):
    '''PPS配置对话框'''
    def __init__(self, parent=None):
        '''初始化tableView及各个按钮'''
        super().__init__(parent)
        self.setupUi(self)
        self.setFixedSize(468, 327)
        self.setWindowIcon(QtGui.QIcon(':/img/pps.png'))
        # 注意：不再设置dialog_exsit标志，允许托盘菜单切换代理

        # 获取配置管理器
        self._config = ConfigManager()

        (self.proxy_name, self.proxy_address, self.proxy_port, self.proxy_type,
            self.proxy_user, self.proxy_pass) = range(6)
        self.langs = ['zh_CN', 'en']
        self.f_or_t = [False, True]
        self.cmds = ['3proxy', 'polipo', 'ip_relay']

        self.comboBox_lang.setCurrentIndex(
            self.langs.index(self._config.get('LANG')))
        self.checkBox_debug.setChecked(self.f_or_t[self._config.get('DEBUG')])
        self.checkBox_show_welcome.setChecked(
            self.f_or_t[self._config.get('SHOW_WELCOME')])
        self.comboBox_cmd.setCurrentIndex(
            self.cmds.index(self._config.get('CMD')))

        self.le_localport.setValidator(QtGui.QIntValidator(0, 65535, self))
        self.le_localport.setText(str(self._config.get('LOCAL_PORT')))

        # 使用增强的验证器
        self.validator = ProxyValidator(self)
        self.validator.validation_error.connect(self.show_error)

        # 为批量导入准备验证器
        self.batch_validator = BatchImportValidator()

        self.tableView.setAlternatingRowColors(True)
        self.tableView.setSortingEnabled(True)
        # 启用双击编辑
        self.tableView.setEditTriggers(QtWidgets.QTableView.DoubleClicked | QtWidgets.QTableView.EditKeyPressed)
        self.tableView.setModel(self.create_model(parent))
        self.data_model = self.tableView.model()
        self.tableView.setCurrentIndex(self.data_model.index(0, 0))

        # 连接数据更改信号
        self.data_model.dataChanged.connect(self.on_data_changed)
        self.tableView.setColumnWidth(self.proxy_name, 80)
        self.tableView.setColumnWidth(self.proxy_address, 100)
        self.tableView.setColumnWidth(self.proxy_port, 40)
        self.tableView.setColumnWidth(self.proxy_type, 60)
        self.tableView.setColumnWidth(self.proxy_user, 60)
        self.tableView.setColumnWidth(self.proxy_pass, 60)

        # 设置代理
        self.tableView.setItemDelegateForColumn(self.proxy_type, ProxyTypeDelegate(self))
        self.tableView.setItemDelegateForColumn(self.proxy_port, ProxyPortDelegate(self))
        self.tableView.setItemDelegateForColumn(self.proxy_name, ProxyNameDelegate(self))

        # 连接信号
        self.tableView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableView.customContextMenuRequested.connect(self.show_context_menu)

        # 按钮连接
        self.btn_add_proxy.clicked.connect(self.add_proxy)
        self.btn_mod.clicked.connect(self.modify_proxy)
        self.btn_del.clicked.connect(self.del_proxy)
        self.btn_batch.clicked.connect(self.show_batch_dialog)

        # 设置连接
        self.comboBox_lang.currentIndexChanged.connect(self.change_language)
        self.comboBox_cmd.currentIndexChanged.connect(self.change_cmd)
        self.checkBox_debug.stateChanged.connect(self.change_debug)
        self.checkBox_show_welcome.stateChanged.connect(self.change_show_welcome)
        self.le_localport.editingFinished.connect(self.change_localport)

    def show_context_menu(self, pnt):
        '''显示右键菜单'''
        # 每次都创建新的菜单，确保使用最新的翻译
        context_menu = QtWidgets.QMenu()

        add_action = context_menu.addAction(self.tr("Add Proxy"))
        add_action.triggered.connect(lambda: self.add_proxy())

        del_action = context_menu.addAction(self.tr("Delete Proxy"))
        del_action.triggered.connect(lambda: self.del_proxy())

        context_menu.addSeparator()

        import_action = context_menu.addAction(self.tr("Import Proxies"))
        import_action.triggered.connect(lambda: self.show_batch_dialog())

        export_action = context_menu.addAction(self.tr("Export Proxies"))
        export_action.triggered.connect(lambda: self.export_proxies())

        context_menu.exec(self.tableView.mapToGlobal(pnt))

    def show_error(self, message: str):
        '''显示错误消息'''
        QtWidgets.QMessageBox.critical(self, self.tr("Error"), message)

    def change_language(self, idx):
        '''实时改变界面语言'''
        lang = self.langs[idx]

        # 保存新语言设置并通知主窗口
        self._config.set('LANG', lang)
        self._config.save()

        parent = self.parentWidget()
        if hasattr(parent, 'on_language_changed'):
            parent.on_language_changed(lang)

    def changeEvent(self, event):
        '''处理语言变更事件'''
        if event.type() == QtCore.QEvent.LanguageChange:
            # 重新翻译UI元素
            self.retranslateUi(self)

            # 更新数据模型的列标题
            model = self.data_model
            model.setHeaderData(self.proxy_name, Qt.Horizontal,
                self.tr('Name', 'Config_Dialog'))
            model.setHeaderData(self.proxy_address, Qt.Horizontal,
                self.tr('Address', 'Config_Dialog'))
            model.setHeaderData(self.proxy_port, Qt.Horizontal,
                self.tr('Port', 'Config_Dialog'))
            model.setHeaderData(self.proxy_type, Qt.Horizontal,
                self.tr('Type', 'Config_Dialog'))
            model.setHeaderData(self.proxy_user, Qt.Horizontal,
                self.tr('Username', 'Config_Dialog'))
            model.setHeaderData(self.proxy_pass, Qt.Horizontal,
                self.tr('Password', 'Config_Dialog'))

            # 清除右键菜单缓存，强制下次显示时重新创建（使用新语言）
            if hasattr(self, '_context_menu'):
                delattr(self, '_context_menu')

        # 调用父类的changeEvent处理其他事件
        super().changeEvent(event)

    def change_cmd(self, idx):
        '''改变代理命令'''
        cmd = self.cmds[idx]
        self._config.set('CMD', cmd)
        self._config.save()

    def change_debug(self, state):
        '''改变调试模式'''
        debug = 1 if state == 2 else 0  # Qt.Checked = 2 in signal
        self._config.set('DEBUG', debug)
        self._config.save()

    def change_show_welcome(self, state):
        '''改变显示欢迎信息设置'''
        show = 1 if state == 2 else 0  # Qt.Checked = 2 in signal
        self._config.set('SHOW_WELCOME', show)
        self._config.save()

    def change_localport(self):
        '''改变本地端口'''
        try:
            port = int(self.le_localport.text())
            if 1 <= port <= 65535:
                old_port = self._config.get('LOCAL_PORT')
                self._config.set('LOCAL_PORT', port)

                # 如果端口确实改变了，更新所有配置文件
                if old_port != port:
                    try:
                        # 先保存配置到文件
                        self._config.save()

                        # 更新pps_config中的全局CONFIG
                        pps_config.update_config()

                        # 重新生成所有代理的配置文件
                        proxies = self._config.get_proxies()
                        if proxies:
                            self._generate_backend_configs(proxies)
                            logger.info(f"Updated all proxy config files with new port: {port}")
                    except Exception as e:
                        logger.error(f"Failed to update proxy config files with new port: {e}")
                        # 继续执行，不阻止用户设置端口
            else:
                self.show_error(self.tr("Port must be between 1 and 65535"))
        except ValueError:
            self.show_error(self.tr("Port must be a valid number"))

    def add_item(self, model, proxy):
        '''添加代理到模型'''
        name, address, port, ptype, user, pwd = proxy

        # 验证代理信息
        try:
            self.validator.validate_full_proxy(name, address, port, ptype, user, pwd)
        except Exception:
            return False

        row = [
            self._create_editable_item(name),
            self._create_editable_item(address),
            self._create_editable_item(port),
            self._create_editable_item(ptype),
            self._create_editable_item(user),
            self._create_editable_item(pwd)
        ]
        model.appendRow(row)
        return True

    def _create_editable_item(self, text):
        '''创建可编辑的表格项'''
        item = QStandardItem(text)
        item.setEditable(True)
        return item

    def create_model(self, parent):
        '''创建数据模型'''
        model = QStandardItemModel(0, 6, parent)
        model.setHeaderData(self.proxy_name, Qt.Horizontal, self.tr("Name"))
        model.setHeaderData(self.proxy_address, Qt.Horizontal, self.tr("Address"))
        model.setHeaderData(self.proxy_port, Qt.Horizontal, self.tr("Port"))
        model.setHeaderData(self.proxy_type, Qt.Horizontal, self.tr("Type"))
        model.setHeaderData(self.proxy_user, Qt.Horizontal, self.tr("Username"))
        model.setHeaderData(self.proxy_pass, Qt.Horizontal, self.tr("Password"))

        # 加载现有代理
        proxies = self._config.get_proxies()
        for proxy in proxies:
            # logger.info(f"Loading proxy: {proxy}")  # 调试日志
            # 确保代理数据有6个元素
            proxy_data = list(proxy)
            while len(proxy_data) < 6:
                proxy_data.append("")

            # 确保端口是字符串格式（验证器期望字符串）
            proxy_data[2] = str(proxy_data[2])

            self.add_item(model, proxy_data)

        return model

    def on_data_changed(self, top_left, bottom_right, roles):
        '''处理表格数据更改'''
        # 只处理编辑角色的更改
        if Qt.EditRole not in roles:
            return

        row = top_left.row()
        col = top_left.column()
        new_value = self.data_model.data(top_left, Qt.EditRole)

        # 验证新值
        if not self._validate_cell_data(row, col, new_value):
            # 如果验证失败，恢复原值
            self._revert_cell_change(row, col)
            return

        # 保存更改
        self.save_proxies()
        self.refresh_menu()

        # 生成后端配置文件
        proxies = self._config.get_proxies()
        self._generate_backend_configs(proxies)

    def _validate_cell_data(self, row, col, value):
        '''验证单元格数据'''
        try:
            if col == self.proxy_name:
                self.validator.validate_proxy_name(value)
            elif col == self.proxy_address:
                self.validator.validate_proxy_address(value)
            elif col == self.proxy_port:
                self.validator.validate_proxy_port(str(value))
            elif col == self.proxy_type:
                self.validator.validate_proxy_type(value)
            elif col == self.proxy_user:
                self.validator.validate_username(value)
            elif col == self.proxy_pass:
                self.validator.validate_password(value)
            return True
        except Exception as e:
            self.show_error(str(e))
            return False

    def _revert_cell_change(self, row, col):
        '''恢复单元格更改'''
        # 重新从配置加载数据
        proxies = self._config.get_proxies()
        if row < len(proxies):
            proxy = proxies[row]
            original_value = proxy[col] if col < len(proxy) else ""
            self.data_model.setData(self.data_model.index(row, col), original_value)

    def show_batch_dialog(self):
        '''显示批量操作对话框'''
        # 读取原始内容
        try:
            with open(pps_config.PROXY_LIST, encoding='utf-8') as f:
                initial_content = f.read()
        except Exception as e:
            initial_content = ""
            errmsg = self.tr("Failed to read proxy list file")
            logger.warning(f'{errmsg}: {e}')

        # 使用新的批量导入对话框
        dialog = BatchImportDialog(self, initial_content)
        dialog.import_completed.connect(
            lambda proxies: self._on_batch_import_completed(proxies, dialog)
        )

        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self._process_batch_import(dialog.get_valid_proxies())

    def _on_batch_import_completed(self, proxies, dialog):
        """批量导入完成回调"""
        self._process_batch_import(proxies)
        dialog.accept()

    def _process_batch_import(self, valid_proxies):
        """处理批量导入结果"""
        if not valid_proxies:
            return

        # 转换代理数据格式以匹配配置管理器
        proxy_list = [list(proxy) for proxy in valid_proxies]

        # 更新配置管理器
        self._config.set_proxies(proxy_list)

        # 保存到文件
        with open(pps_config.PROXY_LIST, 'w', encoding='utf-8') as outfile:
            for proxy in valid_proxies:
                if proxy[4] and proxy[5]:  # 有用户名和密码
                    line = f'{proxy[0]} {proxy[1]}:{proxy[2]} {proxy[4]}:{proxy[5]} {proxy[3]}\n'
                elif proxy[3] != 'HTTP':  # 特殊类型
                    line = f'{proxy[0]} {proxy[1]}:{proxy[2]} {proxy[3]}\n'
                else:  # 普通HTTP
                    line = f'{proxy[0]} {proxy[1]}:{proxy[2]}\n'
                outfile.write(line)

        # 更新界面
        self.data_model = self.create_model(self.parentWidget())
        self.tableView.setModel(self.data_model)

        # 保存并刷新
        self._config.save()
        self.refresh_menu()

        # 生成后端配置文件
        proxies = self._config.get_proxies()
        self._generate_backend_configs(proxies)

    def add_proxy(self):
        '''添加代理'''
        from .add_proxy_dialog import AddProxy_Dialog

        dialog = AddProxy_Dialog(self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            proxy_data = [
                dialog.le_proxy_name.text(),
                dialog.le_address.text(),
                dialog.le_port.text(),
                dialog.comboBox_type.currentText(),
                dialog.le_username.text(),
                dialog.le_password.text()
            ]

            if self.add_item(self.data_model, proxy_data):
                # 保存到配置文件
                self.save_proxies()
                self.refresh_menu()
                # 生成后端配置文件
                proxies = self._config.get_proxies()
                self._generate_backend_configs(proxies)

    def modify_proxy(self):
        '''修改代理'''
        current = self.tableView.currentIndex()
        if not current.isValid():
            self.show_error(self.tr("Please select a proxy to modify"))
            return

        from .add_proxy_dialog import AddProxy_Dialog

        # 获取当前代理数据
        row = current.row()
        name = self.data_model.data(self.data_model.index(row, self.proxy_name))
        address = self.data_model.data(self.data_model.index(row, self.proxy_address))
        port = self.data_model.data(self.data_model.index(row, self.proxy_port))
        ptype = self.data_model.data(self.data_model.index(row, self.proxy_type))
        user = self.data_model.data(self.data_model.index(row, self.proxy_user))
        pwd = self.data_model.data(self.data_model.index(row, self.proxy_pass))

        # 创建修改对话框并填入当前数据
        dialog = AddProxy_Dialog(self)
        dialog.le_proxy_name.setText(name)
        dialog.le_address.setText(address)
        dialog.le_port.setText(port)

        # 设置代理类型
        index = dialog.comboBox_type.findText(ptype)
        if index >= 0:
            dialog.comboBox_type.setCurrentIndex(index)

        dialog.le_username.setText(user)
        dialog.le_password.setText(pwd)

        if dialog.exec() == QtWidgets.QDialog.Accepted:
            proxy_data = [
                dialog.le_proxy_name.text(),
                dialog.le_address.text(),
                dialog.le_port.text(),
                dialog.comboBox_type.currentText(),
                dialog.le_username.text(),
                dialog.le_password.text()
            ]

            # 验证并更新代理
            try:
                self.validator.validate_full_proxy(*proxy_data)

                # 更新模型中的数据
                for col, value in enumerate(proxy_data):
                    self.data_model.setData(self.data_model.index(row, col), value)

                # 保存到配置文件
                self.save_proxies()
                self.refresh_menu()
                # 生成后端配置文件
                proxies = self._config.get_proxies()
                self._generate_backend_configs(proxies)

            except Exception as e:
                self.show_error(str(e))

    def del_proxy(self):
        '''删除代理'''
        current = self.tableView.currentIndex()
        if current.isValid():
            reply = QtWidgets.QMessageBox.question(self, self.tr("Confirm Delete"),
                                                  self.tr("Are you sure you want to delete this proxy?"),
                                                  QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

            if reply == QtWidgets.QMessageBox.Yes:
                self.data_model.removeRow(current.row())
                # 刷新菜单
                self.save_proxies()
                self.refresh_menu()
                # Regenerate backend configs after deletion
                proxies = self._config.get_proxies()
                self._generate_backend_configs(proxies)

    def refresh_menu(self):
        '''刷新托盘菜单'''
        # 立即通知主窗口刷新系统托盘菜单
        parent = self.parentWidget()
        if hasattr(parent, 'refresh_menu'):
            # 重新加载代理列表并刷新菜单
            parent.proxy_list = self._config.get_proxies()
            parent.proxy_names = [i[0] for i in parent.proxy_list]
            if parent.cmd != 'ip_relay':
                parent.proxy_names.append('NoProxy')
            parent.refresh_menu()
            logger.info("Refreshed system tray menu with updated proxy list")
            # 如果当前代理不在列表中，切换到NoProxy
            if parent.item_text not in parent.proxy_names:
                parent.switchProxy('NoProxy')
        else:
            logger.warning("Parent widget does not have refresh_menu method")

    def export_proxies(self):
        '''导出代理'''
        # 收集代理数据
        proxies = []
        for row in range(self.data_model.rowCount()):
            name = self.data_model.data(self.data_model.index(row, self.proxy_name))
            address = self.data_model.data(self.data_model.index(row, self.proxy_address))
            port = self.data_model.data(self.data_model.index(row, self.proxy_port))
            ptype = self.data_model.data(self.data_model.index(row, self.proxy_type))
            user = self.data_model.data(self.data_model.index(row, self.proxy_user))
            pwd = self.data_model.data(self.data_model.index(row, self.proxy_pass))
            proxies.append([name, address, port, ptype, user, pwd])

        BatchImportDialog.export_proxies_to_file(self, proxies)

    def save_proxies(self):
        '''保存代理到配置文件'''
        proxies = []
        for row in range(self.data_model.rowCount()):
            name = self.data_model.data(self.data_model.index(row, self.proxy_name))
            address = self.data_model.data(self.data_model.index(row, self.proxy_address))
            port = self.data_model.data(self.data_model.index(row, self.proxy_port))
            ptype = self.data_model.data(self.data_model.index(row, self.proxy_type))
            user = self.data_model.data(self.data_model.index(row, self.proxy_user))
            pwd = self.data_model.data(self.data_model.index(row, self.proxy_pass))

            proxy = [name, address, port, ptype, user, pwd] # IMPORTANT!
            proxies.append(proxy)

        self._config.set_proxies(proxies)
        self._config.save_proxies()


    def _generate_noproxy_configs(self, local_port):
        """生成NoProxy配置文件"""
        pps_config.generate_noproxy_configs(local_port)


    def _generate_backend_configs(self, proxies, local_port=None):
        """生成后端代理配置文件"""
        pps_config.regenerate_all_configs(proxies, local_port or self._config.get('LOCAL_PORT', 8888))


    def _cleanup_backend_configs(self):
        """清理后端配置文件"""
        pps_config.cleanup_configs()


    def done(self, r):
        '''对话框完成时调用'''
        super().done(r)
