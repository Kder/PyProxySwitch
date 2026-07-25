from datetime import date

import pytest

from tools import release


def test_normalize_release_version() -> None:
    assert release._normalize_version("4.0.4") == "4.0.4"
    assert release._normalize_version("v4.0.4") == "4.0.4"


@pytest.mark.parametrize("version", ["4.0", "4.0.4.dev1", "04.0.4", "release-4.0.4"])
def test_normalize_release_version_rejects_invalid_input(version: str) -> None:
    with pytest.raises(release.ReleaseError, match="X.Y.Z"):
        release._normalize_version(version)


def test_latest_release_requires_explicit_toml_date(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    releases_file = tmp_path / "releases.toml"
    releases_file.write_text(
        '[[release]]\nversion = "4.0.4"\ndate = "2026-07-26"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(release, "RELEASES_FILE", releases_file)

    with pytest.raises(release.ReleaseError, match="explicit unquoted TOML local date"):
        release._latest_release()


def test_latest_release_reads_version_and_date(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    releases_file = tmp_path / "releases.toml"
    releases_file.write_text(
        '[[release]]\nversion = "4.0.4"\ndate = 2026-07-26\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(release, "RELEASES_FILE", releases_file)

    assert release._latest_release() == ("4.0.4", date(2026, 7, 26))


def test_verify_distribution_files_accepts_one_wheel_and_sdist(tmp_path) -> None:
    (tmp_path / "PyProxySwitch-4.0.4-py3-none-any.whl").touch()
    (tmp_path / "pyproxyswitch-4.0.4.tar.gz").touch()

    release._verify_distribution_files(tmp_path)


def test_verify_distribution_files_rejects_unexpected_file(tmp_path) -> None:
    (tmp_path / "PyProxySwitch-4.0.4-py3-none-any.whl").touch()
    (tmp_path / "pyproxyswitch-4.0.4.tar.gz").touch()
    (tmp_path / "checksums.txt").touch()

    with pytest.raises(release.ReleaseError, match="exactly one wheel"):
        release._verify_distribution_files(tmp_path)


def test_build_distributions_uses_requested_scm_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def fake_run(command, *, capture=False, env=None):
        calls.append((command, capture, env))
        return ""

    monkeypatch.setattr(release.shutil, "which", lambda command: "uv.exe")
    monkeypatch.setattr(release, "_reset_release_build_dir", lambda: None)
    monkeypatch.setattr(release, "_verify_distribution_files", lambda directory: None)
    monkeypatch.setattr(release, "_run", fake_run)

    release._build_distributions("4.0.4")

    build_command, _, build_env = calls[0]
    assert build_command[:2] == ["uv", "build"]
    assert "--no-managed-python" in build_command
    assert "--no-python-downloads" in build_command
    assert build_env == {
        "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PYPROXYSWITCH": "4.0.4"
    }


def test_require_successful_tests_accepts_matching_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    head = "a" * 40
    response = (
        '[{"conclusion":"success","headSha":"'
        + head
        + '","status":"completed","url":"https://example.invalid/run"}]'
    )
    monkeypatch.setattr(release.shutil, "which", lambda command: "gh.exe")
    monkeypatch.setattr(release, "_run", lambda command, capture=False: response)

    release._require_successful_tests(head)


def test_require_successful_tests_rejects_failed_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    head = "b" * 40
    response = (
        '[{"conclusion":"failure","headSha":"'
        + head
        + '","status":"completed","url":"https://example.invalid/run"}]'
    )
    monkeypatch.setattr(release.shutil, "which", lambda command: "gh.exe")
    monkeypatch.setattr(release, "_run", lambda command, capture=False: response)

    with pytest.raises(release.ReleaseError, match="no successful Tests workflow"):
        release._require_successful_tests(head)
