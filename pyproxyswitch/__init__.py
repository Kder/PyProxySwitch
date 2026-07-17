"""PyProxySwitch package.

The native proxy core stays importable without PySide6.  GUI/configuration
helpers are loaded lazily for compatibility with the package-level API used by
older releases.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .logger_config import setup_logger
from .native_proxy import NativeProxyServer, Upstream

__version__ = "4.0.0"
__author__ = "Kder"
__description__ = "PyProxySwitch - native Python proxy switcher"

_PPS_EXPORTS = {
    "add_proxy",
    "del_proxy",
    "pps_exc_handle",
    "pps_load_proxylist",
    "pps_loadcfg",
    "pps_output",
    "pps_save_proxylist",
    "pps_savecfg",
}
_VALIDATION_EXPORTS = {"BatchImportValidator", "ProxyValidator"}


def __getattr__(name: str) -> Any:
    if name in _PPS_EXPORTS:
        return getattr(import_module(".pps_config", __name__), name)
    if name in _VALIDATION_EXPORTS:
        return getattr(import_module(".proxy_validation", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "setup_logger",
    "ProxyValidator",
    "BatchImportValidator",
    "NativeProxyServer",
    "Upstream",
    "pps_loadcfg",
    "pps_savecfg",
    "pps_output",
    "pps_exc_handle",
    "pps_load_proxylist",
    "pps_save_proxylist",
    "add_proxy",
    "del_proxy",
    "__version__",
    "__author__",
    "__description__",
]
