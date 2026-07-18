from pyproxyswitch.__main__ import create_parser


def test_log_level_is_only_overridden_when_explicitly_requested() -> None:
    parser = create_parser()

    assert parser.parse_args([]).log_level is None
    assert parser.parse_args(["--log-level", "DEBUG"]).log_level == "DEBUG"
