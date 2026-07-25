#!/usr/bin/env python3
"""Verify that wheel and sdist metadata match an expected release version."""

from __future__ import annotations

import argparse
import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath


def _single_match(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one {pattern!r} file in {directory}, found {len(matches)}"
        )
    return matches[0]


def wheel_version(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        metadata_names = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_names) != 1:
            raise ValueError(
                f"expected exactly one .dist-info/METADATA in {path}, found {len(metadata_names)}"
            )
        version = BytesParser().parsebytes(archive.read(metadata_names[0]))["Version"]
    if not version:
        raise ValueError(f"wheel metadata has no Version field: {path}")
    return version


def sdist_version(path: Path) -> str:
    with tarfile.open(path, "r:gz") as archive:
        pkg_info_members = [
            member
            for member in archive.getmembers()
            if member.name.endswith("/PKG-INFO") and len(PurePosixPath(member.name).parts) == 2
        ]
        if len(pkg_info_members) != 1:
            raise ValueError(
                f"expected exactly one PKG-INFO in {path}, found {len(pkg_info_members)}"
            )
        extracted = archive.extractfile(pkg_info_members[0])
        if extracted is None:
            raise ValueError(f"cannot read PKG-INFO from sdist: {path}")
        version = BytesParser().parse(extracted)["Version"]
    if not version:
        raise ValueError(f"sdist metadata has no Version field: {path}")
    return version


def verify_release_artifacts(directory: Path, expected: str) -> None:
    wheel = _single_match(directory, "*.whl")
    sdist = _single_match(directory, "*.tar.gz")
    versions = {
        "wheel": wheel_version(wheel),
        "sdist": sdist_version(sdist),
    }
    print(f"expected={expected} wheel={versions['wheel']} sdist={versions['sdist']}")
    mismatches = {kind: version for kind, version in versions.items() if version != expected}
    if mismatches:
        details = ", ".join(f"{kind}={version}" for kind, version in mismatches.items())
        raise ValueError(f"distribution version does not match release tag: {details}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="directory containing one wheel and one sdist")
    parser.add_argument("--expected", required=True, help="expected PEP 440 version")
    args = parser.parse_args()

    try:
        verify_release_artifacts(args.directory, args.expected)
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
