PyProxySwitch

PyProxySwitch is a cross-platform upstream proxy switcher written in Python
and PySide6. Its local proxy server is implemented entirely with the Python
standard library and does not launch or depend on 3proxy, polipo, IP Relay, or
another third-party proxy binary.

One local port accepts HTTP, SOCKS4/SOCKS4a and SOCKS5 clients. Configured
upstreams may use HTTP, SOCKS4 or SOCKS5, with HTTP Basic and SOCKS5
username/password authentication. NoProxy connects directly.

The native core proxies TCP traffic. It supports HTTP forwarding/CONNECT and
SOCKS CONNECT; SOCKS BIND, SOCKS5 UDP ASSOCIATE and content caching are not
implemented.

Changing the selected upstream atomically replaces an in-memory route. The
listening socket and event loop remain running; existing connections retain
their original route and new connections immediately use the new route.

Run `python PyProxySwitch.py`, point an application's HTTP or SOCKS proxy to
127.0.0.1:8888, then choose an upstream from the system tray. The default bind
address is loopback-only for safety.

Wheel installations store `PPS.conf` and `proxy.txt` in the current user's
configuration directory, and logs in the current user's log directory. On
Windows these are under the user's AppData folders, not site-packages.

Requirements: Python 3.10+, PySide6 and platformdirs. The proxy protocol core
itself uses only the Python standard library.

After changing a Qt Designer file under pyproxyswitch/resources, run
`python tools/generate_ui.py`. Use `python tools/generate_ui.py --check` to
verify that the tracked Python modules are current. The script works on
Windows, Linux and macOS.

Author: Kder <kderlin (#) gmail dot com>
Project Website: http://pyproxyswitch.kder.info
Last Update: 2026-07-18
License: Apache License, Version 2.0
