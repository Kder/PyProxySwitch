"""GUI boundary for rendering coded application errors."""

from __future__ import annotations

from pyproxyswitch.config import ConfigManager
from pyproxyswitch.errors import format_user_error


def localized_error_message(
    error: object,
    language: str | None = None,
) -> str:
    """Render an error using the active application language."""

    selected_language = language
    if selected_language is None:
        selected_language = str(ConfigManager().get("LANG", "zh_CN"))
    return format_user_error(error, selected_language)


__all__ = ["localized_error_message"]
