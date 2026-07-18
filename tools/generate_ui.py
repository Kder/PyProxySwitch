#!/usr/bin/env python3
"""Regenerate the Python modules produced from Qt Designer UI files."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESOURCE_DIR = PROJECT_ROOT / "pyproxyswitch" / "resources"
UI_MODULES = (
    ("add_proxy.ui", "add_proxy_ui.py"),
    ("pps_conf.ui", "pps_conf_ui.py"),
)
UIC_VERSION_PATTERN = re.compile(
    r"^## Created by: Qt User Interface Compiler version .+$", re.MULTILINE
)
STABLE_GENERATOR_HEADER = "## Created by: Qt User Interface Compiler"


def find_pyside6_uic() -> str:
    """Find the pyside6-uic executable belonging to the active Python."""

    executable_name = "pyside6-uic.exe" if os.name == "nt" else "pyside6-uic"
    scripts_dir = sysconfig.get_path("scripts")
    if scripts_dir:
        candidate = Path(scripts_dir) / executable_name
        if candidate.is_file():
            return str(candidate)

    executable = shutil.which("pyside6-uic")
    if executable:
        return executable

    raise FileNotFoundError(
        "pyside6-uic was not found. Install the project dependencies with "
        f"{Path(sys.executable).name} -m pip install -e ."
    )


def normalize_generated_module(content: bytes) -> bytes:
    """Remove platform and tool-version noise from generated Python modules."""

    text = content.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return UIC_VERSION_PATTERN.sub(STABLE_GENERATOR_HEADER, text).encode("utf-8")


def generate_ui_modules(*, check: bool = False) -> bool:
    """Generate all UI modules, or check whether tracked modules are current."""

    uic = find_pyside6_uic()
    stale: list[Path] = []
    generated_count = 0

    with tempfile.TemporaryDirectory(prefix=".ui-build-", dir=RESOURCE_DIR) as temp_dir:
        temporary_dir = Path(temp_dir)
        for source_name, destination_name in UI_MODULES:
            generated = temporary_dir / destination_name
            destination = RESOURCE_DIR / destination_name
            subprocess.run(
                [uic, "-o", str(generated), source_name],
                cwd=RESOURCE_DIR,
                check=True,
            )
            generated_bytes = normalize_generated_module(generated.read_bytes())
            generated.write_bytes(generated_bytes)

            if (
                destination.exists()
                and generated_bytes == normalize_generated_module(destination.read_bytes())
            ):
                continue

            if check:
                stale.append(destination)
            else:
                os.replace(generated, destination)
                generated_count += 1
                print(f"Generated {destination.relative_to(PROJECT_ROOT)}")

    if stale:
        for destination in stale:
            print(
                f"Out of date: {destination.relative_to(PROJECT_ROOT)}",
                file=sys.stderr,
            )
        return False

    if check:
        print("UI modules are up to date.")
    elif generated_count == 0:
        print("UI modules are already up to date.")
    return True


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate PySide6 Python modules from the project's .ui files."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="check generated modules without modifying them",
    )
    return parser


def main() -> int:
    args = create_parser().parse_args()
    try:
        return 0 if generate_ui_modules(check=args.check) else 1
    except (FileNotFoundError, OSError, subprocess.CalledProcessError) as exc:
        print(f"Failed to generate UI modules: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
