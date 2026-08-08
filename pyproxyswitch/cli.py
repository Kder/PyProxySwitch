"""Command-line interface for PyProxySwitch."""

from __future__ import annotations

import argparse
import contextlib
import sys
import threading

from . import __version__
from .config import ConfigManager
from .errors import LocalizedError, format_cli_error
from .logger_config import setup_logger
from .proxy_manager import ProxyManager
from .proxy_validation import ProxyValidator


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PyProxySwitch - cross-platform proxy switcher",
        prog="pyproxyswitch",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"PyProxySwitch {__version__}",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="override the configured logging level",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list", help="list configured proxies")
    subparsers.add_parser("current", help="show the selected proxy and listener address")

    use_parser = subparsers.add_parser("use", help="select a proxy for the next start")
    use_parser.add_argument("name", help="proxy name, or NoProxy for a direct connection")

    add_parser = subparsers.add_parser("add", help="add a proxy")
    add_parser.add_argument("--name", required=True)
    add_parser.add_argument("--address", required=True)
    add_parser.add_argument("--port", required=True)
    add_parser.add_argument("--type", default="HTTP", help="HTTP, SOCKS4 or SOCKS5")
    add_parser.add_argument("--user", default="")
    add_parser.add_argument("--password", default="")

    del_parser = subparsers.add_parser("del", help="delete a proxy")
    del_parser.add_argument("name")

    start_parser = subparsers.add_parser(
        "start", help="run the local listener in the foreground"
    )
    start_parser.add_argument("name", nargs="?", help="defaults to the selected proxy")
    return parser


def _resolve_current_name(config: ConfigManager) -> str:
    """Mirror the GUI selection fallback: LAST_ITEM, DEFAULT_ITEM, then NoProxy."""

    names = config.get_proxy_names()
    for candidate in (config.get("LAST_ITEM"), config.get("DEFAULT_ITEM")):
        if candidate == "NoProxy" or candidate in names:
            return str(candidate)
    return "NoProxy"


def _cmd_list(config: ConfigManager) -> int:
    current = _resolve_current_name(config)
    for name, host, port, kind, user, _password in config.get_proxies():
        marker = "*" if name == current else " "
        auth = f" (user: {user})" if user else ""
        print(f"{marker} {name}\t{kind}\t{host}:{port}{auth}")
    if current == "NoProxy":
        print("* NoProxy (direct connection)")
    return 0


def _cmd_current(config: ConfigManager) -> int:
    print(f"Selected: {_resolve_current_name(config)}")
    print(f"Listener: {config.get('LOCAL_ADDRESS')}:{config.get('LOCAL_PORT')}")
    return 0


def _cmd_use(config: ConfigManager, name: str) -> int:
    if name != "NoProxy" and name not in config.get_proxy_names():
        print(f"Error: no proxy named {name!r}", file=sys.stderr)
        return 1
    config.set("LAST_ITEM", name)
    if not config.save():
        print("Error: failed to save configuration", file=sys.stderr)
        return 1
    print(f"Selected proxy: {name}")
    return 0


def _cmd_add(config: ConfigManager, args: argparse.Namespace) -> int:
    validated = ProxyValidator().validate_full_proxy(
        args.name, args.address, args.port, args.type, args.user, args.password
    )
    if validated[0] in config.get_proxy_names():
        print(f"Error: a proxy named {validated[0]!r} already exists", file=sys.stderr)
        return 1
    proxies = [list(proxy) for proxy in config.get_proxies()]
    proxies.append([str(value) for value in validated])
    config.set_proxies(proxies)
    if not config.save_proxies():
        print("Error: failed to save proxy list", file=sys.stderr)
        return 1
    print(f"Added proxy: {validated[0]}")
    return 0


def _cmd_del(config: ConfigManager, name: str) -> int:
    proxies = config.get_proxies()
    remaining = [proxy for proxy in proxies if proxy[0] != name]
    if len(remaining) == len(proxies):
        print(f"Error: no proxy named {name!r}", file=sys.stderr)
        return 1
    config.set_proxies(remaining)
    if not config.save_proxies():
        print("Error: failed to save proxy list", file=sys.stderr)
        return 1
    print(f"Deleted proxy: {name}")
    return 0


def _wait_for_interrupt() -> None:
    """Block until the user interrupts the foreground listener."""

    with contextlib.suppress(KeyboardInterrupt):
        threading.Event().wait()


def _cmd_start(config: ConfigManager, name: str | None) -> int:
    name = name or _resolve_current_name(config)
    manager = ProxyManager(config)
    manager.start_proxy(name)
    server = manager.server
    if server is not None:
        print(f"Listening on {server.host}:{server.port}")
    print(f"Upstream: {manager.current_upstream.description}")
    print("Press Ctrl+C to stop.")
    _wait_for_interrupt()
    manager.stop_proxy()
    print("Listener stopped.")
    return 0


def main(argv: list[str] | None = None, config: ConfigManager | None = None) -> int:
    args = create_parser().parse_args(argv)
    if args.command is None:
        from .main import main as gui_main

        gui_main(log_level=args.log_level)
        return 0

    if args.log_level is not None:
        setup_logger(log_level=args.log_level)

    if config is None:
        config = ConfigManager()
    try:
        if args.command == "list":
            return _cmd_list(config)
        if args.command == "current":
            return _cmd_current(config)
        if args.command == "use":
            return _cmd_use(config, args.name)
        if args.command == "add":
            return _cmd_add(config, args)
        if args.command == "del":
            return _cmd_del(config, args.name)
        if args.command == "start":
            return _cmd_start(config, args.name)
    except LocalizedError as exc:
        language = str(config.get("LANG", "en"))
        print(format_cli_error(exc, language), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
