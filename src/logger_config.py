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
    
    # 避免重复添加处理器
    if logger.handlers:
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
    log_dir = log_dir or Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / 'PyProxySwitch.log'
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# 初始化默认日志记录器
logger = setup_logger()
