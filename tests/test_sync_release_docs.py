"""Tests for deterministic release-document generation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]


@pytest.fixture(scope="module")
def release_docs():
    script = REPO_ROOT / "tools" / "sync_release_docs.py"
    spec = importlib.util.spec_from_file_location("sync_release_docs", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_canonical_release_data_is_bilingual_and_newest_first(release_docs) -> None:
    releases = release_docs.load_releases(REPO_ROOT / "releases.toml")

    assert releases[0].version == "4.0.2"
    assert releases[0].date.isoformat() == "2026-07-25"
    assert releases[0].summary_zh
    assert releases[0].summary_en
    assert releases[0].changes_zh
    assert releases[0].changes_en
    assert releases[-1].version == "0.9.0"


def test_expected_release_version_must_match_latest_entry(release_docs) -> None:
    releases = release_docs.load_releases(REPO_ROOT / "releases.toml")

    release_docs.validate_expected_version(releases, "v4.0.2")
    with pytest.raises(ValueError, match="does not match expected release"):
        release_docs.validate_expected_version(releases, "4.0.3")


def test_changelog_rendering_is_deterministic_and_bilingual(release_docs) -> None:
    releases = release_docs.load_releases(REPO_ROOT / "releases.toml")

    first = release_docs.render_changelog(releases)
    second = release_docs.render_changelog(releases)

    assert first == second
    assert "## 4.0.2 — 2026-07-25" in first
    assert "### 中文" in first
    assert "### English" in first
    assert "## 0.9.0 — 2009-08-20" in first


def test_invalid_or_duplicate_release_data_is_rejected(release_docs, tmp_path) -> None:
    duplicate = tmp_path / "releases.toml"
    duplicate.write_text(
        """
[[release]]
version = "1.0.0"
date = 2026-07-25
summary_zh = "测试"
summary_en = "Test"

[[release]]
version = "1.0.0"
summary_zh = "重复"
summary_en = "Duplicate"
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate release version"):
        release_docs.load_releases(duplicate)


def test_strict_html_replacement_rejects_missing_marker(release_docs) -> None:
    with pytest.raises(ValueError, match="expected one match"):
        release_docs._replace_once("no version here", r"version \d+", "version 1", "page.html")
