"""Read and write the user-maintained upstream proxy list."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import TypeAlias

from .proxy_validation import BatchImportValidator, ValidationError

ProxyEntry: TypeAlias = tuple[str, str, str, str, str, str]


def load_proxy_list(path: str | Path) -> list[ProxyEntry]:
    """Load valid proxy entries from *path*."""

    entries: list[ProxyEntry] = []
    with Path(path).open(encoding="utf-8") as proxy_file:
        for line in proxy_file:
            try:
                entry = BatchImportValidator.parse_proxy_line(line)
            except (IndexError, ValidationError):
                continue
            if entry is not None:
                entries.append(entry)
    return entries


def format_proxy(entry: Sequence[str]) -> str:
    """Serialize one six-field proxy entry to the editable text format."""

    if len(entry) != 6:
        raise ValueError("A proxy entry must contain exactly six fields")

    name, address, port, proxy_type, username, password = map(str, entry)
    parts = [name, f"{address}:{port}"]
    if username or password:
        parts.append(f"{username}:{password}")
    if proxy_type.upper() != "HTTP":
        parts.append(proxy_type.upper())
    return " ".join(parts)


def save_proxy_list(proxies: Iterable[Sequence[str]], path: str | Path) -> None:
    """Replace *path* with the supplied proxy entries."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(f"{format_proxy(proxy)}\n" for proxy in proxies)
    destination.write_text(content, encoding="utf-8")


__all__ = ["ProxyEntry", "format_proxy", "load_proxy_list", "save_proxy_list"]
