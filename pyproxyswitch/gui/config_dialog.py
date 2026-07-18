#!/usr/bin/env python3

"""
配置对话框模块 - 包含代理配置和应用程序设置界面

此模块包含Config_Dialog类，负责代理列表管理和应用程序配置。
"""

import logging

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel

from pyproxyswitch.config import ConfigManager
from pyproxyswitch.proxy_validation import ProxyValidator, ValidationError

# 导入UI文件
from pyproxyswitch.resources.pps_conf_ui import Ui_Dialog_Config

from .batch_import_dialog import BatchImportDialog

# 导入代理类
from .delegates import ProxyNameDelegate, ProxyPortDelegate, ProxyTypeDelegate

logger = logging.getLogger("PyProxySwitch")


class Config_Dialog(QtWidgets.QDialog, Ui_Dialog_Config):
    """PPS配置对话框"""

    def __init__(self, parent=None):
        """初始化tableView及各个按钮"""
        super().__init__(parent)
        self.setupUi(self)
        self.setFixedSize(468, 327)
        self.setWindowIcon(QtGui.QIcon(":/img/pps.png"))

        # 获取配置管理器
        self._config = ConfigManager()

        (
            self.proxy_name,
            self.proxy_address,
            self.proxy_port,
            self.proxy_type,
            self.proxy_user,
            self.proxy_pass,
        ) = range(6)
        self.langs = ["zh_CN", "en"]
        self.comboBox_lang.setCurrentIndex(self.langs.index(self._config.get("LANG")))
        self.checkBox_debug.setChecked(bool(self._config.get("DEBUG")))
        self.checkBox_show_welcome.setChecked(bool(self._config.get("SHOW_WELCOME")))

        self.le_localport.setValidator(QtGui.QIntValidator(1, 65535, self))
        self.le_localport.setText(str(self._config.get("LOCAL_PORT")))

        # 使用增强的验证器
        self.validator = ProxyValidator(self)

        self.tableView.setAlternatingRowColors(True)
        self.tableView.setSortingEnabled(True)
        # 启用双击编辑
        self.tableView.setEditTriggers(
            QtWidgets.QTableView.DoubleClicked | QtWidgets.QTableView.EditKeyPressed
        )
        self.tableView.setModel(self.create_model(self))
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
        self.checkBox_debug.stateChanged.connect(self.change_debug)
        self.checkBox_show_welcome.stateChanged.connect(self.change_show_welcome)
        self.le_localport.editingFinished.connect(self.change_localport)

    def show_context_menu(self, pnt):
        """显示右键菜单"""
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
        """显示错误消息"""
        QtWidgets.QMessageBox.critical(self, self.tr("Error"), message)

    def change_language(self, idx):
        """实时改变界面语言"""
        lang = self.langs[idx]
        old_lang = self._config.get("LANG")

        # 保存新语言设置并通知主窗口
        self._config.set("LANG", lang)
        if not self._config.save():
            self._config.set("LANG", old_lang)
            with QtCore.QSignalBlocker(self.comboBox_lang):
                self.comboBox_lang.setCurrentIndex(self.langs.index(old_lang))
            self.show_error(self.tr("Failed to save configuration"))
            return

        parent = self.parentWidget()
        if hasattr(parent, "on_language_changed"):
            parent.on_language_changed(lang)

    def changeEvent(self, event):
        """处理语言变更事件"""
        if event.type() == QtCore.QEvent.LanguageChange:
            # 重新翻译UI元素
            self.retranslateUi(self)

            # 更新数据模型的列标题
            model = self.data_model
            model.setHeaderData(self.proxy_name, Qt.Horizontal, self.tr("Name", "Config_Dialog"))
            model.setHeaderData(
                self.proxy_address, Qt.Horizontal, self.tr("Address", "Config_Dialog")
            )
            model.setHeaderData(self.proxy_port, Qt.Horizontal, self.tr("Port", "Config_Dialog"))
            model.setHeaderData(self.proxy_type, Qt.Horizontal, self.tr("Type", "Config_Dialog"))
            model.setHeaderData(
                self.proxy_user, Qt.Horizontal, self.tr("Username", "Config_Dialog")
            )
            model.setHeaderData(
                self.proxy_pass, Qt.Horizontal, self.tr("Password", "Config_Dialog")
            )

            # 清除右键菜单缓存，强制下次显示时重新创建（使用新语言）
            if hasattr(self, "_context_menu"):
                delattr(self, "_context_menu")

        # 调用父类的changeEvent处理其他事件
        super().changeEvent(event)

    def change_debug(self, state):
        """改变调试模式"""
        debug = 1 if state == 2 else 0  # Qt.Checked = 2 in signal
        old_debug = self._config.get("DEBUG")
        self._config.set("DEBUG", debug)
        if not self._config.save():
            self._config.set("DEBUG", old_debug)
            with QtCore.QSignalBlocker(self.checkBox_debug):
                self.checkBox_debug.setChecked(bool(old_debug))
            self.show_error(self.tr("Failed to save configuration"))
            return
        console_level = logging.DEBUG if debug else logging.INFO
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                handler.setLevel(console_level)

    def change_show_welcome(self, state):
        """改变显示欢迎信息设置"""
        show = 1 if state == 2 else 0  # Qt.Checked = 2 in signal
        old_show = self._config.get("SHOW_WELCOME")
        self._config.set("SHOW_WELCOME", show)
        if not self._config.save():
            self._config.set("SHOW_WELCOME", old_show)
            with QtCore.QSignalBlocker(self.checkBox_show_welcome):
                self.checkBox_show_welcome.setChecked(bool(old_show))
            self.show_error(self.tr("Failed to save configuration"))

    def change_localport(self):
        """改变本地端口"""
        try:
            port = int(self.le_localport.text())
            if 1 <= port <= 65535:
                old_port = self._config.get("LOCAL_PORT")
                self._config.set("LOCAL_PORT", port)

                # 改变监听端口必须重新绑定套接字；普通上游切换不重启。
                if old_port != port:
                    try:
                        # 先保存配置到文件
                        if not self._config.save():
                            self._config.set("LOCAL_PORT", old_port)
                            self.le_localport.setText(str(old_port))
                            self.show_error(self.tr("Failed to save configuration"))
                            return

                        parent = self.parentWidget()
                        if hasattr(parent, "proxy_manager"):
                            parent.proxy_manager.restart_listener()
                            if hasattr(parent, "set_proxy_service_available"):
                                parent.set_proxy_service_available(True)
                        logger.info(f"Native proxy listener moved to port {port}")
                    except Exception as e:
                        self._config.set("LOCAL_PORT", old_port)
                        restored = self._config.save()
                        self.le_localport.setText(str(old_port))
                        parent = self.parentWidget()
                        if hasattr(parent, "set_proxy_service_available") and hasattr(
                            parent, "proxy_manager"
                        ):
                            server = parent.proxy_manager.server
                            parent.set_proxy_service_available(
                                server is not None and server.is_running
                            )
                        logger.error(f"Failed to move native proxy listener: {e}")
                        message = str(e)
                        if not restored:
                            message += "\n" + self.tr("Failed to restore the previous configuration")
                        self.show_error(message)
            else:
                self.show_error(self.tr("Port must be between 1 and 65535"))
        except ValueError:
            self.show_error(self.tr("Port must be a valid number"))

    def add_item(self, model, proxy):
        """添加代理到模型"""
        name, address, port, ptype, user, pwd = proxy

        # 验证代理信息
        try:
            validated = self.validator.validate_full_proxy(name, address, str(port), ptype, user, pwd)
        except ValidationError:
            return False

        name, address, port, ptype, user, pwd = validated
        if self._proxy_name_exists(model, name):
            return False

        row = [
            self._create_editable_item(name),
            self._create_editable_item(address),
            self._create_editable_item(str(port)),
            self._create_editable_item(ptype),
            self._create_editable_item(user),
            self._create_editable_item(pwd),
        ]
        model.appendRow(row)
        return True

    def _create_editable_item(self, text):
        """创建可编辑的表格项"""
        text = str(text)
        item = QStandardItem(text)
        item.setEditable(True)
        item.setData(text, Qt.ItemDataRole.UserRole)
        return item

    def _proxy_name_exists(self, model, name: str, exclude_row: int | None = None) -> bool:
        for row_index in range(model.rowCount()):
            if row_index == exclude_row:
                continue
            if model.data(model.index(row_index, self.proxy_name)) == name:
                return True
        return False

    def create_model(self, parent):
        """创建数据模型"""
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
        """处理表格数据更改"""
        # 只处理编辑角色的更改
        if roles and Qt.ItemDataRole.EditRole not in roles:
            return

        row = top_left.row()
        col = top_left.column()
        new_value = self.data_model.data(top_left, Qt.ItemDataRole.EditRole)

        # 验证新值
        normalized = self._validate_cell_data(row, col, new_value)
        if normalized is None:
            # 如果验证失败，恢复原值
            self._revert_cell_change(row, col)
            return

        with QtCore.QSignalBlocker(self.data_model):
            self.data_model.setData(top_left, normalized, Qt.ItemDataRole.EditRole)
            self.data_model.setData(top_left, normalized, Qt.ItemDataRole.UserRole)

        # 保存更改
        if self.save_proxies():
            self.refresh_menu()

    def _validate_cell_data(self, row, col, value):
        """验证单元格数据"""
        try:
            value = "" if value is None else str(value)
            if col == self.proxy_name:
                normalized = self.validator.validate_proxy_name(value)
                if self._proxy_name_exists(self.data_model, normalized, exclude_row=row):
                    raise ValidationError(f"代理名称 {normalized!r} 已存在")
            elif col == self.proxy_address:
                normalized = self.validator.validate_proxy_address(value)
            elif col == self.proxy_port:
                normalized = str(self.validator.validate_proxy_port(value))
            elif col == self.proxy_type:
                normalized = self.validator.validate_proxy_type(value)
            elif col == self.proxy_user:
                normalized = self.validator.validate_username(value)
            elif col == self.proxy_pass:
                normalized = self.validator.validate_password(value)
            else:
                raise ValidationError("未知的代理字段")
            return normalized
        except ValidationError as e:
            self.show_error(str(e))
            return None

    def _revert_cell_change(self, row, col):
        """恢复单元格更改"""
        index = self.data_model.index(row, col)
        original_value = self.data_model.data(index, Qt.ItemDataRole.UserRole)
        with QtCore.QSignalBlocker(self.data_model):
            self.data_model.setData(index, original_value, Qt.ItemDataRole.EditRole)

    def show_batch_dialog(self):
        """显示批量操作对话框"""
        # 读取原始内容
        try:
            initial_content = self._config.get_proxy_list_path().read_text(encoding="utf-8")
        except Exception as e:
            initial_content = ""
            errmsg = self.tr("Failed to read proxy list file")
            logger.warning(f"{errmsg}: {e}")

        # 使用新的批量导入对话框
        dialog = BatchImportDialog(self, initial_content)

        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self._process_batch_import(dialog.get_valid_proxies())

    def _process_batch_import(self, valid_proxies):
        """处理批量导入结果"""
        if not valid_proxies:
            return

        # 转换代理数据格式以匹配配置管理器
        proxy_list = [list(proxy) for proxy in valid_proxies]

        # 更新配置管理器
        old_proxies = self._config.get_proxies()
        self._config.set_proxies(proxy_list)
        if not self._config.save_proxies():
            self._config.set_proxies(old_proxies)
            self.show_error(self.tr("Failed to save proxy list"))
            return

        # 更新界面
        self._reload_proxy_model()

        # 保存并刷新
        self.refresh_menu()

    def add_proxy(self):
        """添加代理"""
        from .add_proxy_dialog import AddProxy_Dialog

        dialog = AddProxy_Dialog(self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            proxy_data = [
                dialog.le_proxy_name.text(),
                dialog.le_address.text(),
                dialog.le_port.text(),
                dialog.comboBox_type.currentText(),
                dialog.le_username.text(),
                dialog.le_password.text(),
            ]

            if self.add_item(self.data_model, proxy_data):
                # 保存到配置文件
                if self.save_proxies():
                    self.refresh_menu()
            else:
                self.show_error(self.tr("A proxy with this name already exists"))

    def modify_proxy(self):
        """修改代理"""
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
                dialog.le_password.text(),
            ]

            # 验证并更新代理
            try:
                validated = self.validator.validate_full_proxy(*proxy_data)
                proxy_data = [str(value) for value in validated]
                if self._proxy_name_exists(
                    self.data_model, proxy_data[self.proxy_name], exclude_row=row
                ):
                    raise ValidationError(
                        f"代理名称 {proxy_data[self.proxy_name]!r} 已存在"
                    )

                # 更新模型中的数据
                with QtCore.QSignalBlocker(self.data_model):
                    for col, value in enumerate(proxy_data):
                        model_index = self.data_model.index(row, col)
                        self.data_model.setData(model_index, value, Qt.ItemDataRole.EditRole)
                        self.data_model.setData(model_index, value, Qt.ItemDataRole.UserRole)

                # 保存到配置文件
                if self.save_proxies():
                    self.refresh_menu()

            except Exception as e:
                self.show_error(str(e))

    def del_proxy(self):
        """删除代理"""
        current = self.tableView.currentIndex()
        if current.isValid():
            reply = QtWidgets.QMessageBox.question(
                self,
                self.tr("Confirm Delete"),
                self.tr("Are you sure you want to delete this proxy?"),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )

            if reply == QtWidgets.QMessageBox.Yes:
                self.data_model.removeRow(current.row())
                # 刷新菜单
                if self.save_proxies():
                    self.refresh_menu()

    def refresh_menu(self):
        """刷新托盘菜单"""
        # 立即通知主窗口刷新系统托盘菜单
        parent = self.parentWidget()
        if hasattr(parent, "refresh_menu"):
            # 重新加载代理列表并刷新菜单
            parent.proxy_list = self._config.get_proxies()
            parent.proxy_names = [i[0] for i in parent.proxy_list]
            parent.proxy_names.append("NoProxy")
            parent.refresh_menu()
            logger.info("Refreshed system tray menu with updated proxy list")
            # 如果当前代理不在列表中，切换到NoProxy
            if parent.item_text not in parent.proxy_names:
                parent.switchProxy("NoProxy")
            else:
                # 当前代理的地址、端口或认证可能已被编辑；原生监听器需要
                # 获取新的不可变 Upstream 快照。
                try:
                    parent.proxy_manager.start_proxy(parent.item_text)
                    if hasattr(parent, "set_proxy_service_available"):
                        parent.set_proxy_service_available(True)
                except Exception as exc:
                    logger.error("Failed to apply updated proxy settings: %s", exc)
                    if hasattr(parent, "set_proxy_service_available"):
                        server = parent.proxy_manager.server
                        parent.set_proxy_service_available(
                            server is not None and server.is_running
                        )
                    self.show_error(str(exc))
        else:
            logger.warning("Parent widget does not have refresh_menu method")

    def export_proxies(self):
        """导出代理"""
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

    def _reload_proxy_model(self):
        """Rebuild the table from the last successfully persisted proxy state."""

        self.data_model = self.create_model(self)
        self.tableView.setModel(self.data_model)
        self.data_model.dataChanged.connect(self.on_data_changed)
        if self.data_model.rowCount():
            self.tableView.setCurrentIndex(self.data_model.index(0, 0))

    def save_proxies(self):
        """保存代理到配置文件"""
        proxies = []
        for row in range(self.data_model.rowCount()):
            name = self.data_model.data(self.data_model.index(row, self.proxy_name))
            address = self.data_model.data(self.data_model.index(row, self.proxy_address))
            port = self.data_model.data(self.data_model.index(row, self.proxy_port))
            ptype = self.data_model.data(self.data_model.index(row, self.proxy_type))
            user = self.data_model.data(self.data_model.index(row, self.proxy_user))
            pwd = self.data_model.data(self.data_model.index(row, self.proxy_pass))

            try:
                validated = self.validator.validate_full_proxy(
                    name, address, str(port), ptype, user, pwd
                )
            except ValidationError as exc:
                self._reload_proxy_model()
                self.show_error(str(exc))
                return False
            proxies.append([str(value) for value in validated])

        old_proxies = self._config.get_proxies()
        self._config.set_proxies(proxies)
        if not self._config.save_proxies():
            self._config.set_proxies(old_proxies)
            self._reload_proxy_model()
            self.show_error(self.tr("Failed to save proxy list"))
            return False
        return True

    def done(self, r):
        """对话框完成时调用"""
        super().done(r)
