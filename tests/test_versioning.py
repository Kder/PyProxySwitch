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


def test_release_procedure_is_kept_out_of_user_readmes() -> None:
    chinese_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    english_readme = (REPO_ROOT / "README_EN.txt").read_text(encoding="utf-8")
    release_guide = (REPO_ROOT / "RELEASING.md").read_text(encoding="utf-8")
    manifest = (REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert "## 发布到 PyPI" not in chinese_readme
    assert "Publishing to PyPI" not in english_readme
    assert "Trusted Publishers" not in chinese_readme
    assert "Trusted Publishers" not in english_readme
    assert "Git tag 是正式版本的唯一来源" in release_guide
    assert ".github/workflows/publish.yml" in release_guide
    assert "include RELEASING.md" in manifest
