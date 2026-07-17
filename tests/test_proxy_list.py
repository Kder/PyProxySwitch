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
