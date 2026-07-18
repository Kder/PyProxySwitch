#!/usr/bin/env python

"""
PyProxySwitch 代理参数验证增强模块
提供严格的代理参数验证功能
"""

import logging
import re
import shlex
import socket

from PySide6.QtCore import QObject, QRegularExpression, Signal
from PySide6.QtGui import QIntValidator, QRegularExpressionValidator

logger = logging.getLogger("PyProxySwitch")

ParsedProxy = tuple[str, str, str, str, str, str]
ValidatedProxy = tuple[str, str, int, str, str, str]


class ValidationError(Exception):
    """验证错误异常"""

    pass


class ProxyValidator(QObject):
    """代理参数验证器"""

    # 信号：验证失败时发出
    validation_error = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        # 代理名称验证：允许字母、数字、中文、下划线、连字符，长度限制
        name_regex = QRegularExpression("[a-zA-Z0-9\u4e00-\u9fa5_\\-]{1,50}")
        self.name_validator = QRegularExpressionValidator(name_regex, self)

        # 端口验证
        self.port_validator = QIntValidator(1, 65535, self)

        # 地址验证正则表达式 - Fixed to properly validate 0-255
        # Each octet pattern: 0-9, 10-99, 100-199, 200-249, 250-255
        self.ipv4_pattern = re.compile(
            r"^(?:(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\.){3}(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])$"
        )
        self.domain_pattern = re.compile(
            r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
        )

        # 用户名验证
        self.username_validator = QRegularExpressionValidator(
            QRegularExpression("[a-zA-Z0-9_\\-@.+]{1,50}"), self
        )

        # 密码验证（允许更宽松的字符集）
        self.password_validator = QRegularExpressionValidator(
            QRegularExpression(".{0,100}"), self
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
        name = name.strip()

        if not name:
            raise ValidationError("代理名称不能为空")

        if len(name) > 50:
            raise ValidationError("代理名称长度不能超过50个字符")

        # 使用正则表达式直接验证
        if not re.fullmatch(r"[a-zA-Z0-9\u4e00-\u9fa5_\-]{1,50}", name):
            raise ValidationError(
                "代理名称只能包含字母、数字、中文、下划线和连字符，长度1-50"
            )

        # 检查保留名称
        reserved_names = {"NoProxy", "Default", "System", "None"}
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

        # 地址和端口使用独立字段。拒绝内嵌端口，避免两个端口不一致时
        # 静默采用另一个值。
        if (address.startswith("[") and "]:" in address) or address.count(":") == 1:
            raise ValidationError("代理地址不能包含端口号，请使用独立的端口字段")

        # 首先检查是否包含危险字符（适用于所有地址格式）
        dangerous_chars = ["<", ">", '"', "'", ";", "|", "&", "`"]
        for char in dangerous_chars:
            if char in address:
                raise ValidationError(f"域名包含危险字符: {char}")

        # 处理IPv6地址（可能包含方括号）
        if address.startswith("[") and address.endswith("]"):
            ipv6_inner = address[1:-1]
            try:
                # 尝试解析IPv6地址
                socket.inet_pton(socket.AF_INET6, ipv6_inner)
                address = ipv6_inner  # 去掉方括号
            except (OSError, UnicodeError):
                raise ValidationError("无效的IPv6地址格式") from None
        elif ":" in address:
            # 可能是IPv6地址
            try:
                socket.inet_pton(socket.AF_INET6, address)
                # IPv6地址验证通过
                pass
            except (OSError, UnicodeError):
                # 不是有效的IPv6，继续检查其他格式
                if not self.ipv4_pattern.match(
                    address
                ) and not self.domain_pattern.match(address):
                    raise ValidationError("无效的IP地址或域名格式") from None
        # 检查是否为纯数字+点号格式（IP类地址）
        elif address.replace(".", "").isdigit() and "." in address:
            # 这是IP类地址，必须符合IPv4格式
            if not self.ipv4_pattern.match(address):
                raise ValidationError("无效的IP地址格式")
            # 额外检查每个八位组
            parts = address.split(".")
            for part in parts:
                if int(part) > 255:
                    raise ValidationError("IPv4地址包含无效数值")
        elif self.domain_pattern.match(address):
            # 验证域名
            if len(address) > 253:
                raise ValidationError("域名长度不能超过253个字符")
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

        valid_types = ["HTTP", "SOCKS4", "SOCKS5"]

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
        dangerous_chars = ["<", ">", '"', "'", ";", "|", "&", "`", ":", "\n", "\r"]
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
        if not password:
            return ""  # 密码可以为空

        if len(password) > 100:
            raise ValidationError("密码长度不能超过100个字符")

        # 检查是否包含控制字符
        if any(ord(char) < 32 or ord(char) == 127 for char in password):
            raise ValidationError("密码包含非法控制字符")

        return password

    def validate_full_proxy(
        self,
        name: str,
        address: str,
        port: str,
        proxy_type: str = "HTTP",
        username: str = "",
        password: str = "",
    ) -> ValidatedProxy:
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

            if validated_type == "SOCKS5" and (validated_username or validated_password):
                if not validated_username or not validated_password:
                    raise ValidationError("SOCKS5认证必须同时提供用户名和密码")
                try:
                    encoded_username = validated_username.encode("utf-8")
                    encoded_password = validated_password.encode("utf-8")
                except UnicodeEncodeError:
                    raise ValidationError("SOCKS5认证信息包含无效的Unicode字符") from None
                if len(encoded_username) > 255 or len(encoded_password) > 255:
                    raise ValidationError("SOCKS5用户名和密码的UTF-8编码不能超过255字节")

            return (
                validated_name,
                validated_address,
                validated_port,
                validated_type,
                validated_username,
                validated_password,
            )

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

    def __init__(self) -> None:
        self.validator: ProxyValidator = ProxyValidator()

    @staticmethod
    def parse_proxy_line(line: str) -> ParsedProxy | None:
        """解析代理列表行，返回标准化的代理元组(名称, 地址, 端口, 类型, 用户, 密码)"""

        # 跳过空行和注释行
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            return None

        # 使用 shlex 进行安全的分词，支持引号和转义字符
        try:
            line_items = shlex.split(stripped)
        except ValueError as exc:
            raise ValidationError("引号或转义字符不完整") from exc
        if len(line_items) < 2:
            raise ValidationError("格式错误，至少需要代理名称和地址")
        if len(line_items) > 4:
            raise ValidationError("参数过多")

        # 解析地址和端口
        if ":" not in line_items[1]:
            # 为了与旧行为兼容，抛出IndexError
            raise IndexError("地址格式错误，必须包含端口（格式：地址:端口）")
        username = ""
        password = ""
        proxy_type = "HTTP"

        # 分割地址和端口（从右边分割，支持IPv6）
        if line_items[1].startswith("[") and "]:" in line_items[1]:
            # IPv6格式 [2001:db8::1]:8080
            split_pos = line_items[1].rfind("]:")
            if split_pos != -1:
                address = line_items[1][1:split_pos]
                port = line_items[1][split_pos + 2 :]
            else:
                raise ValidationError("IPv6地址格式错误")
        else:
            # 普通格式或IPv6不带端口
            address, port = line_items[1].rsplit(":", 1)
            # 检查是否是IPv6地址（包含多个冒号）
            if address.count(":") > 1:
                # 这可能是IPv6，但我们已经从右边分割了，应该没问题
                pass

        valid_types = {"HTTP", "SOCKS4", "SOCKS5"}
        if len(line_items) == 3:
            possible_type = line_items[2].upper()
            if possible_type in valid_types:
                proxy_type = possible_type
            else:
                username, separator, password = line_items[2].partition(":")
                if not separator:
                    raise ValidationError(
                        "认证信息必须使用用户名:密码格式，或指定受支持的代理类型"
                    )
        elif len(line_items) == 4:
            username, separator, password = line_items[2].partition(":")
            if not separator:
                raise ValidationError("认证信息必须使用用户名:密码格式")
            proxy_type = line_items[3].upper()
            if proxy_type not in valid_types:
                raise ValidationError(f"不支持的代理类型 {line_items[3]}")

        return (
            line_items[0],
            address,
            port,
            proxy_type,
            username,
            password,
        )

    def validate_batch_line(self, line: str, line_number: int) -> ValidatedProxy | None:
        """验证批量导入的每一行

        Args:
            line: 行内容
            line_number: 行号（用于错误提示）

        Returns:
            Tuple: 验证后的代理参数元组，验证失败返回None
        """
        try:
            proxy_tuple = self.parse_proxy_line(line)
        except (IndexError, ValidationError) as e:
            raise ValidationError(f"第{line_number}行: {e}") from e

        if not proxy_tuple:
            return None

        name, address, port, proxy_type, username, password = proxy_tuple

        try:
            return self.validator.validate_full_proxy(
                name, address, port, proxy_type, username, password
            )
        except ValidationError as e:
            raise ValidationError(f"第{line_number}行: {str(e)}") from e

    def validate_batch_content(
        self, content: str, *, strict: bool = False
    ) -> list[ValidatedProxy]:
        """验证批量导入内容

        Args:
            content: 批量导入的内容
            strict: 为True时，任意无效行都会使整个批次失败

        Returns:
            List[Tuple]: 验证通过的代理列表

        Raises:
            ValidationError: 验证失败时抛出
        """
        proxies: list[ValidatedProxy] = []
        proxy_names: set[str] = set()
        lines = content.split("\n")
        valid_lines = 0
        errors: list[str] = []

        for i, line in enumerate(lines, 1):
            try:
                result = self.validate_batch_line(line, i)
                if result:
                    if result[0] in proxy_names:
                        raise ValidationError(f"第{i}行: 代理名称 {result[0]!r} 重复")
                    proxies.append(result)
                    proxy_names.add(result[0])
                    valid_lines += 1
            except (ValidationError, IndexError) as e:
                # 继续验证其他行，但记录错误
                errors.append(str(e))
                logger.warning("%s", e)

        if strict and errors:
            raise ValidationError("批量代理配置包含错误：\n" + "\n".join(errors))

        if valid_lines == 0:
            raise ValidationError("没有找到有效的代理配置")

        return proxies
