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


def test_packaging_and_readmes_expose_only_the_gui_entry_point() -> None:
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    chinese_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    english_readme = (REPO_ROOT / "README_EN.txt").read_text(encoding="utf-8")

    assert "scripts" not in config["project"]
    assert config["project"]["gui-scripts"] == {"pyproxyswitch": "pyproxyswitch.main:main"}
    for readme in (chinese_readme, english_readme):
        assert "pyproxyswitch-cli" not in readme
        assert "python PyProxySwitch.py" not in readme
        assert "pip install -e ." in readme


def test_github_release_workflow_builds_and_verifies_all_artifacts() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert '      - "v[0-9]*"' in workflow
    assert "workflow_dispatch" not in workflow
    assert 'python-version: "3.14"' in workflow
    assert "uv python find" in workflow
    assert "--no-managed-python" in workflow
    assert "--no-python-downloads" in workflow
    assert "--resolve-links 3.14" in workflow
    assert "--group build" in workflow
    assert "python tools/build_nuitka.py --clean" in workflow
    assert "uv build" in workflow
    assert "tools/sync_release_docs.py" in workflow
    assert '--expected-version "${GITHUB_REF_NAME#v}"' in workflow
    assert "--portable-directory artifacts/portable" in workflow
    assert "gh release create" in workflow
    assert "artifacts/python/*.whl" in workflow
    assert "artifacts/python/*.tar.gz" in workflow
    assert "artifacts/portable/*.zip" in workflow
    assert "pypa/gh-action-pypi-publish" in workflow
    assert workflow.count("uv build") == 1
    assert workflow.count("name: python-distributions") >= 3
    assert not (REPO_ROOT / ".github" / "workflows" / "publish.yml").exists()


def test_test_workflow_watches_all_packaging_inputs() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")

    for path in (
        ".python-version",
        "LICENSE",
        "MANIFEST.in",
        "README.md",
        "README_EN.txt",
        "RELEASING.md",
        "uv.lock",
    ):
        assert workflow.count(f"- '{path}'") == 2


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
    assert ".github/workflows/release.yml" in release_guide
    assert "include tools/release.py" in manifest
    assert "include RELEASING.md" in manifest
    assert "include CHANGELOG.md" in manifest
    assert "include releases.toml" in manifest
    assert "prune htdocs" in manifest
