#!/usr/bin/env python3
"""Prepare and publish a PyProxySwitch release.

Release metadata remains human-authored in ``releases.toml``. This command
orchestrates deterministic checks and the signed-tag handoff to the GitHub
Release and PyPI workflows.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import NoReturn

REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASES_FILE = REPO_ROOT / "releases.toml"
RELEASE_BUILD_DIR = REPO_ROOT / "build" / "release-check"
RELEASE_VERSION_RE = re.compile(r"(?:0|[1-9]\d*)(?:\.(?:0|[1-9]\d*)){2}")
TAG_RE = re.compile(r"v(\d+(?:\.\d+){1,3})")


class ReleaseError(RuntimeError):
    """A release precondition was not satisfied."""


@dataclass(frozen=True)
class _ReleaseTagState:
    local_object: str | None
    remote_object: str | None


def _run(
    command: list[str],
    *,
    capture: bool = False,
    env: dict[str, str] | None = None,
) -> str:
    print(f"+ {subprocess.list2cmdline(command)}", flush=True)
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        env={**os.environ, **env} if env is not None else None,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.rstrip() if capture else ""


def _git_output(*args: str) -> str:
    return _run(["git", *args], capture=True)


def _normalize_version(version: str) -> str:
    normalized = version.removeprefix("v")
    if RELEASE_VERSION_RE.fullmatch(normalized) is None:
        raise ReleaseError(f"release version must use X.Y.Z numeric form: {version!r}")
    return normalized


def _version_key(version: str) -> tuple[int, ...]:
    parts = tuple(int(part) for part in version.split("."))
    return parts + (0,) * (4 - len(parts))


def _latest_release() -> tuple[str, date]:
    with RELEASES_FILE.open("rb") as stream:
        document = tomllib.load(stream)
    releases = document.get("release")
    if not isinstance(releases, list) or not releases:
        raise ReleaseError("releases.toml must contain at least one [[release]] entry")
    latest = releases[0]
    if not isinstance(latest, dict):
        raise ReleaseError("the first releases.toml release entry is invalid")
    version = latest.get("version")
    release_date = latest.get("date")
    if not isinstance(version, str):
        raise ReleaseError("the latest releases.toml entry has no valid version")
    if not isinstance(release_date, date):
        raise ReleaseError(
            f"release {version} must have an explicit unquoted TOML local date"
        )
    return version, release_date


def _validate_release(version: str) -> str:
    normalized = _normalize_version(version)
    latest, release_date = _latest_release()
    if latest != normalized:
        raise ReleaseError(
            f"latest releases.toml version {latest} does not match requested "
            f"release {normalized}"
        )
    print(f"release: {normalized} ({release_date.isoformat()})")
    return normalized


def _require_master() -> None:
    branch = _git_output("branch", "--show-current")
    if branch != "master":
        raise ReleaseError(f"release commands must run on master, current branch is {branch!r}")


def _release_tag_versions() -> set[str]:
    tags = set(_git_output("tag", "--list", "v[0-9]*").splitlines())
    remote_tags = _git_output(
        "ls-remote",
        "--tags",
        "--refs",
        "origin",
        "refs/tags/v[0-9]*",
    )
    for line in remote_tags.splitlines():
        fields = line.split()
        if len(fields) != 2 or not fields[1].startswith("refs/tags/"):
            raise ReleaseError(f"git returned invalid remote tag data: {line!r}")
        tags.add(fields[1].removeprefix("refs/tags/"))

    versions: set[str] = set()
    for tag in tags:
        match = TAG_RE.fullmatch(tag.strip())
        if match is not None:
            versions.add(match.group(1))
    return versions


def _require_newer_than_tags(version: str, *, allow_existing: bool = False) -> None:
    versions = _release_tag_versions()
    if allow_existing:
        versions.discard(version)
    if not versions:
        return
    latest_tag = max(versions, key=_version_key)
    if _version_key(version) <= _version_key(latest_tag):
        raise ReleaseError(
            f"release {version} must be newer than existing tag v{latest_tag}"
        )


def _sync_and_check_docs(version: str, *, write: bool) -> None:
    command = [
        sys.executable,
        str(REPO_ROOT / "tools" / "sync_release_docs.py"),
        "--write" if write else "--check",
        "--expected-version",
        version,
    ]
    _run(command)


def _reset_release_build_dir() -> None:
    resolved = RELEASE_BUILD_DIR.resolve()
    build_root = (REPO_ROOT / "build").resolve()
    if resolved.parent != build_root:
        raise ReleaseError(f"refusing to clean unexpected build directory: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True)


def _verify_distribution_files(directory: Path) -> None:
    files = sorted(path for path in directory.iterdir() if path.is_file())
    wheels = [path for path in files if path.suffix == ".whl"]
    sdists = [path for path in files if path.name.endswith(".tar.gz")]
    unexpected = [path for path in files if path not in {*wheels, *sdists}]
    if len(wheels) != 1 or len(sdists) != 1 or unexpected:
        names = ", ".join(path.name for path in files) or "(empty)"
        raise ReleaseError(
            "release build must contain exactly one wheel and one .tar.gz "
            f"sdist; found: {names}"
        )


def _build_distributions(version: str) -> None:
    if shutil.which("uv") is None:
        raise ReleaseError("uv is required to build release artifacts")
    _reset_release_build_dir()
    _run(
        [
            "uv",
            "build",
            "--python",
            sys.executable,
            "--no-managed-python",
            "--no-python-downloads",
            "--no-create-gitignore",
            "--out-dir",
            str(RELEASE_BUILD_DIR),
        ],
        env={
            "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PYPROXYSWITCH": version,
        },
    )
    _verify_distribution_files(RELEASE_BUILD_DIR)
    _run(
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "verify_release_artifacts.py"),
            "--expected",
            version,
            str(RELEASE_BUILD_DIR),
        ]
    )


def _show_changes() -> None:
    _run(["git", "status", "--short"])
    _run(["git", "diff"])
    site = REPO_ROOT / "htdocs"
    if site.is_dir():
        _run(["git", "-C", str(site), "status", "--short"])
        _run(["git", "-C", str(site), "diff"])


def prepare(version: str) -> None:
    normalized = _validate_release(version)
    _require_master()
    _run(["git", "fetch", "origin", "--tags"])
    _require_newer_than_tags(normalized)
    _sync_and_check_docs(normalized, write=True)
    _sync_and_check_docs(normalized, write=False)

    checks = [
        [sys.executable, str(REPO_ROOT / "htdocs" / "tools" / "validate_site.py")],
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, str(REPO_ROOT / "tools" / "generate_ui.py"), "--check"],
        [sys.executable, str(REPO_ROOT / "tools" / "generate_i18n.py"), "--check"],
        [
            sys.executable,
            "-m",
            "mypy",
            "pyproxyswitch",
            "--ignore-missing-imports",
        ],
        [sys.executable, "-m", "pytest"],
    ]
    for command in checks:
        _run(command)

    _build_distributions(normalized)
    _show_changes()
    publish_command = subprocess.list2cmdline(
        [
            "uv",
            "run",
            "--python",
            sys.executable,
            "python",
            "tools/release.py",
            "publish",
            normalized,
        ]
    )
    print(
        "\nRelease preparation passed. Commit and push htdocs first if it changed, "
        "then commit and push the main repository. Wait for Tests to succeed "
        f"before running: {publish_command}"
    )


def _require_clean_checkout() -> None:
    status = _git_output("status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise ReleaseError(f"working tree or submodule is not clean:\n{status}")
    submodules = _git_output("submodule", "status", "--recursive")
    invalid = [
        line
        for line in submodules.splitlines()
        if line and not line.startswith(" ")
    ]
    if invalid:
        raise ReleaseError(
            "submodules are uninitialized, conflicted, or not at the recorded commit:\n"
            + "\n".join(invalid)
        )


def _require_pushed_head() -> str:
    _run(["git", "fetch", "--no-tags", "origin", "master"])
    head = _git_output("rev-parse", "HEAD")
    remote_head = _git_output("rev-parse", "refs/remotes/origin/master")
    if head != remote_head:
        raise ReleaseError(
            f"HEAD {head[:12]} does not match origin/master {remote_head[:12]}"
        )
    return head


def _local_tag_object(tag: str) -> str | None:
    output = _git_output(
        "for-each-ref",
        "--format=%(objectname)",
        f"refs/tags/{tag}",
    )
    objects = output.splitlines()
    if len(objects) > 1:
        raise ReleaseError(f"git returned multiple local objects for tag {tag}")
    return objects[0] if objects else None


def _remote_release_tag_object(tag: str, head: str) -> str | None:
    tag_ref = f"refs/tags/{tag}"
    peeled_ref = f"{tag_ref}^{{}}"
    output = _git_output(
        "ls-remote",
        "--tags",
        "origin",
        tag_ref,
        peeled_ref,
    )
    refs: dict[str, str] = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) != 2 or fields[1] not in {tag_ref, peeled_ref}:
            raise ReleaseError(f"git returned invalid remote state for tag {tag}: {line!r}")
        if fields[1] in refs:
            raise ReleaseError(f"git returned duplicate remote state for tag {tag}")
        refs[fields[1]] = fields[0]

    if not refs:
        return None
    if tag_ref not in refs or peeled_ref not in refs:
        raise ReleaseError(f"remote tag {tag} is not an annotated tag")
    if refs[peeled_ref] != head:
        raise ReleaseError(
            f"remote tag {tag} targets {refs[peeled_ref][:12]}, expected {head[:12]}"
        )
    return refs[tag_ref]


def _validate_local_release_tag(tag: str, head: str) -> str:
    object_id = _local_tag_object(tag)
    if object_id is None:
        raise ReleaseError(f"local tag {tag} disappeared during validation")

    target = _git_output("rev-parse", f"refs/tags/{tag}^{{}}")
    if target != head:
        raise ReleaseError(f"local tag {tag} targets {target[:12]}, expected {head[:12]}")
    try:
        _run(["git", "verify-tag", tag])
    except subprocess.CalledProcessError as exc:
        raise ReleaseError(f"local tag {tag} does not have a valid signature") from exc
    return object_id


def _inspect_release_tag(version: str, head: str) -> _ReleaseTagState:
    tag = f"v{version}"
    local_object = _local_tag_object(tag)
    if local_object is not None:
        local_object = _validate_local_release_tag(tag, head)

    remote_object = _remote_release_tag_object(tag, head)
    if remote_object is not None and local_object is None:
        tag_ref = f"refs/tags/{tag}"
        _run(["git", "fetch", "--no-tags", "origin", f"{tag_ref}:{tag_ref}"])
        local_object = _validate_local_release_tag(tag, head)

    if remote_object is not None and local_object != remote_object:
        raise ReleaseError(
            f"local and remote tag {tag} refer to different signed tag objects"
        )
    return _ReleaseTagState(local_object, remote_object)


def _publish_release_tag(version: str, head: str) -> bool:
    tag = f"v{version}"
    state = _inspect_release_tag(version, head)
    if state.remote_object is not None:
        return False

    _require_newer_than_tags(version, allow_existing=state.local_object is not None)

    local_object = state.local_object
    if local_object is None:
        _run(["git", "tag", "-s", tag, "-m", f"PyProxySwitch {version}"])
        local_object = _validate_local_release_tag(tag, head)

    remote_object = _remote_release_tag_object(tag, head)
    if remote_object is not None:
        if remote_object != local_object:
            raise ReleaseError(
                f"local and remote tag {tag} refer to different signed tag objects"
            )
        return False

    tag_ref = f"refs/tags/{tag}"
    _run(["git", "push", "origin", f"{tag_ref}:{tag_ref}"])
    remote_object = _remote_release_tag_object(tag, head)
    if remote_object != local_object:
        raise ReleaseError(f"remote tag {tag} was not updated to the expected signed tag")
    return True


def _require_successful_tests(head: str) -> None:
    if shutil.which("gh") is None:
        raise ReleaseError("GitHub CLI (gh) is required to verify the Tests workflow")
    raw = _run(
        [
            "gh",
            "run",
            "list",
            "--workflow",
            "test.yml",
            "--commit",
            head,
            "--limit",
            "20",
            "--json",
            "conclusion,headSha,status,url",
        ],
        capture=True,
    )
    runs = json.loads(raw)
    if not isinstance(runs, list):
        raise ReleaseError("GitHub CLI returned an invalid workflow-run response")
    if any(
        isinstance(run, dict)
        and run.get("headSha") == head
        and run.get("status") == "completed"
        and run.get("conclusion") == "success"
        for run in runs
    ):
        return
    summary = "\n".join(
        f"- {run.get('status')}/{run.get('conclusion')}: {run.get('url')}"
        for run in runs
        if isinstance(run, dict)
    )
    raise ReleaseError(
        f"no successful Tests workflow found for {head[:12]}"
        + (f":\n{summary}" if summary else "")
    )


def publish(version: str) -> None:
    normalized = _validate_release(version)
    _require_master()
    _require_clean_checkout()
    head = _require_pushed_head()
    _sync_and_check_docs(normalized, write=False)
    _require_successful_tests(head)

    tag = f"v{normalized}"
    if _publish_release_tag(normalized, head):
        print(
            f"\nPublished {tag}. The tag-triggered GitHub Actions workflows will "
            "build and verify the artifacts, create the GitHub Release, and publish "
            "the Python distributions to PyPI."
        )
    else:
        print(
            f"\nVerified existing {tag} on origin; no push was needed. "
            "The original tag push already triggered the release workflows."
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (
        ("prepare", "generate and validate all release inputs"),
        ("publish", "verify CI and safely create, reuse, or push the signed tag"),
    ):
        subparser = subparsers.add_parser(command, help=help_text)
        subparser.add_argument("version", help="release version in X.Y.Z form")
    return parser


def _fail(message: str) -> NoReturn:
    raise SystemExit(f"error: {message}")


def main() -> None:
    args = _parser().parse_args()
    try:
        if args.command == "prepare":
            prepare(args.version)
        else:
            publish(args.version)
    except (ReleaseError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        _fail(str(exc))


if __name__ == "__main__":
    main()
