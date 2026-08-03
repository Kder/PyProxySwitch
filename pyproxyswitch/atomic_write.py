"""Crash-safe helpers for replacing small UTF-8 application data files."""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path


def atomic_write_text(path: str | Path, content: str, *, encoding: str = "utf-8") -> None:
    """Write *content* and atomically replace *path* only after a successful flush."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing_mode = destination.stat().st_mode & 0o7777
    except FileNotFoundError:
        existing_mode = None
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding=encoding, newline="") as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        if existing_mode is not None:
            # mkstemp creates 0600 files; preserve the permissions the
            # destination had so configuration stays readable by the user.
            os.chmod(temporary_path, existing_mode)
        os.replace(temporary_path, destination)
        _fsync_directory(destination.parent)
    except BaseException:
        with contextlib.suppress(OSError):
            temporary_path.unlink()
        raise


def _fsync_directory(directory: Path) -> None:
    """Persist the rename in case of a crash right after os.replace()."""

    with contextlib.suppress(OSError):
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


__all__ = ["atomic_write_text"]
