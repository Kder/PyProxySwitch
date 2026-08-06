import json
import logging

import pytest
from PySide6 import QtCore, QtGui, QtWidgets

import pyproxyswitch.gui.main_window as main_window
import pyproxyswitch.main as application
from pyproxyswitch.config import ConfigManager
from pyproxyswitch.gui.add_proxy_dialog import AddProxy_Dialog
from pyproxyswitch.gui.batch_import_dialog import BatchImportDialog
from pyproxyswitch.gui.config_dialog import Config_Dialog
from pyproxyswitch.proxy_list import load_proxy_list


def _make_config(tmp_path, proxies=()):
    config = ConfigManager(
        config_path=tmp_path / "PPS.conf",
        proxy_list_path=tmp_path / "proxy.txt",
    )
    config.set_proxies(proxies)
    return config


def test_add_proxy_dialog_stores_normalized_values(qapp) -> None:
    dialog = AddProxy_Dialog()
    dialog.le_proxy_name.setText("  normalized  ")
    dialog.le_address.setText("[::1]")
    dialog.le_port.setText("8080")
    dialog.checkBox_proxy_auth.setChecked(True)
    dialog.le_username.setText(" alice ")
    dialog.le_password.setText(" secret ")

    dialog.done(QtWidgets.QDialog.DialogCode.Accepted)

    assert dialog.result() == QtWidgets.QDialog.DialogCode.Accepted
    assert dialog.le_proxy_name.text() == "normalized"
    assert dialog.le_address.text() == "::1"
    assert dialog.le_username.text() == "alice"
    assert dialog.le_password.text() == " secret "


def test_add_proxy_dialog_discards_credentials_when_auth_is_disabled(qapp) -> None:
    dialog = AddProxy_Dialog()
    dialog.le_proxy_name.setText("no_auth")
    dialog.le_address.setText("localhost")
    dialog.le_port.setText("8080")
    dialog.checkBox_proxy_auth.setChecked(True)
    dialog.le_username.setText("alice")
    dialog.le_password.setText("secret")
    dialog.checkBox_proxy_auth.setChecked(False)

    dialog.done(QtWidgets.QDialog.DialogCode.Accepted)

    assert dialog.result() == QtWidgets.QDialog.DialogCode.Accepted
    assert dialog.le_username.text() == ""
    assert dialog.le_password.text() == ""


def test_socks4_dialog_uses_user_id_and_hides_password(qapp) -> None:
    dialog = AddProxy_Dialog()
    dialog.checkBox_proxy_auth.setChecked(True)
    dialog.le_password.setText("must-be-cleared")

    dialog.comboBox_type.setCurrentText("SOCKS4")

    assert dialog.label_user.text() == "User ID"
    assert dialog.le_username.isVisibleTo(dialog)
    assert not dialog.label_pass.isVisibleTo(dialog)
    assert not dialog.le_password.isVisibleTo(dialog)
    assert dialog.le_password.text() == ""


def test_invalid_sorted_edit_reverts_its_own_row(qapp, tmp_path, monkeypatch) -> None:
    _make_config(
        tmp_path,
        [
            ("alpha", "alpha.example", "8001", "HTTP", "", ""),
            ("zulu", "zulu.example", "9001", "HTTP", "", ""),
        ],
    )
    dialog = Config_Dialog()
    monkeypatch.setattr(dialog, "show_error", lambda message: None)
    dialog.data_model.sort(dialog.proxy_name, QtCore.Qt.SortOrder.DescendingOrder)
    assert dialog.data_model.data(dialog.data_model.index(0, dialog.proxy_name)) == "zulu"

    port_index = dialog.data_model.index(0, dialog.proxy_port)
    dialog.data_model.setData(port_index, "invalid", QtCore.Qt.ItemDataRole.EditRole)

    assert dialog.data_model.data(port_index, QtCore.Qt.ItemDataRole.EditRole) == "9001"
    assert dialog.data_model.parent() is dialog


def test_batch_dialog_result_is_processed_once(qapp, tmp_path, monkeypatch) -> None:
    _make_config(tmp_path)
    dialog = Config_Dialog()
    calls = []

    class FakeBatchDialog:
        def __init__(self, parent, initial_content):
            pass

        def exec(self):
            return QtWidgets.QDialog.DialogCode.Accepted

        def get_valid_proxies(self):
            return [("one", "localhost", 8080, "HTTP", "", "")]

    monkeypatch.setattr("pyproxyswitch.gui.config_dialog.BatchImportDialog", FakeBatchDialog)
    monkeypatch.setattr(dialog, "_process_batch_import", lambda proxies: calls.append(proxies))

    dialog.show_batch_dialog()

    assert len(calls) == 1


