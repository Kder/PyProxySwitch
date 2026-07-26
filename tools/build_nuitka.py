#!/usr/bin/env python3
"""Build a portable PyProxySwitch executable with Nuitka.

The default is a standalone, one-directory build. Nuitka intermediates are
written to ``build/nuitka`` and distributable artifacts to ``release`` so
``dist`` remains reserved for Python sdists and wheels. The staged application
contains ``portable.ini`` so configuration is written to ``config/`` and logs
to ``logs/`` next to the executable. A versioned portable zip is created unless
``--no-zip`` is supplied.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAIN_SCRIPT = REPO_ROOT / "PyProxySwitch.py"
ICON_FILE = REPO_ROOT / "img" / "PyProxySwitch.ico"
DATA_SRC = REPO_ROOT / "pyproxyswitch" / "data"
DEFAULT_BUILD_DIR = REPO_ROOT / "build" / "nuitka"
DEFAULT_RELEASE_DIR = REPO_ROOT / "release"
EXE_NAME = "PyProxySwitch.exe" if sys.platform == "win32" else "PyProxySwitch"


def load_version() -> str:
    """Derive the current package version directly from the Git checkout."""

    from setuptools_scm import get_version

    return get_version(root=str(REPO_ROOT), local_scheme="no-local-version")


def platform_tag() -> str:
    """Return a compact platform and architecture tag for the archive."""

    system = {"win32": "windows", "darwin": "macos"}.get(sys.platform, sys.platform)
    machine = platform.machine().lower() or "unknown"
    machine = {
        "amd64": "x64",
        "x86_64": "x64",
        "aarch64": "arm64",
    }.get(machine, machine)
    return f"{system}-{machine}"


def windows_file_version(version: str) -> str:
    """Convert a package version to Nuitka's four-part numeric file version."""

    numeric_parts = [int(part) for part in re.findall(r"\d+", version)[:4]]
    numeric_parts.extend([0] * (4 - len(numeric_parts)))
    return ".".join(str(part) for part in numeric_parts)


def qt_translations_dir() -> Path | None:
    """Locate the Qt base translation catalogs shipped with PySide6."""

    try:
        from PySide6.QtCore import QLibraryInfo
    except ImportError:
        return None
    path = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    return path if path.is_dir() else None


def build_command(args: argparse.Namespace, version: str) -> list[str]:
    """Assemble the Nuitka command line."""

    command = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--enable-plugin=pyside6",
        f"--include-data-dir={DATA_SRC}=pyproxyswitch/data",
        f"--output-dir={Path(args.output_dir).resolve()}",
        f"--output-filename={EXE_NAME}",
        "--assume-yes-for-downloads",
        f"--jobs={args.jobs}",
    ]

    translations = qt_translations_dir()
    if translations is not None:
        # Nuitka patches QLibraryInfo.TranslationsPath to
        # ``<bundle>/PySide6/translations``. Keep Qt's catalogs at that exact
        # runtime path so QTranslator can find qtbase_zh_CN.qm and translate
        # standard buttons such as OK, Cancel and Close.
        command.append(f"--include-data-dir={translations}=PySide6/translations")

    if args.onefile:
        command.append("--onefile")
    if args.lto:
        command.append("--lto=yes")
    if args.debug:
        command.append("--debug")

    if sys.platform == "win32":
        file_version = windows_file_version(version)
        command.extend(
            [
                "--windows-console-mode=disable",
                f"--windows-icon-from-ico={ICON_FILE}",
                "--company-name=Kder",
                "--product-name=PyProxySwitch",
                f"--file-version={file_version}",
                f"--product-version={file_version}",
                "--file-description=PyProxySwitch - cross-platform proxy switcher",
            ]
        )

    command.append(str(MAIN_SCRIPT))
    return command


