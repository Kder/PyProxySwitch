import logging
import logging.handlers
from pathlib import Path

from pyproxyswitch import logger_config
from pyproxyswitch.logger_config import setup_logger


def test_reconfiguring_console_level_keeps_file_handler_at_debug(tmp_path) -> None:
    logger = setup_logger(
        name=f"PyProxySwitch.test.{tmp_path.name}",
        log_dir=tmp_path,
        log_level=logging.WARNING,
    )
    try:
        console_handler = next(
            handler
            for handler in logger.handlers
            if isinstance(handler, logging.StreamHandler)
            and not isinstance(handler, logging.FileHandler)
        )
        file_handler = next(
            handler
            for handler in logger.handlers
            if isinstance(handler, logging.handlers.RotatingFileHandler)
        )

        setup_logger(name=logger.name, log_level=logging.ERROR)

        assert console_handler.level == logging.ERROR
        assert file_handler.level == logging.DEBUG
    finally:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()


def test_unwritable_custom_log_dir_falls_back(tmp_path, monkeypatch) -> None:
    custom_log_dir = tmp_path / "custom"
    fallback_log_dir = tmp_path / "fallback"
    real_temporary_file = logger_config.tempfile.NamedTemporaryFile

    def probe_temporary_file(*args, **kwargs):
        if Path(kwargs["dir"]) == custom_log_dir:
            raise PermissionError("custom log directory is read-only")
        return real_temporary_file(*args, **kwargs)

    monkeypatch.setattr(logger_config, "USER_LOG_DIR", fallback_log_dir)
    monkeypatch.setattr(logger_config.tempfile, "NamedTemporaryFile", probe_temporary_file)

    logger = setup_logger(
        name=f"PyProxySwitch.test.fallback.{tmp_path.name}",
        log_dir=custom_log_dir,
    )
    try:
        file_handler = next(
            handler
            for handler in logger.handlers
            if isinstance(handler, logging.handlers.RotatingFileHandler)
        )
        assert Path(file_handler.baseFilename) == fallback_log_dir / "PyProxySwitch.log"
    finally:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
