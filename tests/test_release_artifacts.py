"""Tests for release artifact version verification."""

from __future__ import annotations

import importlib.util
import io
import tarfile
import zipfile
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def verifier():
    script = Path(__file__).parents[1] / "tools" / "verify_release_artifacts.py"
    spec = importlib.util.spec_from_file_location("verify_release_artifacts", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_artifacts(directory: Path, version: str) -> None:
    metadata = (f"Metadata-Version: 2.4\nName: PyProxySwitch\nVersion: {version}\n\n").encode()
    wheel = directory / f"pyproxyswitch-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(f"pyproxyswitch-{version}.dist-info/METADATA", metadata)

    sdist = directory / f"pyproxyswitch-{version}.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        info = tarfile.TarInfo(f"pyproxyswitch-{version}/PKG-INFO")
        info.size = len(metadata)
        archive.addfile(info, io.BytesIO(metadata))
        nested = tarfile.TarInfo(f"pyproxyswitch-{version}/PyProxySwitch.egg-info/PKG-INFO")
        nested.size = len(metadata)
        archive.addfile(nested, io.BytesIO(metadata))


def _write_portable(directory: Path, version: str) -> Path:
    stem = f"PyProxySwitch-{version}-windows-x64-portable"
    portable = directory / f"{stem}.zip"
    with zipfile.ZipFile(portable, "w") as archive:
        archive.writestr(f"{stem}/PyProxySwitch.exe", b"executable")
        archive.writestr(f"{stem}/portable.ini", b"")
    return portable


def test_matching_artifacts_pass(verifier, tmp_path, capsys) -> None:
    _write_artifacts(tmp_path, "4.2.0")

    verifier.verify_release_artifacts(tmp_path, "4.2.0")

    assert "expected=4.2.0 wheel=4.2.0 sdist=4.2.0" in capsys.readouterr().out


def test_mismatched_artifacts_fail(verifier, tmp_path) -> None:
    _write_artifacts(tmp_path, "4.2.0")

    with pytest.raises(ValueError, match="does not match release tag"):
        verifier.verify_release_artifacts(tmp_path, "4.2.1")


def test_all_matching_release_artifacts_pass(verifier, tmp_path, capsys) -> None:
    distributions = tmp_path / "python"
    portable = tmp_path / "portable"
    distributions.mkdir()
    portable.mkdir()
    _write_artifacts(distributions, "4.2.0")
    portable_path = _write_portable(portable, "4.2.0")

    verifier.verify_release_artifacts(distributions, "4.2.0", portable)

    output = capsys.readouterr().out
    assert f"portable={portable_path.name}" in output


def test_portable_archive_name_must_match_release(verifier, tmp_path) -> None:
    _write_portable(tmp_path, "4.2.0")

    with pytest.raises(ValueError, match="name does not match release tag"):
        verifier.verify_portable_artifact(tmp_path, "4.2.1")


def test_portable_archive_requires_executable_and_marker(verifier, tmp_path) -> None:
    stem = "PyProxySwitch-4.2.0-windows-x64-portable"
    with zipfile.ZipFile(tmp_path / f"{stem}.zip", "w") as archive:
        archive.writestr(f"{stem}/README.md", b"readme")

    with pytest.raises(ValueError, match="missing required entries"):
        verifier.verify_portable_artifact(tmp_path, "4.2.0")
