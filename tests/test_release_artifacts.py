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


def test_matching_artifacts_pass(verifier, tmp_path, capsys) -> None:
    _write_artifacts(tmp_path, "4.2.0")

    verifier.verify_release_artifacts(tmp_path, "4.2.0")

    assert "expected=4.2.0 wheel=4.2.0 sdist=4.2.0" in capsys.readouterr().out


def test_mismatched_artifacts_fail(verifier, tmp_path) -> None:
    _write_artifacts(tmp_path, "4.2.0")

    with pytest.raises(ValueError, match="does not match release tag"):
        verifier.verify_release_artifacts(tmp_path, "4.2.1")