def test_batch_dialog_rejects_partial_invalid_content(qapp, monkeypatch) -> None:
    dialog = BatchImportDialog(
        initial_content=(
            "valid_proxy localhost:8080\n"
            "invalid_proxy localhost:8081 user:secret SOCKS5 unexpected\n"
        )
    )
    warnings = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", lambda *args: warnings.append(args[2]))

    dialog._on_accept()

    assert dialog.result() != QtWidgets.QDialog.DialogCode.Accepted
    assert dialog.get_valid_proxies() == []
    assert warnings and "第2行" in warnings[0]


def test_tray_double_click_opens_configuration() -> None:
    calls = []

    class FakeWindow:
        def config(self):
            calls.append(True)

    main_window.Window.on_activated(
        FakeWindow(), QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick
    )

    assert calls == [True]


def test_configuration_dialog_is_reused_during_nested_activation(monkeypatch) -> None:
    events = []

    class Host:
        _config_dialog = None

        def config(self):
            return main_window.Window.config(self)

    class FakeDialog:
        def __init__(self, parent):
            self.parent = parent
            events.append("created")

        def exec(self):
            self.parent.config()
            return QtWidgets.QDialog.DialogCode.Rejected

        def show(self):
            events.append("shown")

        def raise_(self):
            events.append("raised")

        def activateWindow(self):
            events.append("activated")

        def deleteLater(self):
            events.append("deleted")

    monkeypatch.setattr("pyproxyswitch.gui.config_dialog.Config_Dialog", FakeDialog)
    host = Host()

    host.config()

    assert events == ["created", "shown", "raised", "activated", "deleted"]
    assert host._config_dialog is None


def test_export_uses_round_trip_safe_proxy_format(qapp, tmp_path, monkeypatch) -> None:
    destination = tmp_path / "exported.txt"
    parent = QtWidgets.QWidget()
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getSaveFileName",
        lambda *args: (str(destination), "Text Files (*.txt)"),
    )
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *args: None)

    exported = BatchImportDialog.export_proxies_to_file(
        parent,
        [("quoted", "localhost", "8080", "HTTP", "alice", "p a'ss\\word")],
    )

    assert exported
    assert load_proxy_list(destination) == [
        ("quoted", "localhost", "8080", "HTTP", "alice", "p a'ss\\word")
    ]


def test_failed_atomic_export_preserves_previous_file(qapp, tmp_path, monkeypatch) -> None:
    destination = tmp_path / "exported.txt"
    destination.write_text("existing\n", encoding="utf-8")
    parent = QtWidgets.QWidget()
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getSaveFileName",
        lambda *args: (str(destination), "Text Files (*.txt)"),
    )
    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", lambda *args: None)

    def fail_replace(source, target):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("pyproxyswitch.atomic_write.os.replace", fail_replace)

    exported = BatchImportDialog.export_proxies_to_file(
        parent,
        [("new", "localhost", "8080", "HTTP", "", "")],
    )

    assert not exported
    assert destination.read_text(encoding="utf-8") == "existing\n"
    assert not list(tmp_path.glob(".exported.txt.*.tmp"))