def validate_build_environment() -> None:
    """Fail early when a required platform build tool is clearly unavailable."""

    if importlib.util.find_spec("nuitka") is None:
        raise SystemExit(
            "error: Nuitka is not installed. Run: "
            "uv run --python <system-python-3.14> --group build "
            "python tools/build_nuitka.py"
        )

    if sys.platform == "darwin" and shutil.which("clang") is None:
        raise SystemExit("error: clang not found; install the Xcode command line tools")

    if sys.platform not in {"win32", "darwin"}:
        problems = []
        if shutil.which("gcc") is None and shutil.which("clang") is None:
            problems.append("a C compiler (gcc or clang)")
        if shutil.which("patchelf") is None:
            problems.append("patchelf")
        if problems:
            joined = " and ".join(problems)
            raise SystemExit(f"error: {joined} not found; required for a standalone build")


def _replace_directory(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def stage_portable_build(args: argparse.Namespace, version: str) -> Path:
    """Copy build output into a versioned portable staging directory."""

    output_dir = Path(args.output_dir).resolve()
    release_dir = Path(args.release_dir).resolve()
    staging = release_dir / f"PyProxySwitch-{version}-{platform_tag()}-portable"
    release_dir.mkdir(parents=True, exist_ok=True)

    if args.onefile:
        executable = output_dir / EXE_NAME
        if not executable.is_file():
            raise SystemExit(f"error: expected executable not found: {executable}")
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        shutil.copy2(executable, staging / executable.name)
    else:
        dist_dir = output_dir / "PyProxySwitch.dist"
        if not dist_dir.is_dir():
            raise SystemExit(f"error: expected Nuitka output not found: {dist_dir}")
        _replace_directory(dist_dir, staging)

    (staging / "portable.ini").write_text(
        "# Portable mode marker for PyProxySwitch.\n"
        "# Delete this file to use the operating system's per-user directories.\n",
        encoding="utf-8",
    )

    for filename in ("README.md", "README_EN.txt", "LICENSE"):
        source = REPO_ROOT / filename
        if source.is_file():
            shutil.copy2(source, staging / filename)

    print(f"portable folder: {staging}")
    return staging


def create_portable_zip(staging: Path) -> Path:
    """Create a zip whose top-level directory is the portable folder."""

    archive_base = staging.parent / staging.name
    archive = shutil.make_archive(
        str(archive_base),
        "zip",
        root_dir=staging.parent,
        base_dir=staging.name,
    )
    result = Path(archive)
    print(f"portable zip   : {result}")
    return result


def clean_output_directory(output_dir: Path) -> None:
    """Remove a build output directory after rejecting unsafe broad targets."""

    resolved = output_dir.resolve()
    repo_root = REPO_ROOT.resolve()
    protected = {Path(resolved.anchor), repo_root, repo_root.parent, Path.home().resolve()}
    if resolved in protected or repo_root.is_relative_to(resolved):
        raise SystemExit(f"error: refusing to clean unsafe output directory: {resolved}")
    shutil.rmtree(resolved)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--onefile", action="store_true", help="build a single executable")
    parser.add_argument("--no-zip", action="store_true", help="skip the portable zip archive")
    parser.add_argument("--lto", action="store_true", help="enable link-time optimisation")
    parser.add_argument("--debug", action="store_true", help="pass --debug to Nuitka")
    parser.add_argument(
        "--jobs",
        type=int,
        default=os.cpu_count() or 4,
        help="parallel C compilation jobs",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_BUILD_DIR),
        help="Nuitka intermediate directory (default: build/nuitka)",
    )
    parser.add_argument(
        "--release-dir",
        default=str(DEFAULT_RELEASE_DIR),
        help="portable folder and zip directory (default: release)",
    )
    parser.add_argument("--clean", action="store_true", help="remove the output directory first")
    parser.add_argument("--dry-run", action="store_true", help="print the command and exit")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    version = load_version()
    command = build_command(args, version)

    print(f"PyProxySwitch {version} - Nuitka portable build ({platform_tag()})")
    print(subprocess.list2cmdline(command))
    if args.dry_run:
        return

    validate_build_environment()
    output_dir = Path(args.output_dir).resolve()
    if args.clean and output_dir.exists():
        clean_output_directory(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(command, cwd=REPO_ROOT, check=True)
    staging = stage_portable_build(args, version)
    if not args.no_zip:
        create_portable_zip(staging)


if __name__ == "__main__":
    main()
