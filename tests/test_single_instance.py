import os

from PySide6.QtTest import QSignalSpy

from pyproxyswitch.single_instance import SingleInstanceGuard, server_name


def _unique_name(prefix: str) -> str:
    return f"{prefix}-{os.getpid()}"


def test_server_name_scoped_to_user_and_config(monkeypatch, tmp_path):
    monkeypatch.setattr("pyproxyswitch.single_instance.USER_CONFIG_DIR", tmp_path / "conf-a")
    name_a = server_name()
    monkeypatch.setattr("pyproxyswitch.single_instance.USER_CONFIG_DIR", tmp_path / "conf-b")

    assert name_a.startswith("PyProxySwitch-")
    assert server_name() != name_a


def test_first_instance_becomes_primary(qapp):
    guard = SingleInstanceGuard(name=_unique_name("PyProxySwitch-test-primary"))

    assert guard.try_become_primary()
    assert guard.is_primary


def test_second_instance_activates_existing_primary(qapp):
    name = _unique_name("PyProxySwitch-test-second")
    primary = SingleInstanceGuard(name=name)
    assert primary.try_become_primary()
    spy = QSignalSpy(primary.activated)

    secondary = SingleInstanceGuard(name=name)

    assert not secondary.try_become_primary()
    assert not secondary.is_primary
    # The activation request is delivered once the primary's event loop runs.
    assert spy.wait(2000)


def test_instances_with_different_names_do_not_conflict(qapp):
    first = SingleInstanceGuard(name=_unique_name("PyProxySwitch-test-a"))
    second = SingleInstanceGuard(name=_unique_name("PyProxySwitch-test-b"))

    assert first.try_become_primary()
    assert second.try_become_primary()
