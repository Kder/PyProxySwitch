import logging
import logging.handlers

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
