"""Command-line entry point for PyProxySwitch."""

from __future__ import annotations

import sys

from .cli import create_parser
from .cli import main as _cli_main

__all__ = ["create_parser", "main"]


def main() -> None:
    sys.exit(_cli_main())


if __name__ == "__main__":
    main()
