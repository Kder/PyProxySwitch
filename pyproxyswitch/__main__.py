#!/usr/bin/env python

# Copyright 2009-2026 Kder Lin
#
# Licensed under the Apache License, 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

"""
PyProxySwitch CLI Entry Point

This module provides command-line interface for PyProxySwitch.
"""

import sys
import argparse
from . import __version__


def create_parser():
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="PyProxySwitch - Cross-platform proxy switcher",
        prog="pyproxyswitch"
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'PyProxySwitch {__version__}'
    )

    parser.add_argument(
        '--gui',
        action='store_true',
        help='Launch GUI application (default behavior)'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )

    return parser


def main():
    """CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()

    # For now, always launch GUI
    # In the future, we could add CLI-only functionality
    try:
        from .main import main as gui_main
        gui_main(log_level=args.log_level)
    except ImportError as e:
        print(f"Error: Failed to import GUI module: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()