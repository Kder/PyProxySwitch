import subprocess
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


def test_existing_release_tag_is_ignored_only_for_a_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        release,
        "_release_tag_versions",
        lambda: {"4.0.3", "4.0.4"},
    )

    release._require_newer_than_tags("4.0.4", allow_existing=True)

    with pytest.raises(release.ReleaseError, match="existing tag v4.0.4"):
        release._require_newer_than_tags("4.0.4")


def test_release_retry_still_rejects_a_newer_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        release,
        "_release_tag_versions",
        lambda: {"4.0.4", "4.0.5"},
    )

    with pytest.raises(release.ReleaseError, match="existing tag v4.0.5"):
        release._require_newer_than_tags("4.0.4", allow_existing=True)


def test_release_tag_versions_include_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_git_output(*args):
        if args[0] == "tag":
            return "v4.0.3"
        return f"{'b' * 40}\trefs/tags/v4.0.4"

    monkeypatch.setattr(release, "_git_output", fake_git_output)

    assert release._release_tag_versions() == {"4.0.3", "4.0.4"}


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


def test_require_pushed_head_fetches_without_updating_tags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    head = "a" * 40
    calls = []

    def fake_run(command, *, capture=False, env=None):
        calls.append(command)
        if command[-1] in {"HEAD", "refs/remotes/origin/master"}:
            return head
        return ""

    monkeypatch.setattr(release, "_run", fake_run)

    assert release._require_pushed_head() == head
    assert calls[0] == ["git", "fetch", "--no-tags", "origin", "master"]


def test_local_release_tag_requires_a_valid_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    head = "a" * 40
    monkeypatch.setattr(release, "_local_tag_object", lambda tag: "b" * 40)
    monkeypatch.setattr(release, "_git_output", lambda *args: head)

    def reject_signature(command, *, capture=False, env=None):
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(release, "_run", reject_signature)

    with pytest.raises(release.ReleaseError, match="valid signature"):
        release._validate_local_release_tag("v4.0.4", head)


def test_local_release_tag_must_target_current_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    head = "a" * 40
    other = "c" * 40
    monkeypatch.setattr(release, "_local_tag_object", lambda tag: "b" * 40)
    monkeypatch.setattr(release, "_git_output", lambda *args: other)
    monkeypatch.setattr(release, "_run", pytest.fail)

    with pytest.raises(release.ReleaseError, match=f"targets {other[:12]}"):
        release._validate_local_release_tag("v4.0.4", head)


@pytest.mark.parametrize(
    ("remote_output", "message"),
    [
        (
            f"{'b' * 40}\trefs/tags/v4.0.4",
            "not an annotated tag",
        ),
        (
            (
                f"{'b' * 40}\trefs/tags/v4.0.4\n"
                f"{'c' * 40}\trefs/tags/v4.0.4^{{}}"
            ),
            "targets",
        ),
    ],
)
def test_remote_release_tag_rejects_invalid_state(
    remote_output: str,
    message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(release, "_git_output", lambda *args: remote_output)

    with pytest.raises(release.ReleaseError, match=message):
        release._remote_release_tag_object("v4.0.4", "a" * 40)


def test_remote_release_tag_accepts_annotated_tag_at_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    head = "a" * 40
    tag_object = "b" * 40
    remote_output = (
        f"{tag_object}\trefs/tags/v4.0.4\n"
        f"{head}\trefs/tags/v4.0.4^{{}}"
    )
    monkeypatch.setattr(release, "_git_output", lambda *args: remote_output)

    assert release._remote_release_tag_object("v4.0.4", head) == tag_object


def test_inspect_release_tag_fetches_and_verifies_remote_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    head = "a" * 40
    tag_object = "b" * 40
    calls = []
    monkeypatch.setattr(release, "_local_tag_object", lambda tag: None)
    monkeypatch.setattr(
        release,
        "_remote_release_tag_object",
        lambda tag, expected_head: tag_object,
    )
    monkeypatch.setattr(
        release,
        "_validate_local_release_tag",
        lambda tag, expected_head: tag_object,
    )
    monkeypatch.setattr(
        release,
        "_run",
        lambda command, **kwargs: calls.append(command) or "",
    )

    state = release._inspect_release_tag("4.0.4", head)

    assert state == release._ReleaseTagState(tag_object, tag_object)
    assert calls == [
        [
            "git",
            "fetch",
            "--no-tags",
            "origin",
            "refs/tags/v4.0.4:refs/tags/v4.0.4",
        ]
    ]


def test_inspect_release_tag_rejects_different_local_and_remote_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(release, "_local_tag_object", lambda tag: "b" * 40)
    monkeypatch.setattr(
        release,
        "_validate_local_release_tag",
        lambda tag, head: "b" * 40,
    )
    monkeypatch.setattr(
        release,
        "_remote_release_tag_object",
        lambda tag, head: "c" * 40,
    )

    with pytest.raises(release.ReleaseError, match="different signed tag objects"):
        release._inspect_release_tag("4.0.4", "a" * 40)


def test_publish_release_tag_reuses_local_tag_after_push_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    head = "a" * 40
    tag_object = "b" * 40
    calls = []
    allowed_existing = []
    remote_objects = iter([None, tag_object])
    monkeypatch.setattr(
        release,
        "_inspect_release_tag",
        lambda version, expected_head: release._ReleaseTagState(tag_object, None),
    )
    monkeypatch.setattr(
        release,
        "_require_newer_than_tags",
        lambda version, *, allow_existing=False: allowed_existing.append(allow_existing),
    )
    monkeypatch.setattr(
        release,
        "_remote_release_tag_object",
        lambda tag, expected_head: next(remote_objects),
    )
    monkeypatch.setattr(
        release,
        "_run",
        lambda command, **kwargs: calls.append(command) or "",
    )

    assert release._publish_release_tag("4.0.4", head)
    assert allowed_existing == [True]
    assert calls == [
        [
            "git",
            "push",
            "origin",
            "refs/tags/v4.0.4:refs/tags/v4.0.4",
        ]
    ]


def test_publish_release_tag_accepts_matching_remote_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tag_object = "b" * 40
    monkeypatch.setattr(
        release,
        "_inspect_release_tag",
        lambda version, head: release._ReleaseTagState(tag_object, tag_object),
    )
    monkeypatch.setattr(release, "_require_newer_than_tags", pytest.fail)
    monkeypatch.setattr(release, "_run", pytest.fail)

    assert not release._publish_release_tag("4.0.4", "a" * 40)


def test_publish_release_tag_creates_validates_and_pushes_new_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    head = "a" * 40
    tag_object = "b" * 40
    calls = []
    remote_objects = iter([None, tag_object])
    monkeypatch.setattr(
        release,
        "_inspect_release_tag",
        lambda version, expected_head: release._ReleaseTagState(None, None),
    )
    monkeypatch.setattr(release, "_require_newer_than_tags", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        release,
        "_validate_local_release_tag",
        lambda tag, expected_head: tag_object,
    )
    monkeypatch.setattr(
        release,
        "_remote_release_tag_object",
        lambda tag, expected_head: next(remote_objects),
    )
    monkeypatch.setattr(
        release,
        "_run",
        lambda command, **kwargs: calls.append(command) or "",
    )

    assert release._publish_release_tag("4.0.4", head)
    assert calls == [
        ["git", "tag", "-s", "v4.0.4", "-m", "PyProxySwitch 4.0.4"],
        [
            "git",
            "push",
            "origin",
            "refs/tags/v4.0.4:refs/tags/v4.0.4",
        ],
    ]


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
