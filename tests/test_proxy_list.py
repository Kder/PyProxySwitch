import pytest

from pyproxyswitch.proxy_list import format_proxy, load_proxy_list, save_proxy_list


def test_load_proxy_list_skips_comments_and_invalid_lines(tmp_path):
    path = tmp_path / "proxy.txt"
    path.write_text(
        "# comment\nplain proxy.example:8080\ninvalid\nsecure 127.0.0.1:1080 user:pass SOCKS5\n",
        encoding="utf-8",
    )

    assert load_proxy_list(path) == [
        ("plain", "proxy.example", "8080", "HTTP", "", ""),
        ("secure", "127.0.0.1", "1080", "SOCKS5", "user", "pass"),
    ]


@pytest.mark.parametrize(
    ("entry", "line"),
    [
        (("plain", "example.com", "80", "HTTP", "", ""), "plain example.com:80"),
        (
            ("secure", "localhost", "1080", "SOCKS5", "user", "pass"),
            "secure localhost:1080 user:pass SOCKS5",
        ),
    ],
)
def test_format_proxy(entry, line):
    assert format_proxy(entry) == line


def test_format_proxy_requires_six_fields():
    with pytest.raises(ValueError):
        format_proxy(("name", "host", "80"))


def test_save_proxy_list_creates_parent_and_round_trips(tmp_path):
    path = tmp_path / "nested" / "proxy.txt"
    proxies = [("socks", "localhost", "1080", "SOCKS5", "", "")]

    save_proxy_list(proxies, path)

    assert path.exists()
    assert load_proxy_list(path) == proxies


def test_credentials_with_shell_characters_round_trip(tmp_path):
    path = tmp_path / "proxy.txt"
    proxies = [("quoted", "localhost", "8080", "HTTP", "alice", "p a'ss\\word:ok")]

    save_proxy_list(proxies, path)

    assert load_proxy_list(path) == proxies


def test_load_proxy_list_skips_invalid_and_duplicate_entries(tmp_path):
    path = tmp_path / "proxy.txt"
    path.write_text(
        "bad-port localhost:70000\n"
        "bad-type localhost:1080 FTP\n"
        "first localhost:8080\n"
        "first localhost:8081\n"
        "lowercase localhost:1080 socks5\n",
        encoding="utf-8",
    )

    assert load_proxy_list(path) == [
        ("first", "localhost", "8080", "HTTP", "", ""),
        ("lowercase", "localhost", "1080", "SOCKS5", "", ""),
    ]


def test_format_proxy_rejects_line_breaks():
    with pytest.raises(ValueError, match="line breaks"):
        format_proxy(("name", "host", "80", "HTTP", "user", "bad\npassword"))
