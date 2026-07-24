"""Tests for the portable Nuitka build helper."""

from __future__ import annotations

import argparse
import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def build_nuitka():
    script = Path(__file__).parents[1] / "tools" / "build_nuitka.py"
    spec = importlib.util.spec_from_file_location("build_nuitka", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _args(output_dir: Path, *, onefile: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        output_dir=str(output_dir),
        onefile=onefile,
        no_zip=False,
        lto=False,
        debug=False,
        jobs=2,
    )


def test_load_version_matches_package(build_nuitka):
    from pyproxyswitch._version import __version__

    assert __version__ == build_nuitka.load_version()


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("4.0.1", "4.0.1.0"),
        ("4.1.0rc2", "4.1.0.2"),
        ("5", "5.0.0.0"),
    ],
)
def test_windows_file_version(build_nuitka, version, expected):
    assert expected == build_nuitka.windows_file_version(version)


def test_build_command_contains_portable_runtime_data(build_nuitka, monkeypatch, tmp_path):
    monkeypatch.setattr(build_nuitka, "qt_translations_dir", lambda: None)

    command = build_nuitka.build_command(_args(tmp_path), "4.0.1")

    assert "--standalone" in command
    assert "--enable-plugin=pyside6" in command
    assert any(
        item.startswith("--include-data-dir=") and item.endswith("=pyproxyswitch/data")
        for item in command
    )
    assert str(build_nuitka.MAIN_SCRIPT) == command[-1]


def test_stage_and_zip_one_directory_build(build_nuitka, monkeypatch, tmp_path):
    output_dir = tmp_path / "nuitka"
    dist_dir = output_dir / "PyProxySwitch.dist"
    dist_dir.mkdir(parents=True)
    executable_name = "PyProxySwitch.exe" if sys.platform == "win32" else "PyProxySwitch"
    (dist_dir / executable_name).write_bytes(b"fake executable")
    monkeypatch.setattr(build_nuitka, "REPO_ROOT", Path(__file__).parents[1])

    staging = build_nuitka.stage_portable_build(_args(output_dir), "4.0.1")
    archive = build_nuitka.create_portable_zip(staging)

    assert (staging / "portable.ini").is_file()
    assert (staging / executable_name).read_bytes() == b"fake executable"
    assert (staging / "README.md").is_file()
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
    prefix = f"{staging.name}/"
    assert prefix + "portable.ini" in names
    assert prefix + executable_name in names


def test_dry_run_does_not_create_output_or_require_nuitka(
    build_nuitka, monkeypatch, tmp_path, capsys
):
    output_dir = tmp_path / "dry-run"
    monkeypatch.setattr(build_nuitka, "validate_build_environment", pytest.fail)

    build_nuitka.main(["--dry-run", "--output-dir", str(output_dir)])

    assert not output_dir.exists()
    output = capsys.readouterr().out
    assert "Nuitka portable build" in output
    assert "--standalone" in output
