#!/usr/bin/env python3
"""Update and compile the project's Qt translations on any supported platform."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
I18N_DIR = PROJECT_ROOT / "i18n"
COMPILED_DIR = PROJECT_ROOT / "pyproxyswitch" / "data" / "i18n"
SOURCE_PATHS = (
    PROJECT_ROOT / "pyproxyswitch" / "gui",
    PROJECT_ROOT / "pyproxyswitch" / "resources" / "add_proxy.ui",
    PROJECT_ROOT / "pyproxyswitch" / "resources" / "pps_conf.ui",
)
TRANSLATIONS = (
    ("zh_CN.ts", "zh_CN.qm"),
    ("en.ts", "en.qm"),
)

MESSAGE_PATTERN = re.compile(r"<message(?:\s[^>]*)?>.*?</message>", re.DOTALL)
SOURCE_PATTERN = re.compile(r"<source(?:\s[^>]*)?>(.*?)</source>", re.DOTALL)
TRANSLATION_PATTERN = re.compile(
    r"<translation(?P<self_attrs>[^>]*)\s*/>"
    r"|<translation(?P<attrs>[^>]*)>(?P<body>.*?)</translation>",
    re.DOTALL,
)
UNFINISHED_ATTRIBUTE_PATTERN = re.compile(r"\s+type=(['\"])unfinished\1")


def find_pyside6_tool(tool_name: str) -> str:
    """Find a PySide6 command belonging to the active Python environment."""

    executable_name = f"{tool_name}.exe" if os.name == "nt" else tool_name
    scripts_dir = sysconfig.get_path("scripts")
    if scripts_dir:
        candidate = Path(scripts_dir) / executable_name
        if candidate.is_file():
            return str(candidate)

    executable = shutil.which(tool_name)
    if executable:
        return executable

    raise FileNotFoundError(
        f"{tool_name} was not found. Install the project dependencies with "
        f"{Path(sys.executable).name} -m pip install -e ."
    )


def update_translation_sources(output_dir: Path) -> None:
    """Merge translatable strings from Python and Qt Designer sources into TS files."""

    lupdate = find_pyside6_tool("pyside6-lupdate")
    ts_paths = [output_dir / ts_name for ts_name, _ in TRANSLATIONS]
    subprocess.run(
        [
            lupdate,
            "-no-obsolete",
            "-extensions",
            "py,ui",
            *(str(path) for path in SOURCE_PATHS),
            "-ts",
            *(str(path) for path in ts_paths),
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )


def complete_english_translations(ts_path: Path) -> int:
    """Use source text for empty English translations without reformatting the TS file."""

    document = ts_path.read_text(encoding="utf-8")
    completed_count = 0

    def complete_message(match: re.Match[str]) -> str:
        nonlocal completed_count
        message_xml = match.group(0)
        message = ET.fromstring(message_xml)
        translation = message.find("translation")
        if translation is None:
            return message_xml

        is_empty = not "".join(translation.itertext()).strip()
        if translation.get("type") != "unfinished" and not is_empty:
            return message_xml

        source_match = SOURCE_PATTERN.search(message_xml)
        translation_match = TRANSLATION_PATTERN.search(message_xml)
        if source_match is None or translation_match is None:
            return message_xml

        attrs = translation_match.group("attrs")
        if attrs is None:
            attrs = translation_match.group("self_attrs") or ""
        attrs = UNFINISHED_ATTRIBUTE_PATTERN.sub("", attrs)
        replacement = f"<translation{attrs}>{source_match.group(1)}</translation>"
        completed_count += 1
        return (
            message_xml[: translation_match.start()]
            + replacement
            + message_xml[translation_match.end() :]
        )

    updated_document = MESSAGE_PATTERN.sub(complete_message, document)
    if updated_document != document:
        ts_path.write_text(updated_document, encoding="utf-8", newline="")
    return completed_count


def compile_translations(source_dir: Path, output_dir: Path) -> None:
    """Compile every TS source into the QM file loaded by the application."""

    lrelease = find_pyside6_tool("pyside6-lrelease")
    output_dir.mkdir(parents=True, exist_ok=True)
    for ts_name, qm_name in TRANSLATIONS:
        subprocess.run(
            [lrelease, str(source_dir / ts_name), "-qm", str(output_dir / qm_name)],
            cwd=PROJECT_ROOT,
            check=True,
        )


def check_generated_translations() -> bool:
    """Return whether tracked TS and QM files match freshly generated files."""

    stale: list[Path] = []
    with tempfile.TemporaryDirectory(prefix=".i18n-build-", dir=PROJECT_ROOT) as temp_dir:
        temporary_dir = Path(temp_dir)
        for ts_name, _ in TRANSLATIONS:
            source = I18N_DIR / ts_name
            if source.is_file():
                shutil.copy2(source, temporary_dir / ts_name)

        update_translation_sources(temporary_dir)
        complete_english_translations(temporary_dir / "en.ts")
        compile_translations(temporary_dir, temporary_dir)

        for ts_name, qm_name in TRANSLATIONS:
            for generated, tracked in (
                (temporary_dir / ts_name, I18N_DIR / ts_name),
                (temporary_dir / qm_name, COMPILED_DIR / qm_name),
            ):
                if not tracked.is_file() or generated.read_bytes() != tracked.read_bytes():
                    stale.append(tracked)

    if stale:
        for path in stale:
            print(f"Out of date: {path.relative_to(PROJECT_ROOT)}", file=sys.stderr)
        return False

    print("Translation sources and compiled catalogs are up to date.")
    return True


def generate_translations(action: str) -> None:
    """Run the requested translation generation stage."""

    if action in {"all", "update"}:
        update_translation_sources(I18N_DIR)
        completed_count = complete_english_translations(I18N_DIR / "en.ts")
        print(f"Completed {completed_count} English translation(s) from source text.")
    if action in {"all", "compile"}:
        compile_translations(I18N_DIR, COMPILED_DIR)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Update Qt TS sources and compile the project's QM translation catalogs."
    )
    parser.add_argument(
        "action",
        nargs="?",
        choices=("all", "update", "compile"),
        default="all",
        help="generation stage to run (default: all)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="check all generated translation files without modifying them",
    )
    return parser


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()
    if args.check and args.action != "all":
        parser.error("--check cannot be combined with an action")

    try:
        if args.check:
            return 0 if check_generated_translations() else 1
        generate_translations(args.action)
    except (ET.ParseError, FileNotFoundError, OSError, subprocess.CalledProcessError) as exc:
        print(f"Failed to generate translations: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
