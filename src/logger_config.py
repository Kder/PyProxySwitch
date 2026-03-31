#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyProxySwitch 日志系统配置
提供统一的日志管理和记录功能
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional


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
    log_dir: Optional[Path] = None,
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
    
    # 控制台处理器（仅显示 INFO 及以上级别）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（记录所有级别）
    if log_dir is None:
        # 尝试从配置管理器获取自定义日志路径
        try:
            from .config import ConfigManager
            config = ConfigManager()
            custom_log_path = config.get('LOG_PATH', '').strip()
            if custom_log_path:
                log_dir = Path(custom_log_path)
            else:
                log_dir = Path(__file__).parent.parent / 'logs'
        except Exception:
            # 如果配置管理器不可用，使用默认路径
            log_dir = Path(__file__).parent.parent / 'logs'

    # 确保日志目录存在
    try:
        log_dir.mkdir(exist_ok=True, parents=True)
        # 验证目录确实被创建了
        if not log_dir.exists():
            raise Exception("Directory creation failed")
    except Exception as e:
        # 如果无法创建指定目录，回退到默认路径
        import warnings
        warnings.warn(f"无法创建日志目录 {log_dir}: {e}，使用默认路径")
        log_dir = Path(__file__).parent.parent / 'logs'
        try:
            log_dir.mkdir(exist_ok=True, parents=True)
        except Exception:
            # 如果默认路径也无法创建，继续执行（文件处理器可能会处理这个情况）
            pass

    log_file = log_dir / 'PyProxySwitch.log'
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8',
        delay=True  # 延迟文件打开
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def update_log_path(new_log_dir: Optional[Path] = None) -> None:
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

    # 确定新的日志目录
    if new_log_dir is None:
        try:
            from .config import ConfigManager
            config = ConfigManager()
            custom_log_path = config.get('LOG_PATH', '').strip()
            if custom_log_path:
                new_log_dir = Path(custom_log_path)
            else:
                new_log_dir = Path(__file__).parent.parent / 'logs'
        except Exception:
            new_log_dir = Path(__file__).parent.parent / 'logs'

    # 确保目录存在
    try:
        new_log_dir.mkdir(exist_ok=True, parents=True)
        # 验证目录确实被创建了
        if not new_log_dir.exists():
            raise Exception("Directory creation failed")
    except Exception as e:
        import warnings
        warnings.warn(f"无法创建日志目录 {new_log_dir}: {e}，使用默认路径")
        new_log_dir = Path(__file__).parent.parent / 'logs'
        try:
            new_log_dir.mkdir(exist_ok=True, parents=True)
        except Exception:
            # 如果默认路径也无法创建，继续执行（文件处理器可能会处理这个情况）
            pass

    # 创建新的文件处理器
    formatter = Formatter()
    log_file = new_log_dir / 'PyProxySwitch.log'
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
