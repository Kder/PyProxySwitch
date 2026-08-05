"""Connectivity probe for configured upstream proxies.

The probe reuses the native server's upstream handshake: it opens a tunnel
through the candidate upstream to a fixed, trivial target and closes it
immediately.  A single code path therefore validates reachability,
authentication, and protocol conformance for HTTP, SOCKS4 and SOCKS5.
"""

from __future__ import annotations

import asyncio
import logging

from pyproxyswitch.native_proxy import NativeProxyServer, Upstream

logger = logging.getLogger("PyProxySwitch")

# Only a tunnel is established; no data ever flows to the target.
TEST_TARGET = ("www.gstatic.com", 80)


def check_proxy(
    host: str,
    port: int,
    proxy_type: str,
    username: str = "",
    password: str = "",
    *,
    timeout: float = 15.0,
    target: tuple[str, int] = TEST_TARGET,
) -> bool:
    """Return whether a tunnel can be established through the upstream."""

    try:
        asyncio.run(
            _check(host, port, proxy_type, username, password, timeout=timeout, target=target)
        )
    except Exception as exc:
        logger.debug("Connectivity check failed for %s:%s: %s", host, port, exc)
        return False
    return True


async def _check(
    host: str,
    port: int,
    proxy_type: str,
    username: str,
    password: str,
    *,
    timeout: float,
    target: tuple[str, int],
) -> None:
    # The server instance is never started; only its upstream handshake is used.
    server = NativeProxyServer(connect_timeout=timeout)
    upstream = Upstream(
        name="connectivity-check",
        proxy_type=proxy_type,
        host=host,
        port=port,
        username=username,
        password=password,
    )
    _, writer, _ = await server._open_tunnel(target[0], target[1], upstream)
    await server._close_writer(writer)


__all__ = ["TEST_TARGET", "check_proxy"]
