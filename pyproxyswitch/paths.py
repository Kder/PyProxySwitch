"""Filesystem locations used by PyProxySwitch.

Packaged resources are read from the installed package. Mutable application
state is kept in per-user directories so a wheel installation never needs to
write to ``site-packages``.

Runtime directories are resolved with the following precedence:

1. ``PYPROXYSWITCH_HOME`` environment variable. Configuration files live
   directly in that directory and logs in its ``logs`` subdirectory.
2. A ``portable.ini`` file next to a frozen executable. Configuration files
   then live in ``config`` and logs in ``logs`` next to the executable.
3. The operating system's per-user directories, resolved by ``platformdirs``.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from platformdirs import PlatformDirs

APP_NAME = "PyProxySwitch"
APP_AUTHOR = "Kder"

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
I18N_DIR = DATA_DIR / "i18n"
DEFAULTS_DIR = DATA_DIR / "defaults"

ENV_HOME = "PYPROXYSWITCH_HOME"
PORTABLE_MARKER = "portable.ini"


def _is_frozen() -> bool:
    """Return whether the application is running as a bundled executable."""

    return bool(getattr(sys, "frozen", False)) or "__compiled__" in globals()


def _resolve_runtime_dirs() -> tuple[Path, Path, str]:
    """Return ``(config_dir, log_dir, source)`` using portable precedence."""

    env_home = os.environ.get(ENV_HOME, "").strip()
    if env_home:
        home = Path(env_home).expanduser().resolve()
        return home, home / "logs", "environment"

    if _is_frozen():
        executable_dir = Path(sys.executable).resolve().parent
        if (executable_dir / PORTABLE_MARKER).is_file():
            return executable_dir / "config", executable_dir / "logs", "portable"

    config_dirs = PlatformDirs(APP_NAME, APP_AUTHOR, roaming=True)
    local_dirs = PlatformDirs(APP_NAME, APP_AUTHOR)
    return Path(config_dirs.user_config_dir), Path(local_dirs.user_log_dir), "user"


USER_CONFIG_DIR, USER_LOG_DIR, PATHS_SOURCE = _resolve_runtime_dirs()
PORTABLE_MODE = PATHS_SOURCE != "user"
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
