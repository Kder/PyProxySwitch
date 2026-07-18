import logging

import pytest
from PySide6 import QtCore, QtWidgets

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
    dialog.le_username.setText(" alice ")
    dialog.le_password.setText(" secret ")

    dialog.done(QtWidgets.QDialog.DialogCode.Accepted)

    assert dialog.result() == QtWidgets.QDialog.DialogCode.Accepted
    assert dialog.le_proxy_name.text() == "normalized"
    assert dialog.le_address.text() == "::1"
    assert dialog.le_username.text() == "alice"
    assert dialog.le_password.text() == " secret "


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

    class FakeConfig:
        def get(self, key, default=None):
            return 0

    root_logger = logging.getLogger("PyProxySwitch")
    previous_handlers = root_logger.handlers[:]
    root_logger.handlers = [logging.NullHandler()]
    monkeypatch.setattr(QtWidgets, "QApplication", FakeApplication)
    monkeypatch.setattr(main_window, "Window", lambda: object())
    monkeypatch.setattr("pyproxyswitch.config.ConfigManager", FakeConfig)
    try:
        with pytest.raises(SystemExit, match="0"):
            application.main()
    finally:
        root_logger.handlers = previous_handlers

    assert events == [False]


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
    assert (
        dialog.data_model.data(dialog.data_model.index(0, dialog.proxy_address))
        == "localhost"
    )
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
