#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
异常处理模块

定义了PyProxySwitch中使用的自定义异常类，用于更好的错误管理和用户反馈。
"""


class ProxyError(Exception):
    """代理操作的基类异常"""
    
    def __init__(self, user_message: str, log_message: str = None):
        """
        初始化异常
        
        Args:
            user_message: 用户看到的消息（通常用于UI提示）
            log_message: 日志消息（通常包含更多技术细节），默认与user_message相同
        """
        self.user_message = user_message  # 用户看到的消息
        self.log_message = log_message or user_message  # 日志消息
        super().__init__(self.user_message)


class ProxyStartError(ProxyError):
    """启动代理失败"""
    pass


class ProxyStopError(ProxyError):
    """停止代理失败"""
    pass


class ConfigError(ProxyError):
    """配置错误"""
    pass
