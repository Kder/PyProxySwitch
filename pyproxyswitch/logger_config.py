#!/usr/bin/env python

"""
PyProxySwitch 日志系统配置
提供统一的日志管理和记录功能
"""

import logging
import logging.handlers
from pathlib import Path

from .paths import USER_LOG_DIR


def _configured_log_dir() -> Path:
    """Return the configured log directory or the per-user default."""
    try:
        from .config import ConfigManager

        custom_log_path = ConfigManager().get('LOG_PATH', '').strip()
        return Path(custom_log_path) if custom_log_path else USER_LOG_DIR
    except Exception:
        return USER_LOG_DIR


def _prepare_log_dir(log_dir: Path) -> Path | None:
    """Create a writable log directory without ever using site-packages."""
    candidates = [log_dir]
    if log_dir != USER_LOG_DIR:
        candidates.append(USER_LOG_DIR)

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            candidate.mkdir(exist_ok=True, parents=True)
            if not candidate.is_dir():
                raise OSError("directory creation failed")
            return candidate
        except Exception as e:
            last_error = e

    import warnings

    warnings.warn(
        f"无法创建日志目录 {log_dir}: {last_error}，已禁用文件日志",
        stacklevel=3,
    )
    return None


class Formatter(logging.Formatter):
    """自定义日志格式化器，根据日志级别使用不同的格式"""

    FORMATS = {
        logging.DEBUG: "%(asctime)s - %(name)s - [DEBUG] - %(message)s [%(filename)s:%(lineno)d]",
        logging.INFO: "%(asctime)s - %(name)s - [INFO] - %(message)s",
        logging.WARNING: "%(asctime)s - %(name)s - [WARNING] - %(message)s",
        logging.ERROR: "%(asctime)s - %(name)s - [ERROR] - %(message)s [%(filename)s:%(lineno)d]",
        logging.CRITICAL: "%(asctime)s - %(name)s - [CRITICAL] - %(message)s [%(filename)s:%(lineno)d]",
    }

    def format(self, record):
        """根据日志级别选择适当的格式"""
        log_format = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


def setup_logger(
    name: str = 'PyProxySwitch',
    log_dir: Path | None = None,
    log_level: int = logging.INFO,
    max_bytes: int = 5 * 1024 * 1024,  # 5MB
    backup_count: int = 3
) -> logging.Logger:
    """
    配置日志记录器

    Args:
        name: 记录器名称
        log_dir: 日志目录，如果为None则使用默认目录
        log_level: 日志级别（默认 INFO）
        max_bytes: 日志文件最大大小（默认 5MB）
        backup_count: 备份文件数量（默认 3）

    Returns:
        logging.Logger: 配置的记录器
    """
    logger = logging.getLogger(name)

    # 避免重复添加处理器，但要更新console_handler的级别
    if logger.handlers:
        # 更新现有console_handler的级别
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(log_level)
        return logger

    logger.setLevel(logging.DEBUG)

    # 设置日志格式化器
    formatter = Formatter()

    # 控制台处理器（根据传入的级别过滤）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器（记录所有级别）
    prepared_log_dir = _prepare_log_dir(log_dir or _configured_log_dir())
    if prepared_log_dir is not None:
        log_file = prepared_log_dir / 'PyProxySwitch.log'
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
            delay=True,
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def update_log_path(new_log_dir: Path | None = None) -> None:
    """
    更新日志文件路径

    Args:
        new_log_dir: 新的日志目录，如果为None则从配置管理器获取
    """
    logger = logging.getLogger('PyProxySwitch')

    # 如果已经有文件处理器，移除它们
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            logger.removeHandler(handler)
            handler.close()

    # 确定并创建新的日志目录
    prepared_log_dir = _prepare_log_dir(new_log_dir or _configured_log_dir())
    if prepared_log_dir is None:
        return

    # 创建新的文件处理器
    formatter = Formatter()
    log_file = prepared_log_dir / 'PyProxySwitch.log'
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8',
        delay=True  # 延迟文件打开
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


# 初始化默认日志记录器（延迟初始化以避免循环导入）
def _init_logger():
    """初始化日志记录器"""
    try:
        return setup_logger()
    except Exception:
        # 如果setup_logger失败（可能是循环导入），创建基本logger
        logger = logging.getLogger('PyProxySwitch')
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

# 延迟初始化logger
logger = None

def get_logger():
    """获取日志记录器（延迟初始化）"""
    global logger
    if logger is None:
        logger = _init_logger()
    return logger
