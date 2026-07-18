"""Command-line entry point for PyProxySwitch."""

from __future__ import annotations

import argparse

from . import __version__


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PyProxySwitch - cross-platform proxy switcher",
        prog="pyproxyswitch",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"PyProxySwitch {__version__}",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="override the configured logging level",
    )
    return parser


def main() -> None:
    args = create_parser().parse_args()
    from .main import main as gui_main

    gui_main(log_level=args.log_level)


if __name__ == "__main__":
    main()
