#!/usr/bin/env python3

"""
主窗口模块 - 包含系统托盘界面和主窗口逻辑

此模块包含Window类，负责系统托盘图标、菜单和主窗口逻辑。
"""

import sys
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QLibraryInfo, Slot

import pyproxyswitch.pps_config as pps_config
from pyproxyswitch.config import ConfigManager
from pyproxyswitch.logger_config import get_logger
from pyproxyswitch.proxy_manager import ProxyManager


class Window(QtWidgets.QDialog):
    '''主程序UI'''
    def __init__(self) -> None:
        '''初始化系统托盘图标和菜单'''
        super().__init__()

        # 初始化配置管理器（单例模式）
        self._config = ConfigManager()

        # 初始化代理管理器
        self.proxy_manager = ProxyManager(self._config)

        self.cmd = self._config.get('CMD')

        self.trayIcon = None  # 初始化托盘图标引用

        # 初始化翻译器
        self.translator = QtCore.QTranslator(self)
        self.translator_qt = QtCore.QTranslator(self)
        self._load_translator()
        get_logger().debug(f"Config file path: {self._config.get_config_path()}")
        get_logger().debug(f"Proxy list file path: {self._config.get_proxy_list_path()}")

    def _load_translator(self) -> None:
        """加载并安装翻译器"""
        lang = self._config.get('LANG', 'zh_CN')
        stdtranslator_path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
        translator_path = str(Path(pps_config.PROGRAM_PATH) / 'i18n' / (lang + '.qm'))
        get_logger().debug(f"Main Window - loading translator from: {translator_path}")
        # 加载新翻译器
        if not self.translator_qt.load(QtCore.QLocale(lang), "qtbase", "_", stdtranslator_path):
            get_logger().warning(f"QT base translator failed to load from: {stdtranslator_path}. "
                           f"Standard buttons may not be translated.")
        else:
            get_logger().debug("QT translator loaded.")
        if not self.translator.load(translator_path):
            get_logger().warning(f"Translator failed to load from: {translator_path}. "
                f"UI may not be translated.")
        else:
            get_logger().debug("Translator loaded.")
        # 确保只有一个翻译器被安装
        app = QtCore.QCoreApplication.instance()
        if app:
            # 移除所有现有的翻译器
            for translator in app.findChildren(QtCore.QTranslator):
                app.removeTranslator(translator)

            # 安装新的翻译器
            app.installTranslator(self.translator_qt)
            app.installTranslator(self.translator)

        if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            QtWidgets.QMessageBox.critical(None, self.tr('System Tray'),
            self.tr('I\'ve not detected any system tray on this system.\n'
            'PyProxySwitch cannot start.'))
            sys.exit(1)

        self.proxy_list = self._config.get_proxies()
        self.proxy_names = [i[0] for i in self.proxy_list]

        # 根据上次退出时记录的代理项目恢复选择。
        self.item_text = self._config.get('LAST_ITEM')
        if self.item_text not in self.proxy_names and self.item_text != 'NoProxy':
            self.item_text = self._config.get('DEFAULT_ITEM')

        self.item = self.item_text
        self.port = ''
        self.proxy_names.append('NoProxy')

        self.icon = QtGui.QIcon(':/img/pps.png')
        self.setWindowIcon(self.icon)
        self.trayIcon = QtWidgets.QSystemTrayIcon(self)
        self.trayIcon.setIcon(self.icon)
        self.tray_tip = f" - PyProxySwitch({self.cmd})"
        self.trayIcon.setToolTip(self.item_text + self.tray_tip)
        self.trayIcon.show()

        self.createActions()
        self.refresh_menu()
        self.trayIcon.activated.connect(self.on_activated)

        # 如果是第一次运行，显示欢迎信息
        if self._config.get('SHOW_WELCOME', 1) == 1:
            self.showWelcome()
            self._config.set('SHOW_WELCOME', 0)

        # 启动默认代理（包括NoProxy）
        try:
            self.proxy_manager.start_proxy(self.item_text)
        except Exception as e:
            get_logger().error(f"Failed to start default proxy: {e}")

    def cleanup_tray_icon(self) -> None:
        """清理托盘图标"""
        if hasattr(self, 'trayIcon') and self.trayIcon is not None:
            try:
                self.trayIcon.hide()
                self.trayIcon.deleteLater()
            except Exception as e:
                get_logger().warning(f"Error cleaning up tray icon: {e}")
            finally:
                self.trayIcon = None

    def refresh_menu(self) -> None:
        '''刷新托盘菜单'''
        # 确保只有一个托盘菜单实例
        if not hasattr(self, 'trayIconMenu') or self.trayIconMenu is None:
            self.trayIconMenu = QtWidgets.QMenu(self)

        # 清除现有菜单项但保留菜单
        self.trayIconMenu.clear()

        # 使用代理名称列表
        proxy_actions = []
        for proxy_name in self.proxy_names:
            action = self.trayIconMenu.addAction(proxy_name)
            action.triggered.connect(lambda checked=False, name=proxy_name: self.switchProxy(name))
            # 如果这是当前选中的代理，设置为选中状态
            if proxy_name == self.item_text:
                action.setCheckable(True)
                action.setChecked(True)
            proxy_actions.append(action)

        self.trayIconMenu.addSeparator()

        # 添加其他菜单项
        self.configAction = self.trayIconMenu.addAction(self.tr("Config"))
        self.configAction.triggered.connect(self.config)

        self.aboutAction = self.trayIconMenu.addAction(self.tr("About"))
        self.aboutAction.triggered.connect(self.about)

        self.trayIconMenu.addSeparator()

        self.quitAction = self.trayIconMenu.addAction(self.tr("Quit"))
        self.quitAction.triggered.connect(self.quit)

        self.trayIcon.setContextMenu(self.trayIconMenu)

    @Slot()
    def on_activated(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason) -> None:
        '''托盘图标点击事件'''
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            # 左键点击 - 显示配置对话框
            self.config()
        elif reason == QtWidgets.QSystemTrayIcon.Context:
            # 右键点击 - 显示上下文菜单（自动处理）
            pass

    def createActions(self) -> None:
        '''创建动作 - 为了保持兼容性而保留'''
        pass

    @Slot()
    def config(self) -> None:
        '''显示配置对话框'''
        from .config_dialog import Config_Dialog

        dialog = Config_Dialog(self)
        ret = dialog.exec()

        if ret == QtWidgets.QDialog.Accepted:
            # 重新加载代理列表
            self.proxy_list = self._config.get_proxies()
            self.proxy_names = [i[0] for i in self.proxy_list]
            self.proxy_names.append('NoProxy')
            self.refresh_menu()

            # 如果当前代理不在列表中，切换到NoProxy
            if self.item_text not in self.proxy_names:
                self.switchProxy('NoProxy')
        # 注意：不再需要重置dialog_exsit标志

    @Slot()
    def about(self) -> None:
        '''显示关于对话框'''
        QtWidgets.QMessageBox.about(self, self.tr("About PyProxySwitch"),
                "<h2>PyProxySwitch 4.0.0</h2>" + \
        self.tr("<p>Copyright 2009-2026 Kder</p>"
                "<p>A cross-platform proxy switcher with a native Python HTTP/SOCKS server.</p>"
                "<p>Licensed under Apache License 2.0</p>"
                "<p>Visit <a href='http://pyproxyswitch.kder.info'>http://pyproxyswitch.kder.info</a> for more information.</p>"))

    @Slot()
    def switchProxy(self, proxy_name: str) -> None:
        '''切换代理'''
        if proxy_name != 'NoProxy' and proxy_name not in self.proxy_names:
            get_logger().error(f"Proxy {proxy_name} not found in proxy list")
            return

        try:
            self.proxy_manager.start_proxy(proxy_name)
        except Exception as e:
            get_logger().error(f"Failed to switch to {proxy_name}: {e}")
            QtWidgets.QMessageBox.critical(self, self.tr("Error"), str(e))
            return

        self._config.set('LAST_ITEM', proxy_name)
        self._config.save()
        self.item_text = proxy_name
        # 使用翻译后的文本更新托盘提示
        translated_tip = self.tr(" - PyProxySwitch({})").format(self.cmd)
        self.trayIcon.setToolTip(self.item_text + translated_tip)

        # 刷新托盘菜单以更新选中状态
        self.refresh_menu()

        # 强制处理事件以确保菜单立即更新
        QtWidgets.QApplication.processEvents()

    @Slot()
    def quit(self) -> None:
        '''退出程序'''
        # 清理托盘图标
        self.cleanup_tray_icon()

        # 停止代理进程
        self.proxy_manager.stop_proxy()

        # 退出应用程序
        QtWidgets.QApplication.quit()

    @Slot()
    def showWelcome(self) -> None:
        '''在系统托盘显示欢迎信息'''
        icon = QtWidgets.QSystemTrayIcon.MessageIcon.Information
        self.trayIcon.showMessage('Hi',
        self.tr('I\'m here, welcome to PyProxySwitch!'), icon, 5 * 1000)

    def reload_translator(self) -> None:
        """重新加载翻译器（供外部调用）"""
        self._load_translator()

    def on_language_changed(self, new_lang: str) -> None:
        """语言更改事件处理"""
        # 清理现有的托盘图标
        self.cleanup_tray_icon()

        # 保存新语言设置
        self._config.set('LANG', new_lang)
        self._config.save()

        # 重新加载翻译器
        self._load_translator()

        # 刷新菜单以立即显示新语言
        self.refresh_menu()

        # 强制处理事件以确保翻译立即生效
        QtWidgets.QApplication.processEvents()

        # 重新创建托盘图标并更新提示（使用翻译后的文本）
        if not hasattr(self, 'trayIcon') or self.trayIcon is None:
            self.trayIcon = QtWidgets.QSystemTrayIcon(self)
            self.trayIcon.setIcon(self.icon)
        translated_tip = self.tr(" - PyProxySwitch({})").format(self.cmd)
        self.trayIcon.setToolTip(self.item_text + translated_tip)