def test_refreshing_menu_reapplies_edited_active_proxy(qapp, tmp_path) -> None:
    _make_config(tmp_path, [("one", "localhost", "8080", "HTTP", "", "")])

    class ProxyManagerStub:
        def __init__(self):
            self.started = []

        def start_proxy(self, name):
            self.started.append(name)

    class Parent(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.item_text = "one"
            self.proxy_manager = ProxyManagerStub()
            self.refresh_count = 0

        def refresh_menu(self):
            self.refresh_count += 1

        def switchProxy(self, name):
            self.item_text = name

    parent = Parent()
    dialog = Config_Dialog(parent)

    dialog.refresh_menu()

    assert parent.refresh_count == 1
    assert parent.proxy_manager.started == ["one"]


def test_changing_listener_port_reapplies_the_selected_proxy(qapp, tmp_path) -> None:
    config = _make_config(
        tmp_path,
        [("one", "proxy.example", "8080", "HTTP", "", "")],
    )

    class ProxyManagerStub:
        def __init__(self):
            self.started = []
            self.restart_calls = 0

        def start_proxy(self, name):
            self.started.append(name)

        def restart_listener(self):
            self.restart_calls += 1

    class Parent(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.item_text = "one"
            self.proxy_manager = ProxyManagerStub()
            self.proxy_service_available = False

        def set_proxy_service_available(self, available):
            self.proxy_service_available = available

    parent = Parent()
    dialog = Config_Dialog(parent)
    dialog.le_localport.setText("9999")

    dialog.change_localport()

    assert config.get("LOCAL_PORT") == 9999
    assert parent.proxy_manager.started == ["one"]
    assert parent.proxy_manager.restart_calls == 0
    assert parent.proxy_service_available


@pytest.mark.parametrize("invalid_port", ["", "0", "65536", "not-a-port"])
def test_invalid_listener_port_restores_configured_value(
    qapp, tmp_path, monkeypatch, invalid_port
) -> None:
    config = _make_config(tmp_path)
    dialog = Config_Dialog()
    monkeypatch.setattr(dialog, "show_error", lambda message: None)
    dialog.le_localport.setText(invalid_port)

    dialog.change_localport()

    assert config.get("LOCAL_PORT") == 8888
    assert dialog.le_localport.text() == "8888"


def test_modifying_authenticated_proxy_enables_credential_fields(
    qapp, tmp_path, monkeypatch
) -> None:
    _make_config(
        tmp_path,
        [("auth", "proxy.example", "8080", "HTTP", "alice", "secret")],
    )
    captured = []

    class CapturingDialog(AddProxy_Dialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            captured.append(self)

        def exec(self):
            return QtWidgets.QDialog.DialogCode.Rejected

    monkeypatch.setattr(
        "pyproxyswitch.gui.add_proxy_dialog.AddProxy_Dialog",
        CapturingDialog,
    )
    dialog = Config_Dialog()
    dialog.tableView.setCurrentIndex(dialog.data_model.index(0, dialog.proxy_name))

    dialog.modify_proxy()

    editor = captured[0]
    assert editor.checkBox_proxy_auth.isChecked()
    assert editor.le_username.isEnabled()
    assert editor.le_password.isEnabled()


def test_debug_checkbox_updates_console_logging_immediately(qapp, tmp_path) -> None:
    _make_config(tmp_path)
    dialog = Config_Dialog()
    root_logger = logging.getLogger("PyProxySwitch")
    previous_handlers = root_logger.handlers[:]
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    root_logger.handlers = [console_handler]
    try:
        dialog.change_debug(2)
        assert console_handler.level == logging.DEBUG

        dialog.change_debug(0)
        assert console_handler.level == logging.INFO
    finally:
        root_logger.handlers = previous_handlers


def test_gui_entry_point_keeps_tray_app_alive(monkeypatch) -> None:
    events = []

    class FakeApplication:
        def __init__(self, args):
            pass

        def setApplicationName(self, name):
            pass

        def setApplicationVersion(self, version):
            pass

        def setQuitOnLastWindowClosed(self, enabled):
            events.append(enabled)

        def exec(self):
            return 0

    class FakeWindow:
        def on_external_activation(self):
            pass

    class FakeSignal:
        def connect(self, slot):
            pass

    class FakeInstanceGuard:
        def __init__(self, app):
            self.activated = FakeSignal()

        def try_become_primary(self):
            return True

    class FakeConfig:
        def get(self, key, default=None):
            return 0

    root_logger = logging.getLogger("PyProxySwitch")
    previous_handlers = root_logger.handlers[:]
    root_logger.handlers = [logging.NullHandler()]
    try:
        # Restore QApplication before pytest-qt processes events after the test call.
        # Leaving the fake class installed until fixture teardown breaks that hook.
        with monkeypatch.context() as scoped_monkeypatch:
            scoped_monkeypatch.setattr(QtWidgets, "QApplication", FakeApplication)
            scoped_monkeypatch.setattr(main_window, "Window", FakeWindow)
            scoped_monkeypatch.setattr(
                "pyproxyswitch.single_instance.SingleInstanceGuard", FakeInstanceGuard
            )
            scoped_monkeypatch.setattr("pyproxyswitch.config.ConfigManager", FakeConfig)
            with pytest.raises(SystemExit, match="0"):
                application.main()
    finally:
        root_logger.handlers = previous_handlers

    assert events == [False]


def test_second_launch_exits_after_activating_primary(monkeypatch, capsys) -> None:
    class FakeApplication:
        def __init__(self, args):
            pass

        def setApplicationName(self, name):
            pass

        def setApplicationVersion(self, version):
            pass

        def setQuitOnLastWindowClosed(self, enabled):
            pass

        def exec(self):
            raise AssertionError("a second launch must never enter the event loop")

    class FakeSignal:
        def connect(self, slot):
            pass

    class SecondaryInstanceGuard:
        def __init__(self, app):
            self.activated = FakeSignal()

        def try_become_primary(self):
            return False

    class FakeConfig:
        def get(self, key, default=None):
            return 0

    window_calls = []
    root_logger = logging.getLogger("PyProxySwitch")
    previous_handlers = root_logger.handlers[:]
    root_logger.handlers = [logging.NullHandler()]
    try:
        with monkeypatch.context() as scoped_monkeypatch:
            scoped_monkeypatch.setattr(QtWidgets, "QApplication", FakeApplication)
            scoped_monkeypatch.setattr(
                main_window, "Window", lambda: window_calls.append(1) or object()
            )
            scoped_monkeypatch.setattr(
                "pyproxyswitch.single_instance.SingleInstanceGuard", SecondaryInstanceGuard
            )
            scoped_monkeypatch.setattr("pyproxyswitch.config.ConfigManager", FakeConfig)
            with pytest.raises(SystemExit, match="0"):
                application.main()
    finally:
        root_logger.handlers = previous_handlers

    assert window_calls == []
    assert "already running" in capsys.readouterr().out


def test_listener_start_failure_is_visible_in_tray(qapp, tmp_path, monkeypatch) -> None:
    _make_config(tmp_path)
    errors = []
    monkeypatch.setattr(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", lambda: True)
    monkeypatch.setattr(QtWidgets.QSystemTrayIcon, "show", lambda self: None)
    monkeypatch.setattr(
        "pyproxyswitch.gui.main_window.ProxyManager.start_proxy",
        lambda self, name: (_ for _ in ()).throw(OSError("port already in use")),
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "critical",
        lambda *args: errors.append(args[2]),
    )

    window = main_window.Window()
    try:
        assert not window.proxy_service_available
        assert window.tr("Proxy service unavailable") in window.trayIcon.toolTip()
        assert errors and "port already in use" in errors[0]
    finally:
        window.cleanup_tray_icon()


def test_welcome_is_shown_only_on_first_start(qapp, tmp_path, monkeypatch) -> None:
    config = _make_config(tmp_path)
    messages = []
    monkeypatch.setattr(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", lambda: True)
    monkeypatch.setattr(QtWidgets.QSystemTrayIcon, "show", lambda self: None)
    monkeypatch.setattr(
        "pyproxyswitch.gui.main_window.ProxyManager.start_proxy", lambda self, name: None
    )
    monkeypatch.setattr(main_window.Window, "showWelcome", lambda self: messages.append(True))

    first = main_window.Window()
    try:
        assert messages == [True]
        assert config.get("SHOW_WELCOME") == 0
        saved = json.loads(config.get_config_path().read_text(encoding="utf-8"))
        assert saved["SHOW_WELCOME"] == 0
    finally:
        first.cleanup_tray_icon()

    second = main_window.Window()
    try:
        assert messages == [True]
    finally:
        second.cleanup_tray_icon()


def test_failed_proxy_save_restores_table_and_config(qapp, tmp_path, monkeypatch) -> None:
    config = _make_config(
        tmp_path,
        [("one", "localhost", "8080", "HTTP", "", "")],
    )
    dialog = Config_Dialog()
    errors = []
    monkeypatch.setattr(dialog, "show_error", errors.append)
    monkeypatch.setattr(config, "save_proxies", lambda: False)

    address_index = dialog.data_model.index(0, dialog.proxy_address)
    dialog.data_model.setData(address_index, "changed.example", QtCore.Qt.ItemDataRole.EditRole)

    assert config.get_proxies()[0][1] == "localhost"
    assert dialog.data_model.data(dialog.data_model.index(0, dialog.proxy_address)) == "localhost"
    assert errors


def test_inline_edit_cannot_persist_incomplete_socks5_credentials(
    qapp, tmp_path, monkeypatch
) -> None:
    config = _make_config(
        tmp_path,
        [("socks", "localhost", "1080", "SOCKS5", "", "")],
    )
    dialog = Config_Dialog()
    errors = []
    monkeypatch.setattr(dialog, "show_error", errors.append)

    username_index = dialog.data_model.index(0, dialog.proxy_user)
    dialog.data_model.setData(username_index, "alice", QtCore.Qt.ItemDataRole.EditRole)

    assert config.get_proxies()[0][4:] == ("", "")
    assert dialog.data_model.data(dialog.data_model.index(0, dialog.proxy_user)) == ""
    assert errors and "同时提供" in errors[0]


def _make_watched_window(tmp_path, monkeypatch, started):
    """Build a Window whose route changes are recorded instead of applied."""

    monkeypatch.setattr(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", lambda: True)
    monkeypatch.setattr(QtWidgets.QSystemTrayIcon, "show", lambda self: None)
    monkeypatch.setattr(
        "pyproxyswitch.gui.main_window.ProxyManager.start_proxy",
        lambda self, name: started.append(name),
    )
    return main_window.Window()


def test_external_proxy_list_edit_refreshes_menu_and_route(qapp, tmp_path, monkeypatch) -> None:
    _make_config(tmp_path, [("one", "localhost", "8080", "HTTP", "", "")])
    started = []
    window = _make_watched_window(tmp_path, monkeypatch, started)
    try:
        assert started == ["NoProxy"]

        (tmp_path / "proxy.txt").write_text(
            "one localhost:8080\ntwo localhost:8081\n", encoding="utf-8"
        )
        window._reload_external_config()

        assert started == ["NoProxy", "NoProxy"]
        assert window.proxy_names == ["one", "two", "NoProxy"]
        menu_texts = [action.text() for action in window.trayIconMenu.actions()]
        assert "two" in menu_texts
    finally:
        window.cleanup_tray_icon()


def test_self_save_does_not_reapply_route(qapp, tmp_path, monkeypatch) -> None:
    config = _make_config(tmp_path, [("one", "localhost", "8080", "HTTP", "", "")])
    assert config.save_proxies()
    started = []
    window = _make_watched_window(tmp_path, monkeypatch, started)
    try:
        assert started == ["NoProxy"]

        # 自身保存 LAST_ITEM 等无关设置不应触发菜单刷新或路由重建。
        window._config.set("LAST_ITEM", "NoProxy")
        assert window._config.save()
        window._reload_external_config()

        assert started == ["NoProxy"]
    finally:
        window.cleanup_tray_icon()


def test_removed_current_proxy_falls_back_to_no_proxy(qapp, tmp_path, monkeypatch) -> None:
    config = _make_config(tmp_path, [("one", "localhost", "8080", "HTTP", "", "")])
    config.set("LAST_ITEM", "one")
    started = []
    window = _make_watched_window(tmp_path, monkeypatch, started)
    try:
        assert started == ["one"]

        (tmp_path / "proxy.txt").write_text("two localhost:8081\n", encoding="utf-8")
        window._reload_external_config()

        assert window.item_text == "NoProxy"
        assert started == ["one", "NoProxy"]
    finally:
        window.cleanup_tray_icon()


def test_connectivity_results_color_proxy_names(qapp, tmp_path, monkeypatch) -> None:
    _make_config(
        tmp_path,
        [
            ("one", "localhost", "8080", "HTTP", "", ""),
            ("two", "localhost", "8081", "SOCKS5", "", ""),
        ],
    )
    # 自动触发的后台检测被替换掉，测试只验证结果如何标示。
    monkeypatch.setattr(Config_Dialog, "_start_proxy_checks", lambda self: None)
    dialog = Config_Dialog()

    dialog._apply_check_result("one", True)
    dialog._apply_check_result("two", False)

    colors = {}
    for row in range(dialog.data_model.rowCount()):
        item = dialog.data_model.item(row, dialog.proxy_name)
        colors[item.text()] = item.foreground().color().name()
    assert colors == {"one": "#2e7d32", "two": "#c62828"}


def test_tray_menu_copies_proxy_address(qapp, tmp_path, monkeypatch) -> None:
    _make_config(tmp_path)
    started = []
    window = _make_watched_window(tmp_path, monkeypatch, started)
    try:
        menu_texts = [action.text() for action in window.trayIconMenu.actions()]
        assert window.tr("Copy proxy address") in menu_texts
        assert window.tr("Open config directory") in menu_texts

        window.copy_proxy_address()
        assert QtGui.QGuiApplication.clipboard().text() == "127.0.0.1:8888"
    finally:
        window.cleanup_tray_icon()


def test_open_config_dir_uses_config_parent(qapp, tmp_path, monkeypatch) -> None:
    _make_config(tmp_path)
    started = []
    opened = []
    monkeypatch.setattr(QtGui.QDesktopServices, "openUrl", lambda url: opened.append(url))
    window = _make_watched_window(tmp_path, monkeypatch, started)
    try:
        window.open_config_dir()
        assert opened
        assert opened[0].isLocalFile()
        assert opened[0].toLocalFile() == str(tmp_path)
    finally:
        window.cleanup_tray_icon()
