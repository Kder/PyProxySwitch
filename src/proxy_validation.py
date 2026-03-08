#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyProxySwitch 代理参数验证增强模块
提供严格的代理参数验证功能
"""

import re
import socket
import shlex
from typing import Tuple, Optional, List
from PyQt6.QtGui import QRegularExpressionValidator, QIntValidator, QValidator
from PyQt6.QtCore import QRegularExpression, pyqtSignal, QObject
from logger_config import logger


class ValidationError(Exception):
    """验证错误异常"""
    pass


class ProxyValidator(QObject):
    """代理参数验证器"""

    # 信号：验证失败时发出
    validation_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # 代理名称验证：允许字母、数字、中文、下划线、连字符，长度限制
        name_regex = QRegularExpression('[a-zA-Z0-9\u4e00-\u9fa5_\\-]{1,50}')
        self.name_validator = QRegularExpressionValidator(name_regex, self)

        # 端口验证
        self.port_validator = QIntValidator(1, 65535, self)

        # 地址验证正则表达式
        self.ipv4_pattern = re.compile(
            r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        )
        # 使用更简单的IPv6验证，实际使用socket验证
        self.ipv6_pattern = None
        self.domain_pattern = re.compile(
            r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        )

        # 用户名验证
        self.username_validator = QRegularExpressionValidator(
            QRegularExpression('[a-zA-Z0-9_\\-@.+]{1,50}'), self
        )

        # 密码验证（允许更宽松的字符集）
        self.password_validator = QRegularExpressionValidator(
            QRegularExpression('.{0,100}'), self
        )

    def validate_proxy_name(self, name: str) -> str:
        """验证代理名称

        Args:
            name: 代理名称

        Returns:
            str: 验证后的代理名称

        Raises:
            ValidationError: 验证失败时抛出
        """
        import re

        name = name.strip()

        if not name:
            raise ValidationError("代理名称不能为空")

        if len(name) > 50:
            raise ValidationError("代理名称长度不能超过50个字符")

        # 使用正则表达式直接验证
        if not re.match(r'^[a-zA-Z0-9\u4e00-\u9fa5_\-]{1,50}$', name):
            raise ValidationError("代理名称只能包含字母、数字、中文、下划线和连字符，长度1-50")

        # 检查保留名称
        reserved_names = {'NoProxy', 'Default', 'System', 'None'}
        if name in reserved_names:
            raise ValidationError(f"'{name}'是保留名称，不能使用")

        return name

    def validate_proxy_address(self, address: str) -> str:
        """验证代理地址

        Args:
            address: 代理地址

        Returns:
            str: 验证通过的地址

        Raises:
            ValidationError: 验证失败时抛出
        """
        address = address.strip().lower()

        if not address:
            raise ValidationError("代理地址不能为空")

        # 检查是否包含端口
        if ':' in address:
            # 检查是否是IPv6地址带端口 [::1]:8080
            if address.startswith('[') and ']:' in address:
                # IPv6格式 [2001:db8::1]:8080
                split_pos = address.rfind(']:')
                if split_pos != -1:
                    address = address[1:split_pos]
                    port_part = address[split_pos+2:]
                    if port_part.isdigit():
                        self.validate_proxy_port(port_part)
            elif address.count(':') == 1:
                # 普通格式 IPv4或域名:端口
                host, port = address.rsplit(':', 1)
                if port.isdigit():
                    self.validate_proxy_port(port)
                address = host

        # 处理IPv6地址（可能包含方括号）
        if address.startswith('[') and address.endswith(']'):
            ipv6_inner = address[1:-1]
            try:
                # 尝试解析IPv6地址
                socket.inet_pton(socket.AF_INET6, ipv6_inner)
                address = ipv6_inner  # 去掉方括号
            except (socket.error, UnicodeError):
                raise ValidationError("无效的IPv6地址格式")
        elif ':' in address:
            # 可能是IPv6地址
            try:
                socket.inet_pton(socket.AF_INET6, address)
                # IPv6地址验证通过
                pass
            except (socket.error, UnicodeError):
                # 不是有效的IPv6，继续检查其他格式
                if not self.ipv4_pattern.match(address) and not self.domain_pattern.match(address):
                    raise ValidationError("无效的IP地址或域名格式")
        elif self.ipv4_pattern.match(address):
            # 验证IPv4地址
            parts = address.split('.')
            for part in parts:
                if int(part) > 255:
                    raise ValidationError("IPv4地址包含无效数值")
        elif self.domain_pattern.match(address):
            # 验证域名
            if len(address) > 253:
                raise ValidationError("域名长度不能超过253个字符")

            # 检查是否包含危险字符
            dangerous_chars = ['<', '>', '"', "'", ';', '|', '&', '`']
            for char in dangerous_chars:
                if char in address:
                    raise ValidationError(f"域名包含危险字符: {char}")
        else:
            raise ValidationError("无效的IP地址或域名格式")

        return address

    def validate_proxy_port(self, port: str) -> int:
        """验证代理端口

        Args:
            port: 端口号

        Returns:
            int: 验证通过的端口号

        Raises:
            ValidationError: 验证失败时抛出
        """
        port = port.strip()

        if not port:
            raise ValidationError("端口号不能为空")

        if not port.isdigit():
            raise ValidationError("端口号必须是数字")

        port_num = int(port)

        if port_num < 1 or port_num > 65535:
            raise ValidationError("端口号必须在1-65535之间")

        # 检查是否为常用代理端口
        common_ports = {80, 8080, 443, 8443, 3128, 1080, 7890, 7891}
        if port_num in common_ports:
            # 可以添加警告，但不阻止使用
            pass

        return port_num

    def validate_proxy_type(self, proxy_type: str) -> str:
        """验证代理类型

        Args:
            proxy_type: 代理类型

        Returns:
            str: 验证通过的代理类型

        Raises:
            ValidationError: 验证失败时抛出
        """
        proxy_type = proxy_type.strip().upper()

        valid_types = ['HTTP', 'SOCKS4', 'SOCKS5']

        if proxy_type not in valid_types:
            raise ValidationError(f"代理类型必须是以下之一: {', '.join(valid_types)}")

        return proxy_type

    def validate_username(self, username: str) -> str:
        """验证用户名

        Args:
            username: 用户名

        Returns:
            str: 验证通过的用户名

        Raises:
            ValidationError: 验证失败时抛出
        """
        username = username.strip()

        if not username:
            return ""  # 用户名可以为空

        if len(username) > 50:
            raise ValidationError("用户名长度不能超过50个字符")

        # 检查是否包含危险字符
        dangerous_chars = ['<', '>', '"', "'", ';', '|', '&', '`', '\n', '\r']
        for char in dangerous_chars:
            if char in username:
                raise ValidationError(f"用户名包含危险字符: {char}")

        return username

    def validate_password(self, password: str) -> str:
        """验证密码

        Args:
            password: 密码

        Returns:
            str: 验证通过的原密码（不改变）

        Raises:
            ValidationError: 验证失败时抛出
        """
        password = password

        if not password:
            return ""  # 密码可以为空

        if len(password) > 100:
            raise ValidationError("密码长度不能超过100个字符")

        # 检查是否包含控制字符
        if any(ord(char) < 32 and char not in ['\t', '\n', '\r'] for char in password):
            raise ValidationError("密码包含非法控制字符")

        return password

    def validate_full_proxy(self, name: str, address: str, port: str,
                          proxy_type: str = 'HTTP', username: str = "",
                          password: str = "") -> Tuple[str, str, int, str, str, str]:
        """完整验证代理的所有参数

        Args:
            name: 代理名称
            address: 代理地址
            port: 端口号
            proxy_type: 代理类型
            username: 用户名
            password: 密码

        Returns:
            Tuple: (name, address, port, proxy_type, username, password) 验证后的参数

        Raises:
            ValidationError: 验证失败时抛出
        """
        try:
            # 逐个验证参数
            validated_name = self.validate_proxy_name(name)
            validated_address = self.validate_proxy_address(address)
            validated_port = self.validate_proxy_port(port)
            validated_type = self.validate_proxy_type(proxy_type)
            validated_username = self.validate_username(username)
            validated_password = self.validate_password(password)

            return (validated_name, validated_address, validated_port,
                   validated_type, validated_username, validated_password)

        except ValidationError as e:
            self.validation_error.emit(str(e))
            raise

    def get_name_validator(self) -> QRegularExpressionValidator:
        """获取代理名称验证器"""
        return self.name_validator

    def get_port_validator(self) -> QIntValidator:
        """获取端口验证器"""
        return self.port_validator

    def get_username_validator(self) -> QRegularExpressionValidator:
        """获取用户名验证器"""
        return self.username_validator

    def get_password_validator(self) -> QRegularExpressionValidator:
        """获取密码验证器"""
        return self.password_validator


class BatchImportValidator:
    """批量导入验证器"""

    def __init__(self):
        self.validator = ProxyValidator()

    def validate_batch_line(self, line: str, line_number: int) -> Optional[Tuple]:
        """验证批量导入的每一行

        Args:
            line: 行内容
            line_number: 行号（用于错误提示）

        Returns:
            Tuple: 验证后的代理参数元组，验证失败返回None
        """
        line = line.strip()

        # 跳过空行和注释行
        if not line or line.startswith('#'):
            return None

        # 使用 shlex 进行安全的分词，支持引号和转义字符
        try:
            parts = shlex.split(line.strip())
        except ValueError:
            # 如果引号不匹配，尝试使用更宽松的分词
            parts = line.strip().split()

        # 检查基本格式
        if len(parts) < 2:
            raise ValidationError(
                f"第{line_number}行: 格式错误，至少需要代理名称和地址"
            )

        name = parts[0]
        address_part = parts[1]

        # 解析地址和端口
        if ':' not in address_part:
            raise ValidationError(
                f"第{line_number}行: 地址格式错误，必须包含端口（格式：地址:端口）"
            )

        # 分割地址和端口（从右边分割，支持IPv6）
        if address_part.startswith('[') and ']:' in address_part:
            # IPv6格式 [2001:db8::1]:8080
            split_pos = address_part.rfind(']:')
            if split_pos != -1:
                address = address_part[1:split_pos]
                port = address_part[split_pos+2:]
            else:
                raise ValidationError(
                    f"第{line_number}行: IPv6地址格式错误"
                )
        else:
            # 普通格式或IPv6不带端口
            address, port = address_part.rsplit(':', 1)
            # 检查是否是IPv6地址（包含多个冒号）
            if address.count(':') > 1:
                # 这可能是IPv6，但我们已经从右边分割了，应该没问题
                pass

        proxy_type = 'HTTP'  # 默认
        username = ""
        password = ""

        # 如果有更多参数
        if len(parts) >= 3:
            # 检查是否是代理类型
            if parts[2] in ['HTTP', 'SOCKS4', 'SOCKS5']:
                proxy_type = parts[2]
                # 如果还有第4个参数，可能是用户名:密码
                if len(parts) >= 4 and ':' in parts[3]:
                    username, password = parts[3].split(':', 1)
            elif ':' in parts[2]:
                username, password = parts[2].split(':', 1)

        try:
            return self.validator.validate_full_proxy(
                name, address, port, proxy_type, username, password
            )
        except ValidationError as e:
            raise ValidationError(f"第{line_number}行: {str(e)}")

    def validate_batch_content(self, content: str) -> List[Tuple]:
        """验证批量导入内容

        Args:
            content: 批量导入的内容

        Returns:
            List[Tuple]: 验证通过的代理列表

        Raises:
            ValidationError: 验证失败时抛出
        """
        proxies = []
        lines = content.split('\n')
        valid_lines = 0

        for i, line in enumerate(lines, 1):
            try:
                result = self.validate_batch_line(line, i)
                if result:
                    proxies.append(result)
                    valid_lines += 1
            except ValidationError as e:
                # 继续验证其他行，但记录错误
                logger.warning(f"{str(e)}")

        if valid_lines == 0:
            raise ValidationError("没有找到有效的代理配置")

        return proxies