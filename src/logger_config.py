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
import pps_config


# 创建日志目录
LOG_DIR = Path(pps_config.PROGRAM_PATH) / 'logs'
LOG_DIR.mkdir(exist_ok=True)

# 日志文件路径
LOG_FILE = LOG_DIR / 'PyProxySwitch.log'


def setup_logger(name: str = 'PyProxySwitch', debug_mode: Optional[bool] = None) -> logging.Logger:
    """配置并返回日志记录器

    Args:
        name: 日志记录器名称
        debug_mode: 调试模式（True/False），如果为None则从配置读取

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 读取调试模式配置
    if debug_mode is None:
        debug_mode = pps_config.CONFIG.get('DEBUG_MODE', 0) == 1
    
    # 设置日志级别：调试模式下为DEBUG，否则为INFO
    log_level = logging.DEBUG if debug_mode else logging.INFO
    logger.setLevel(logging.DEBUG)  # 记录器层级设置为DEBUG，由处理器控制输出
    
    # ==================== 控制台处理器 ====================
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # ==================== 文件处理器 ====================
    # 使用RotatingFileHandler实现日志轮转
    # 配置：5MB单个文件，最多保留7个历史日志
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=7,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # 文件总是记录详细日志
    
    # ==================== 日志格式化器 ====================
    # 格式：时间 - 记录器名 - 级别 - 消息
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # ==================== 添加处理器 ====================
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


# 创建全局日志记录器实例
logger = setup_logger()
