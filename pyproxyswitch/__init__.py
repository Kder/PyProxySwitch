"""PyProxySwitch package."""

from __future__ import annotations

from ._version import __version__
from .native_proxy import NativeProxyServer, Upstream

__author__ = "Kder"
__description__ = "PyProxySwitch - native Python proxy switcher"

__all__ = [
    "NativeProxyServer",
    "Upstream",
    "__version__",
    "__author__",
    "__description__",
]
