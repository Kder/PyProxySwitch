import json

from pyproxyswitch.config import ConfigManager


def make_config(tmp_path, settings=None, proxies=""):
    config_path = tmp_path / "PPS.conf"
    proxy_path = tmp_path / "proxy.txt"
    if settings is not None:
        config_path.write_text(json.dumps(settings), encoding="utf-8")
    proxy_path.write_text(proxies, encoding="utf-8")
    return ConfigManager(
        config_path=config_path,
        proxy_list_path=proxy_path,
        use_singleton=False,
    )


def test_defaults_do_not_contain_backend_selector(tmp_path):
    config = make_config(tmp_path)

    assert "CMD" not in config
    assert config.get("LOCAL_ADDRESS") == "127.0.0.1"
    assert config.get("LOCAL_PORT") == 8888


def test_load_migrates_old_settings_without_retaining_backend(tmp_path):
    config = make_config(
        tmp_path,
        {"CMD": "old-backend", "FISRT_RUN": 1, "LOCAL_PORT": 9000},
    )

    assert "CMD" not in config
    assert config.get("FIRST_RUN") == 1
    assert config.get("LOCAL_PORT") == 9000


def test_settings_round_trip(tmp_path):
    config = make_config(tmp_path)
    config.update({"LANG": "en", "LOCAL_PORT": 8123})
    config.save()

    reloaded = make_config(
        tmp_path,
        json.loads((tmp_path / "PPS.conf").read_text(encoding="utf-8")),
    )
    assert reloaded.get("LANG") == "en"
    assert reloaded.get("LOCAL_PORT") == 8123


def test_proxy_updates_keep_names_in_sync_and_round_trip(tmp_path):
    config = make_config(tmp_path)
    config.set_proxies(
        [
            ["http", "proxy.example", "8080", "http", "", ""],
            ["socks", "127.0.0.1", "1080", "socks5", "alice", "secret"],
        ]
    )

    assert config.get_proxy_names() == ["http", "socks"]
    assert config.get_proxies()[1][3] == "SOCKS5"

    config.save_proxies()
    config.reload()
    assert config.get_proxy_names() == ["http", "socks"]
    assert config.get_proxies()[1] == (
        "socks",
        "127.0.0.1",
        "1080",
        "SOCKS5",
        "alice",
        "secret",
    )


def test_singleton_can_be_reset(tmp_path):
    config_path = tmp_path / "PPS.conf"
    proxy_path = tmp_path / "proxy.txt"
    first = ConfigManager(config_path=config_path, proxy_list_path=proxy_path)
    second = ConfigManager()
    assert first is second

    ConfigManager.reset_singleton()
    assert ConfigManager(config_path=config_path, proxy_list_path=proxy_path) is not first


def test_malformed_persisted_settings_are_repaired(tmp_path):
    config = make_config(
        tmp_path,
        {
            "CONNECT_TIMEOUT": float("inf"),
            "DEBUG": "unexpected",
            "DEFAULT_ITEM": None,
            "LANG": "missing-locale",
            "LAST_ITEM": [],
            "LOCAL_ADDRESS": "   ",
            "LOCAL_PORT": 70000,
            "LOG_PATH": 123,
            "SHOW_WELCOME": 9,
        },
    )

    assert config.get("CONNECT_TIMEOUT") == 15
    assert config.get("DEBUG") == 0
    assert config.get("DEFAULT_ITEM") == "NoProxy"
    assert config.get("LANG") == "zh_CN"
    assert config.get("LAST_ITEM") == "NoProxy"
    assert config.get("LOCAL_ADDRESS") == "127.0.0.1"
    assert config.get("LOCAL_PORT") == 8888
    assert config.get("LOG_PATH") == ""
    assert config.get("SHOW_WELCOME") == 0


def test_oversized_connect_timeout_is_repaired(tmp_path):
    config = make_config(tmp_path, {"CONNECT_TIMEOUT": 10**4000})

    assert config.get("CONNECT_TIMEOUT") == 15


def test_obsolete_backend_selector_cannot_be_persisted(tmp_path):
    config = make_config(tmp_path)

    config.update({"CMD": "legacy", "LOCAL_PORT": 8123})
    config.save()

    saved = json.loads((tmp_path / "PPS.conf").read_text(encoding="utf-8"))
    assert "CMD" not in saved
    assert saved["LOCAL_PORT"] == 8123


def test_update_applies_log_path_side_effect(tmp_path, monkeypatch):
    config = make_config(tmp_path)
    updates = []
    monkeypatch.setattr("pyproxyswitch.logger_config.update_log_path", lambda: updates.append(True))

    config.update({"LOG_PATH": str(tmp_path / "logs")})

    assert updates == [True]


def test_failed_atomic_config_save_preserves_previous_file(tmp_path, monkeypatch):
    config = make_config(tmp_path, {"LANG": "zh_CN"})
    original = config.config_path.read_text(encoding="utf-8")
    config.set("LANG", "en")

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("pyproxyswitch.atomic_write.os.replace", fail_replace)

    assert not config.save()
    assert config.config_path.read_text(encoding="utf-8") == original
    assert not list(config.config_path.parent.glob(f".{config.config_path.name}.*.tmp"))
