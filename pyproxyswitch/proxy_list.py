"""Read and write the user-maintained upstream proxy list."""

from __future__ import annotations

import logging
import shlex
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import TypeAlias

from .proxy_validation import BatchImportValidator, ValidationError

ProxyEntry: TypeAlias = tuple[str, str, str, str, str, str]
logger = logging.getLogger("PyProxySwitch")


def load_proxy_list(path: str | Path) -> list[ProxyEntry]:
    """Load valid proxy entries from *path*."""

    entries: list[ProxyEntry] = []
    names: set[str] = set()
    validator = BatchImportValidator()
    with Path(path).open(encoding="utf-8") as proxy_file:
        for line_number, line in enumerate(proxy_file, 1):
            try:
                validated = validator.validate_batch_line(line, line_number)
            except ValidationError as exc:
                logger.warning("Skipping invalid proxy-list entry: %s", exc)
                continue
            if validated is None:
                continue
            name, address, port, proxy_type, username, password = validated
            if name in names:
                logger.warning("Skipping duplicate proxy-list entry %r", name)
                continue
            names.add(name)
            entries.append((name, address, str(port), proxy_type, username, password))
    return entries


def format_proxy(entry: Sequence[str]) -> str:
    """Serialize one six-field proxy entry to the editable text format."""

    if len(entry) != 6:
        raise ValueError("A proxy entry must contain exactly six fields")

    name, address, port, proxy_type, username, password = map(str, entry)
    if any("\n" in value or "\r" in value for value in (name, address, username, password)):
        raise ValueError("Proxy fields cannot contain line breaks")
    parts = [name, f"{address}:{port}"]
    if username or password:
        parts.append(f"{username}:{password}")
    if proxy_type.upper() != "HTTP":
        parts.append(proxy_type.upper())
    return shlex.join(parts)


def save_proxy_list(proxies: Iterable[Sequence[str]], path: str | Path) -> None:
    """Replace *path* with the supplied proxy entries."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(f"{format_proxy(proxy)}\n" for proxy in proxies)
    destination.write_text(content, encoding="utf-8")


__all__ = ["ProxyEntry", "format_proxy", "load_proxy_list", "save_proxy_list"]
