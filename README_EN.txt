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

Installation
============

Install from PyPI:

    pip install PyProxySwitch

For an isolated environment with globally available commands, pipx is
recommended:

    pipx install PyProxySwitch

You can also install directly from the repository:

    pip install git+https://github.com/Kder/PyProxySwitch.git

After installation, run `pyproxyswitch` for the GUI or `pyproxyswitch-cli`
for the command-line interface.

Uninstallation
==============

    pip uninstall PyProxySwitch
    # If installed with pipx:
    pipx uninstall PyProxySwitch

Uninstallation removes the application and its command entry points. Following
normal Python application conventions, user data is retained. For a complete
cleanup, remove these directories manually:

* Windows configuration: `%APPDATA%\Kder\PyProxySwitch` (`PPS.conf` and
  `proxy.txt`)
* Windows logs: `%LOCALAPPDATA%\Kder\PyProxySwitch` (or the directory selected
  by `LOG_PATH` in `PPS.conf`)
* Linux: `~/.config/PyProxySwitch` and
  `~/.local/state/PyProxySwitch/log`
* macOS: `~/Library/Application Support/PyProxySwitch` and
  `~/Library/Logs/PyProxySwitch`

When installed with pip rather than pipx, dependencies such as PySide6 and
platformdirs are also retained; uninstall them separately if no longer needed.

Portable mode
=============

Portable mode keeps configuration and logs inside the application directory
and does not write application data to per-user system directories. To
uninstall it, delete the application folder.

* Nuitka build: run
  `uv run --group build python tools/build_nuitka.py`; uv installs Nuitka
  from the project's `build` dependency group and produces a portable zip.
  On Windows the default is a one-directory executable build. Nuitka
  intermediates are written to `build/nuitka/`, while distributable folders
  and zips are written to `release/`; `dist/` remains reserved for Python
  sdists and wheels. The included `portable.ini` marker stores configuration
  in `config/` and logs in `logs/` next to the executable. Delete
  `portable.ini` to restore per-user storage.
* Environment override: for source, pip, or executable runs, set
  `PYPROXYSWITCH_HOME` to the portable directory. `PPS.conf`, `proxy.txt`, and
  `logs/` will all be stored there.

The precedence is `PYPROXYSWITCH_HOME`, then `portable.ini` for frozen
executables, then the operating system's per-user directories.

Run `python PyProxySwitch.py`, point an application's HTTP or SOCKS proxy to
127.0.0.1:8888, then choose an upstream from the system tray. The default bind
address is loopback-only for safety.

Wheel installations store `PPS.conf` and `proxy.txt` in the current user's
configuration directory, and logs in the current user's log directory. On
Windows these are under the user's AppData folders, not site-packages.

Requirements: Python 3.11+, PySide6 and platformdirs. The proxy protocol core
itself uses only the Python standard library.

Maintainer setup, generation, validation, build, and release commands are
centralized in `RELEASING.md`.

After changing a Qt Designer file under pyproxyswitch/resources, run
`python tools/generate_ui.py`. Use `python tools/generate_ui.py --check` to
verify that the tracked Python modules are current.

Run `python tools/generate_i18n.py update` to update the Qt TS translation
sources from Python and UI files, then run `python tools/generate_i18n.py
compile` after editing translations to build the QM catalogs used by the
application. Running the script without an action performs both stages, and
`python tools/generate_i18n.py --check` verifies every generated translation
file. Both generators use the PySide6 tools from the active Python environment
and work on Windows, Linux and macOS.

Author: Kder <kderlin (#) gmail dot com>
Project Website: http://pyproxyswitch.kder.info
Changelog: CHANGELOG.md
License: Apache License, Version 2.0
