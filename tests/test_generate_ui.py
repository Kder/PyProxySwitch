from tools.generate_ui import normalize_generated_module


def test_normalize_generated_module_ignores_uic_version_and_line_endings() -> None:
    windows_output = (
        b"## Created by: Qt User Interface Compiler version 6.10.2\r\n"
        b"generated_code()\r\n"
    )
    linux_output = (
        b"## Created by: Qt User Interface Compiler version 6.11.1\n"
        b"generated_code()\n"
    )

    expected = b"## Created by: Qt User Interface Compiler\ngenerated_code()\n"
    assert normalize_generated_module(windows_output) == expected
    assert normalize_generated_module(linux_output) == expected
