"""Version-source and generated metadata regressions."""

from __future__ import annotations

import importlib.metadata
import tomllib
from pathlib import Path

import pyproxyswitch

REPO_ROOT = Path(__file__).parents[1]


def test_runtime_version_matches_installed_distribution() -> None:
    assert pyproxyswitch.__version__ == importlib.metadata.version("PyProxySwitch")


def test_setuptools_scm_is_the_only_configured_version_source() -> None:
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert config["project"]["dynamic"] == ["version"]
    assert any(
        requirement.startswith("setuptools-scm")
        for requirement in config["build-system"]["requires"]
    )
    assert config["tool"]["setuptools_scm"]["version_file"] == "pyproxyswitch/_version.py"
    assert "dynamic" not in config["tool"]["setuptools"]


def test_publish_workflow_is_tag_only_and_checks_artifact_metadata() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")

    assert '      - "v[0-9]*"' in workflow
    assert "workflow_dispatch" not in workflow
    assert "fetch-depth: 0" in workflow
    assert "Verify tag matches distribution metadata" in workflow
    assert 'expected "${GITHUB_REF_NAME#v}"' in workflow
    assert "tools/verify_release_artifacts.py" in workflow
