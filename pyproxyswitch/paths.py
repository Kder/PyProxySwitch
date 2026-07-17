"""Filesystem locations used by PyProxySwitch.

Packaged resources are read from the installed package. Mutable application
state is kept in per-user directories so a wheel installation never needs to
write to ``site-packages``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from platformdirs import PlatformDirs

APP_NAME = "PyProxySwitch"
APP_AUTHOR = "Kder"

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
I18N_DIR = DATA_DIR / "i18n"
DEFAULTS_DIR = DATA_DIR / "defaults"

_config_dirs = PlatformDirs(APP_NAME, APP_AUTHOR, roaming=True)
_local_dirs = PlatformDirs(APP_NAME, APP_AUTHOR)

USER_CONFIG_DIR = Path(_config_dirs.user_config_dir)
USER_LOG_DIR = Path(_local_dirs.user_log_dir)
CONFIG_FILE = USER_CONFIG_DIR / "PPS.conf"
PROXY_LIST_FILE = USER_CONFIG_DIR / "proxy.txt"

DEFAULT_CONFIG_FILE = DEFAULTS_DIR / "PPS.conf"
DEFAULT_PROXY_LIST_FILE = DEFAULTS_DIR / "proxy.txt"


def initialize_user_config(
    config_file: Path = CONFIG_FILE,
    proxy_list_file: Path = PROXY_LIST_FILE,
) -> None:
    """Create missing user configuration files from packaged defaults.

    Existing files are never overwritten. Callers can catch ``OSError`` when
    running in an intentionally read-only environment and continue with their
    in-memory defaults.
    """

    for source, destination in (
        (DEFAULT_CONFIG_FILE, config_file),
        (DEFAULT_PROXY_LIST_FILE, proxy_list_file),
    ):
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
