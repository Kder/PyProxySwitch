#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test to verify that Config_Dialog buttons are properly connected.
This test ensures the AttributeError fix is working correctly.
"""

import pytest
import sys
from pathlib import Path

# Add the src directory to the path so we can import the modules
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

try:
    from PySide6 import QtWidgets, QtCore
    from src.gui.config_dialog import Config_Dialog
    from src.config import ConfigManager
    PYSIDE_AVAILABLE = True
except ImportError as e:
    PYSIDE_AVAILABLE = False
    print(f"PySide6 not available for testing: {e}")


@pytest.mark.skipif(not PYSIDE_AVAILABLE, reason="PySide6 not available")
def test_config_dialog_button_connections():
    """Test that Config_Dialog buttons exist and are properly connected."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])

    # Create a mock parent widget
    parent = QtWidgets.QWidget()
    parent.dialog_exsit = False

    # Create the dialog
    dialog = Config_Dialog(parent)

    # Test that the buttons exist and have the expected attributes
    assert hasattr(dialog, 'btn_add_proxy'), "btn_add_proxy button should exist"
    assert hasattr(dialog, 'btn_del'), "btn_del button should exist"
    assert hasattr(dialog, 'btn_mod'), "btn_mod button should exist"
    assert hasattr(dialog, 'btn_batch'), "btn_batch button should exist"

    # Test that the buttons are properly connected (no AttributeError should occur)
    # These calls should not raise AttributeError
    try:
        dialog.btn_add_proxy.clicked.emit()
        dialog.btn_del.clicked.emit()
        dialog.btn_mod.clicked.emit()
        dialog.btn_batch.clicked.emit()
    except AttributeError as e:
        pytest.fail(f"Button connection failed with AttributeError: {e}")

    # Test that the methods exist
    assert hasattr(dialog, 'add_proxy'), "add_proxy method should exist"
    assert hasattr(dialog, 'del_proxy'), "del_proxy method should exist"
    assert hasattr(dialog, 'modify_proxy'), "modify_proxy method should exist"
    assert hasattr(dialog, 'show_batch_dialog'), "show_batch_dialog method should exist"
    assert hasattr(dialog, 'import_proxies'), "import_proxies method should exist"
    assert hasattr(dialog, 'export_proxies'), "export_proxies method should exist"

    dialog.close()


@pytest.mark.skipif(not PYSIDE_AVAILABLE, reason="PySide6 not available")
def test_config_dialog_no_attribute_error_on_init():
    """Test that Config_Dialog initialization doesn't raise AttributeError."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])

    parent = QtWidgets.QWidget()
    parent.dialog_exsit = False

    try:
        dialog = Config_Dialog(parent)
        success = True
    except AttributeError as e:
        success = False
        print(f"AttributeError during initialization: {e}")

    assert success, "Config_Dialog initialization should not raise AttributeError"
    dialog.close()


if __name__ == "__main__":
    if PYSIDE_AVAILABLE:
        test_config_dialog_no_attribute_error_on_init()
        test_config_dialog_button_connections()
        print("All tests passed!")
    else:
        print("Skipping tests - PySide6 not available")