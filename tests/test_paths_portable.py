"""Portable-mode path resolution in :mod:`pyproxyswitch.paths`."""

from __future__ import annotations

import importlib
import sys

import pytest

import pyproxyswitch.paths as paths


@pytest.fixture
def restore_paths(monkeypatch: pytest.MonkeyPatch):
    """Restore module-level path constants after each reload-based test."""

    yield monkeypatch
    monkeypatch.undo()
    importlib.reload(paths)


def _reload():
    return importlib.reload(paths)


def test_env_home_takes_precedence(restore_paths, tmp_path):
    home = tmp_path / "pps-home"
    restore_paths.setenv(paths.ENV_HOME, str(home))
    restore_paths.setattr(sys, "frozen", True, raising=False)
    executable_dir = tmp_path / "dist"
    executable_dir.mkdir()
    (executable_dir / paths.PORTABLE_MARKER).touch()
    restore_paths.setattr(sys, "executable", str(executable_dir / "PyProxySwitch"))

    module = _reload()

    assert module.PATHS_SOURCE == "environment"
    assert module.PORTABLE_MODE is True
    assert home / "PPS.conf" == module.CONFIG_FILE
    assert home / "proxy.txt" == module.PROXY_LIST_FILE
    assert home / "logs" == module.USER_LOG_DIR


def test_portable_marker_for_frozen_executable(restore_paths, tmp_path):
    restore_paths.delenv(paths.ENV_HOME, raising=False)
    executable_dir = tmp_path / "dist"
    executable_dir.mkdir()
    (executable_dir / paths.PORTABLE_MARKER).touch()
    restore_paths.setattr(sys, "frozen", True, raising=False)
    restore_paths.setattr(sys, "executable", str(executable_dir / "PyProxySwitch"))

    module = _reload()

    assert module.PATHS_SOURCE == "portable"
    assert module.PORTABLE_MODE is True
    assert executable_dir / "config" / "PPS.conf" == module.CONFIG_FILE
    assert executable_dir / "config" / "proxy.txt" == module.PROXY_LIST_FILE
    assert executable_dir / "logs" == module.USER_LOG_DIR


def test_frozen_without_marker_falls_back_to_user_dirs(restore_paths, tmp_path):
    restore_paths.delenv(paths.ENV_HOME, raising=False)
    restore_paths.setattr(sys, "frozen", True, raising=False)
    restore_paths.setattr(sys, "executable", str(tmp_path / "dist" / "PyProxySwitch"))

    module = _reload()

    assert module.PATHS_SOURCE == "user"
    assert module.PORTABLE_MODE is False


def test_default_resolution_uses_user_dirs(restore_paths):
    restore_paths.delenv(paths.ENV_HOME, raising=False)
    restore_paths.delattr(sys, "frozen", raising=False)

    module = _reload()

    assert module.PATHS_SOURCE == "user"
    assert module.PORTABLE_MODE is False
    assert module.CONFIG_FILE.parent == module.USER_CONFIG_DIR
    assert module.PROXY_LIST_FILE.parent == module.USER_CONFIG_DIR


def test_initialize_user_config_never_overwrites(tmp_path):
    config = tmp_path / "cfg" / "PPS.conf"
    proxy_list = tmp_path / "cfg" / "proxy.txt"

    paths.initialize_user_config(config, proxy_list)

    assert config.exists()
    assert proxy_list.exists()
    config.write_text("# user edits\n", encoding="utf-8")

    paths.initialize_user_config(config, proxy_list)

    assert config.read_text(encoding="utf-8") == "# user edits\n"
