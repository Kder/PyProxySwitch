from pyproxyswitch import cli
from pyproxyswitch.__main__ import create_parser
from pyproxyswitch.config import ConfigManager


def _make_config(tmp_path, proxies=()):
    config = ConfigManager(
        config_path=tmp_path / "PPS.conf",
        proxy_list_path=tmp_path / "proxy.txt",
        use_singleton=False,
    )
    config.set_proxies(proxies)
    return config


def test_log_level_is_only_overridden_when_explicitly_requested() -> None:
    parser = create_parser()

    assert parser.parse_args([]).log_level is None
    assert parser.parse_args(["--log-level", "DEBUG"]).log_level == "DEBUG"


def test_explicit_log_level_applies_to_subcommands(tmp_path, monkeypatch) -> None:
    config = _make_config(tmp_path)
    calls: list[str] = []
    monkeypatch.setattr(cli, "setup_logger", lambda log_level: calls.append(log_level))

    assert cli.main(["--log-level", "DEBUG", "current"], config=config) == 0
    assert calls == ["DEBUG"]


def test_subcommands_without_log_level_do_not_configure_logger(tmp_path, monkeypatch) -> None:
    config = _make_config(tmp_path)
    calls: list[str] = []
    monkeypatch.setattr(cli, "setup_logger", lambda log_level: calls.append(log_level))

    assert cli.main(["current"], config=config) == 0
    assert calls == []


def test_subcommand_parsing() -> None:
    parser = create_parser()

    assert parser.parse_args(["list"]).command == "list"
    assert parser.parse_args(["current"]).command == "current"
    assert parser.parse_args(["use", "alpha"]).name == "alpha"
    assert parser.parse_args(["del", "alpha"]).name == "alpha"
    assert parser.parse_args(["start"]).name is None
    assert parser.parse_args(["start", "alpha"]).name == "alpha"

    add_args = parser.parse_args(
        [
            "add",
            "--name",
            "alpha",
            "--address",
            "alpha.example",
            "--port",
            "8001",
            "--type",
            "socks5",
            "--user",
            "alice",
            "--password",
            "secret",
        ]
    )
    assert (add_args.name, add_args.port, add_args.user) == ("alpha", "8001", "alice")


def test_use_persists_selection(tmp_path, capsys) -> None:
    config = _make_config(tmp_path, [("alpha", "alpha.example", "8001", "HTTP", "", "")])

    assert cli.main(["use", "alpha"], config=config) == 0

    reloaded = _make_config(tmp_path)
    assert reloaded.get("LAST_ITEM") == "alpha"
    assert "alpha" in capsys.readouterr().out


def test_use_rejects_unknown_name(tmp_path, capsys) -> None:
    config = _make_config(tmp_path)

    assert cli.main(["use", "ghost"], config=config) == 1
    assert "ghost" in capsys.readouterr().err


def test_list_marks_current_and_hides_password(tmp_path, capsys) -> None:
    config = _make_config(
        tmp_path, [("alpha", "alpha.example", "8001", "HTTP", "alice", "secret")]
    )
    config.set("LAST_ITEM", "alpha")

    assert cli.main(["list"], config=config) == 0

    out = capsys.readouterr().out
    assert "* alpha" in out
    assert "alice" in out
    assert "secret" not in out


def test_current_falls_back_to_noproxy(tmp_path, capsys) -> None:
    config = _make_config(tmp_path)

    assert cli.main(["current"], config=config) == 0

    out = capsys.readouterr().out
    assert "NoProxy" in out
    assert "127.0.0.1:8888" in out


def test_add_and_delete_proxy(tmp_path, capsys) -> None:
    config = _make_config(tmp_path)

    assert (
        cli.main(
            [
                "add",
                "--name",
                "alpha",
                "--address",
                "alpha.example",
                "--port",
                "8001",
                "--type",
                "socks5",
            ],
            config=config,
        )
        == 0
    )
    assert config.get_proxy_names() == ["alpha"]
    assert config.get_proxies()[0][3] == "SOCKS5"

    assert (
        cli.main(
            ["add", "--name", "alpha", "--address", "alpha.example", "--port", "8001"],
            config=config,
        )
        == 1
    )
    assert "already exists" in capsys.readouterr().err

    assert cli.main(["del", "alpha"], config=config) == 0
    assert config.get_proxy_names() == []
    assert cli.main(["del", "alpha"], config=config) == 1


def test_add_rejects_invalid_port(tmp_path, capsys) -> None:
    config = _make_config(tmp_path)

    assert (
        cli.main(
            ["add", "--name", "alpha", "--address", "alpha.example", "--port", "0"],
            config=config,
        )
        == 1
    )
    assert config.get_proxy_names() == []
    assert capsys.readouterr().err


def test_start_runs_listener_until_interrupted(tmp_path, monkeypatch, capsys) -> None:
    config = _make_config(tmp_path)
    events = []

    class FakeUpstream:
        description = "direct connection"

    class FakeServer:
        host = "127.0.0.1"
        port = 8888

    class FakeManager:
        def __init__(self, config) -> None:
            pass

        @property
        def server(self):
            return FakeServer()

        @property
        def current_upstream(self):
            return FakeUpstream()

        def start_proxy(self, name) -> None:
            events.append(("start", name))

        def stop_proxy(self, timeout=5) -> bool:
            events.append(("stop",))
            return True

    monkeypatch.setattr(cli, "ProxyManager", FakeManager)
    monkeypatch.setattr(cli, "_wait_for_interrupt", lambda: None)

    assert cli.main(["start"], config=config) == 0

    assert events == [("start", "NoProxy"), ("stop",)]
    out = capsys.readouterr().out
    assert "127.0.0.1:8888" in out
    assert "direct connection" in out


def test_start_surfaces_proxy_errors(tmp_path, capsys) -> None:
    config = _make_config(tmp_path)

    assert cli.main(["start", "ghost"], config=config) == 1
    assert capsys.readouterr().err
