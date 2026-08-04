"""Best-effort diagnostics that identify the process holding a TCP port.

No third-party dependencies: Linux parses ``/proc``, Windows falls back to
``netstat``/``tasklist`` and macOS to ``lsof``.  Every helper returns
``None`` on failure so a diagnostic gap never masks the original bind error.
"""

from __future__ import annotations

import csv
import ipaddress
import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path

_TCP_LISTEN_STATE = "0A"
_WILDCARD_HOSTS = {"0.0.0.0", "::", "[::]"}
_SUBPROCESS_TIMEOUT = 10
# Avoid a console window flash when the frozen GUI spawns helper tools.
_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass(frozen=True)
class PortOwner:
    """The process holding a port, when it can be identified."""

    pid: int
    name: str

    def describe(self) -> str:
        """Return a language-neutral ``name (PID n)`` description."""

        return f"{self.name} (PID {self.pid})"


def find_port_owner(port: int, host: str | None = None) -> PortOwner | None:
    """Return the process listening on ``host:port``, or ``None``."""

    try:
        # platform.system() is used instead of sys.platform so static
        # analysis keeps every branch reachable on any host OS.
        system = platform.system()
        if system == "Linux":
            return _find_port_owner_linux(port, host)
        if system == "Windows":
            return _find_port_owner_windows(port, host)
        if system == "Darwin":
            return _find_port_owner_lsof(port, host)
    except Exception:
        return None
    return None


# --------------------------------------------------------------------- Linux


def _find_port_owner_linux(port: int, host: str | None) -> PortOwner | None:
    inodes: set[str] = set()
    for table, ipv6 in (("/proc/net/tcp", False), ("/proc/net/tcp6", True)):
        try:
            text = Path(table).read_text(encoding="ascii")
        except OSError:
            continue
        inodes.update(parse_proc_net_tcp(text, port, host, ipv6=ipv6))
    if not inodes:
        return None
    owners = _pids_for_socket_inodes(inodes)
    return owners[0] if owners else None


def parse_proc_net_tcp(
    text: str,
    port: int,
    host: str | None = None,
    *,
    ipv6: bool = False,
) -> set[str]:
    """Return the socket inodes LISTENing on *port* in /proc/net/tcp* content."""

    inodes: set[str] = set()
    for line in text.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 10:
            continue
        local_address, state, inode = fields[1], fields[3], fields[9]
        if state != _TCP_LISTEN_STATE:
            continue
        address_hex, _, port_hex = local_address.rpartition(":")
        try:
            local_port = int(port_hex, 16)
        except ValueError:
            continue
        if local_port != port:
            continue
        if host is not None and not proc_address_matches(address_hex, host, ipv6=ipv6):
            continue
        inodes.add(inode)
    return inodes


def proc_address_matches(address_hex: str, host: str, *, ipv6: bool) -> bool:
    """Return whether a /proc hex address can serve clients bound to *host*."""

    if set(address_hex) == {"0"}:
        return True  # wildcard listener conflicts with any bind address
    try:
        packed = ipaddress.ip_address(host).packed
    except ValueError:
        return True  # hostnames cannot be compared; keep the candidate
    if ipv6:
        if len(packed) != 16:
            return False
        # /proc/net/tcp6 stores four little-endian 32-bit words.
        expected = "".join(packed[i : i + 4][::-1].hex() for i in range(0, 16, 4))
    else:
        if len(packed) != 4:
            return False
        expected = packed[::-1].hex()
    return expected.upper() == address_hex.upper()


def _pids_for_socket_inodes(inodes: set[str], proc: str = "/proc") -> list[PortOwner]:
    targets = {f"socket:[{inode}]" for inode in inodes}
    owners: list[PortOwner] = []
    try:
        entries = os.listdir(proc)
    except OSError:
        return owners
    for entry in entries:
        if not entry.isdigit():
            continue
        fd_dir = os.path.join(proc, entry, "fd")
        try:
            fds = os.listdir(fd_dir)
        except OSError:
            continue  # owned by another user or already gone
        for fd in fds:
            try:
                if os.readlink(os.path.join(fd_dir, fd)) in targets:
                    owners.append(PortOwner(int(entry), _linux_process_name(proc, entry)))
                    break
            except OSError:
                continue
    return owners


def _linux_process_name(proc: str, pid_text: str) -> str:
    try:
        return (Path(proc) / pid_text / "comm").read_text(encoding="utf-8").strip()
    except OSError:
        return f"pid {pid_text}"


# ------------------------------------------------------------------- Windows


def _find_port_owner_windows(port: int, host: str | None) -> PortOwner | None:
    output = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        timeout=_SUBPROCESS_TIMEOUT,
        creationflags=_CREATE_NO_WINDOW,
    ).stdout
    fallback: int | None = None
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 4 or fields[0].upper() != "TCP":
            continue
        local_address, _, local_port = fields[1].rpartition(":")
        if local_port != str(port):
            continue
        pid_text = fields[-1]
        if not pid_text.isdigit():
            continue
        pid = int(pid_text)
        if pid <= 0:
            continue
        if host is not None and host not in _WILDCARD_HOSTS:
            address = local_address.strip("[]")
            if address != host and address not in _WILDCARD_HOSTS:
                continue
        # Prefer a LISTENING entry but accept any entry as a fallback.
        if any(field.upper().startswith("LISTEN") for field in fields[2:-1]):
            return PortOwner(pid, _windows_process_name(pid))
        fallback = fallback if fallback is not None else pid
    if fallback is not None:
        return PortOwner(fallback, _windows_process_name(fallback))
    return None


def _windows_process_name(pid: int) -> str:
    try:
        output = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT,
            creationflags=_CREATE_NO_WINDOW,
        ).stdout
        row = next(csv.reader(output.splitlines()))
        if row:
            return row[0]
    except (OSError, StopIteration, subprocess.SubprocessError):
        pass
    return f"pid {pid}"


# --------------------------------------------------------------------- macOS


def _find_port_owner_lsof(port: int, host: str | None) -> PortOwner | None:
    # lsof ORs multiple -i selectors, so the host cannot be filtered safely;
    # a same-port listener on another interface is an acceptable report here.
    del host
    args = ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-Fpc"]
    try:
        output = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT,
        ).stdout
    except OSError:
        return None  # lsof is unavailable
    pid: int | None = None
    name: str | None = None
    for line in output.splitlines():
        if line.startswith("p") and line[1:].isdigit():
            if pid is not None:
                break  # only the first process is reported
            pid = int(line[1:])
        elif line.startswith("c") and pid is not None and name is None:
            name = line[1:]
    if pid is None:
        return None
    return PortOwner(pid, name or f"pid {pid}")


__all__ = ["PortOwner", "find_port_owner", "parse_proc_net_tcp", "proc_address_matches"]
