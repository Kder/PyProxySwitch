import os
import socket
import sys

import pytest

from pyproxyswitch.port_diagnostics import (
    find_port_owner,
    parse_proc_net_tcp,
    proc_address_matches,
)

# 0x1F90 = 8080 LISTEN on 127.0.0.1, 0x50 = 80 LISTEN on 0.0.0.0,
# plus an ESTABLISHED entry that must be ignored.
PROC_NET_TCP_SAMPLE = """  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
   0: 0100007F:1F90 00000000:0000 0A 00000000:00000000 00:00000000 00000000  1000        0 123456 1 0000000000000000 100 0 0 10 0
   1: 00000000:0050 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 234567 1 0000000000000000 100 0 0 10 0
   2: 0100007F:0025 0100007F:9C40 01 00000000:00000000 00:00000000 00000000  1000        0 345678 1 0000000000000000 100 0 0 10 0
"""

PROC_NET_TCP6_SAMPLE = """  sl  local_address                         remote_address                        st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
   0: 00000000000000000000000001000000:1F90 00000000000000000000000000000000:0000 0A 00000000:00000000 00:00000000 00000000  1000        0 456789 1 0000000000000000 100 0 0 10 0
"""


def test_parse_proc_net_tcp_finds_listen_inode():
    assert parse_proc_net_tcp(PROC_NET_TCP_SAMPLE, 8080) == {"123456"}
    # The ESTABLISHED entry on port 25 (0x25) must be ignored.
    assert parse_proc_net_tcp(PROC_NET_TCP_SAMPLE, 25) == set()


def test_parse_proc_net_tcp_filters_by_host():
    assert parse_proc_net_tcp(PROC_NET_TCP_SAMPLE, 8080, "127.0.0.1") == {"123456"}
    assert parse_proc_net_tcp(PROC_NET_TCP_SAMPLE, 8080, "127.0.0.2") == set()
    # A wildcard listener conflicts with any bind address.
    assert parse_proc_net_tcp(PROC_NET_TCP_SAMPLE, 80, "127.0.0.1") == {"234567"}


def test_parse_proc_net_tcp6_loopback():
    assert parse_proc_net_tcp(PROC_NET_TCP6_SAMPLE, 8080, "::1", ipv6=True) == {"456789"}
    assert parse_proc_net_tcp(PROC_NET_TCP6_SAMPLE, 8080, "::2", ipv6=True) == set()


def test_proc_address_matches_wildcard_and_hostname():
    assert proc_address_matches("00000000", "192.168.1.5", ipv6=False)
    # Hostnames cannot be compared, so the candidate is kept.
    assert proc_address_matches("0100007F", "localhost", ipv6=False)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="requires /proc")
def test_find_port_owner_identifies_current_process():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    try:
        owner = find_port_owner(port, "127.0.0.1")
    finally:
        listener.close()
    assert owner is not None
    assert owner.pid == os.getpid()
    assert f"PID {os.getpid()}" in owner.describe()


def test_find_port_owner_returns_none_for_free_port():
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    free_port = probe.getsockname()[1]
    probe.close()

    assert find_port_owner(free_port, "127.0.0.1") is None
