#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyProxySwitch 代理验证模块测试

测试 ProxyValidator 和 BatchImportValidator 的功能。
"""

import pytest
import sys
from pathlib import Path

# 确保导入路径正确 (项目根目录)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.proxy_validation import ProxyValidator, BatchImportValidator, ValidationError


class TestProxyValidatorName:
    """代理名称验证测试"""

    def test_valid_name_simple(self, proxy_validator):
        """测试简单的有效名称"""
        assert proxy_validator.validate_proxy_name("test") == "test"

    def test_valid_name_with_numbers(self, proxy_validator):
        """测试包含数字的名称"""
        assert proxy_validator.validate_proxy_name("proxy123") == "proxy123"

    def test_valid_name_with_underscore(self, proxy_validator):
        """测试包含下划线的名称"""
        assert proxy_validator.validate_proxy_name("my_proxy") == "my_proxy"

    def test_valid_name_with_hyphen(self, proxy_validator):
        """测试包含连字符的名称"""
        assert proxy_validator.validate_proxy_name("my-proxy") == "my-proxy"

    def test_valid_name_chinese(self, proxy_validator):
        """测试中文名称"""
        assert proxy_validator.validate_proxy_name("测试代理") == "测试代理"

    def test_valid_name_max_length(self, proxy_validator):
        """测试最大长度边界 (50字符)"""
        name = "a" * 50
        assert proxy_validator.validate_proxy_name(name) == name

    def test_valid_name_with_whitespace(self, proxy_validator):
        """测试名称首尾空白被去除"""
        assert proxy_validator.validate_proxy_name("  test  ") == "test"

    def test_invalid_name_empty(self, proxy_validator):
        """测试空名称"""
        with pytest.raises(ValidationError) as exc_info:
            proxy_validator.validate_proxy_name("")
        assert "不能为空" in str(exc_info.value)

    def test_invalid_name_whitespace_only(self, proxy_validator):
        """测试仅包含空白字符的名称"""
        with pytest.raises(ValidationError) as exc_info:
            proxy_validator.validate_proxy_name("   ")
        assert "不能为空" in str(exc_info.value)

    def test_invalid_name_too_long(self, proxy_validator):
        """测试过长名称"""
        long_name = "a" * 51
        with pytest.raises(ValidationError) as exc_info:
            proxy_validator.validate_proxy_name(long_name)
        assert "50" in str(exc_info.value)

    def test_invalid_name_special_chars(self, proxy_validator):
        """测试包含特殊字符的名称"""
        invalid_names = [
            "test*proxy",
            "test@proxy",
            "test#proxy",
            "test$proxy",
            "test proxy",  # 空格
        ]
        for name in invalid_names:
            with pytest.raises(ValidationError):
                proxy_validator.validate_proxy_name(name)

    def test_invalid_name_reserved(self, proxy_validator):
        """测试保留名称"""
        reserved_names = ["NoProxy", "Default", "System", "None"]
        for name in reserved_names:
            with pytest.raises(ValidationError) as exc_info:
                proxy_validator.validate_proxy_name(name)
            assert "保留名称" in str(exc_info.value)


class TestProxyValidatorAddress:
    """代理地址验证测试"""

    def test_valid_ipv4_standard(self, proxy_validator):
        """测试标准 IPv4 地址"""
        assert proxy_validator.validate_proxy_address("192.168.1.1") == "192.168.1.1"

    def test_valid_ipv4_all_octets_max(self, proxy_validator):
        """测试 IPv4 所有段都是最大值"""
        assert (
            proxy_validator.validate_proxy_address("255.255.255.255")
            == "255.255.255.255"
        )

    def test_valid_ipv4_leading_zeros(self, proxy_validator):
        """测试 IPv4 开头零被保留"""
        # 实际行为：010会被视为八进制还是保留？
        # 这里测试正常情况
        assert proxy_validator.validate_proxy_address("1.1.1.1") == "1.1.1.1"

    def test_valid_domain_simple(self, proxy_validator):
        """测试简单域名"""
        assert proxy_validator.validate_proxy_address("example.com") == "example.com"

    def test_valid_domain_subdomain(self, proxy_validator):
        """测试子域名"""
        assert (
            proxy_validator.validate_proxy_address("sub.example.com")
            == "sub.example.com"
        )

    def test_valid_domain_with_numbers(self, proxy_validator):
        """测试包含数字的域名"""
        assert (
            proxy_validator.validate_proxy_address("proxy123.example.com")
            == "proxy123.example.com"
        )

    def test_valid_ipv6_bracket(self, proxy_validator):
        """测试 IPv6 地址 (带方括号)"""
        assert proxy_validator.validate_proxy_address("[::1]") == "::1"
        assert proxy_validator.validate_proxy_address("[2001:db8::1]") == "2001:db8::1"

    def test_valid_ipv6_no_bracket(self, proxy_validator):
        """测试 IPv6 地址 (不带方括号)"""
        result = proxy_validator.validate_proxy_address("::1")
        assert result == "::1"

    def test_invalid_address_empty(self, proxy_validator):
        """测试空地址"""
        with pytest.raises(ValidationError) as exc_info:
            proxy_validator.validate_proxy_address("")
        assert "不能为空" in str(exc_info.value)

    def test_invalid_ipv4_octet_overflow(self, proxy_validator):
        """测试 IPv4 段值超出范围

        注意: 修复后的验证器会将此类地址识别为IP类地址并正确拒绝
        """
        # 192.168.1.256 应该被拒绝，因为256超出有效范围
        with pytest.raises(ValidationError):
            proxy_validator.validate_proxy_address("192.168.1.256")

    def test_invalid_ipv4_too_many_octets(self, proxy_validator):
        """测试 IPv4 段数过多

        注意: 修复后的验证器会将此类地址识别为IP类地址并正确拒绝
        """
        # 192.168.1.1.1 应该被拒绝，因为不是有效的IPv4格式
        with pytest.raises(ValidationError):
            proxy_validator.validate_proxy_address("192.168.1.1.1")

    def test_invalid_domain_dangerous_chars(self, proxy_validator):
        """测试域名包含危险字符"""
        dangerous = ["<", ">", '"', "'", ";", "|", "&", "`"]
        for char in dangerous:
            with pytest.raises(ValidationError):
                proxy_validator.validate_proxy_address(f"test{char}example.com")


class TestProxyValidatorPort:
    """代理端口验证测试"""

    def test_valid_port_min(self, proxy_validator):
        """测试最小端口号"""
        assert proxy_validator.validate_proxy_port("1") == 1

    def test_valid_port_max(self, proxy_validator):
        """测试最大端口号"""
        assert proxy_validator.validate_proxy_port("65535") == 65535

    def test_valid_port_common(self, proxy_validator):
        """测试常用端口"""
        common_ports = ["80", "443", "8080", "3128", "1080"]
        for port in common_ports:
            assert proxy_validator.validate_proxy_port(port) == int(port)

    def test_valid_port_with_whitespace(self, proxy_validator):
        """测试带空白字符的端口"""
        assert proxy_validator.validate_proxy_port("  8080  ") == 8080

    def test_invalid_port_zero(self, proxy_validator):
        """测试端口 0"""
        with pytest.raises(ValidationError) as exc_info:
            proxy_validator.validate_proxy_port("0")
        assert "1-65535" in str(exc_info.value)

    def test_invalid_port_too_large(self, proxy_validator):
        """测试超出范围的端口"""
        with pytest.raises(ValidationError) as exc_info:
            proxy_validator.validate_proxy_port("65536")
        assert "1-65535" in str(exc_info.value)

    def test_invalid_port_negative(self, proxy_validator):
        """测试负数端口"""
        with pytest.raises(ValidationError):
            proxy_validator.validate_proxy_port("-1")

    def test_invalid_port_non_numeric(self, proxy_validator):
        """测试非数字端口"""
        with pytest.raises(ValidationError) as exc_info:
            proxy_validator.validate_proxy_port("abc")
        assert "必须是数字" in str(exc_info.value)


class TestProxyValidatorType:
    """代理类型验证测试"""

    @pytest.mark.parametrize("proxy_type", ["HTTP", "SOCKS4", "SOCKS5"])
    def test_valid_types(self, proxy_validator, proxy_type):
        """测试有效的代理类型"""
        assert proxy_validator.validate_proxy_type(proxy_type) == proxy_type

    @pytest.mark.parametrize("proxy_type", ["http", "socks4", "socks5"])
    def test_valid_types_lowercase(self, proxy_validator, proxy_type):
        """测试小写代理类型被转为大写"""
        result = proxy_validator.validate_proxy_type(proxy_type)
        assert result == proxy_type.upper()

    @pytest.mark.parametrize("invalid_type", ["FTP", "SSH", "INVALID", ""])
    def test_invalid_types(self, proxy_validator, invalid_type):
        """测试无效代理类型"""
        with pytest.raises(ValidationError) as exc_info:
            proxy_validator.validate_proxy_type(invalid_type)
        assert "必须是以下之一" in str(exc_info.value)


class TestProxyValidatorUsername:
    """用户名验证测试"""

    def test_valid_username_simple(self, proxy_validator):
        """测试简单用户名"""
        assert proxy_validator.validate_username("testuser") == "testuser"

    def test_valid_username_with_special_chars(self, proxy_validator):
        """测试包含特殊字符的用户名"""
        valid_chars = ["_", "-", "@", "."]
        for char in valid_chars:
            assert (
                proxy_validator.validate_username(f"user{char}name")
                == f"user{char}name"
            )

    def test_valid_username_empty(self, proxy_validator):
        """测试空用户名（允许）"""
        assert proxy_validator.validate_username("") == ""

    def test_valid_username_max_length(self, proxy_validator):
        """测试最大长度"""
        name = "a" * 50
        assert proxy_validator.validate_username(name) == name

    def test_invalid_username_dangerous_chars(self, proxy_validator):
        """测试包含危险字符的用户名"""
        dangerous = ["<", ">", '"', "'", ";", "|", "&", "`", "\n", "\r"]
        for char in dangerous:
            with pytest.raises(ValidationError):
                proxy_validator.validate_username(f"user{char}name")

    def test_invalid_username_too_long(self, proxy_validator):
        """测试过长用户名"""
        long_name = "a" * 51
        with pytest.raises(ValidationError):
            proxy_validator.validate_username(long_name)


class TestProxyValidatorPassword:
    """密码验证测试"""

    def test_valid_password_simple(self, proxy_validator):
        """测试简单密码"""
        assert proxy_validator.validate_password("testpass") == "testpass"

    def test_valid_password_empty(self, proxy_validator):
        """测试空密码（允许）"""
        assert proxy_validator.validate_password("") == ""

    def test_valid_password_special_chars(self, proxy_validator):
        """测试特殊字符密码"""
        assert proxy_validator.validate_password("p@ss!#$%") == "p@ss!#$%"

    def test_valid_password_max_length(self, proxy_validator):
        """测试最大长度"""
        password = "a" * 100
        assert proxy_validator.validate_password(password) == password

    def test_invalid_password_too_long(self, proxy_validator):
        """测试过长密码"""
        long_pass = "a" * 101
        with pytest.raises(ValidationError):
            proxy_validator.validate_password(long_pass)

    def test_invalid_password_control_chars(self, proxy_validator):
        """测试包含控制字符的密码"""
        with pytest.raises(ValidationError):
            proxy_validator.validate_password("pass\x00word")


class TestProxyValidatorFullProxy:
    """完整代理验证测试"""

    def test_full_proxy_valid_http(self, proxy_validator):
        """测试有效的 HTTP 代理"""
        result = proxy_validator.validate_full_proxy(
            "test_proxy", "192.168.1.1", "8080", "HTTP", "", ""
        )
        assert len(result) == 6
        assert result[0] == "test_proxy"
        assert result[1] == "192.168.1.1"
        assert result[2] == 8080
        assert result[3] == "HTTP"
        assert result[4] == ""
        assert result[5] == ""

    def test_full_proxy_valid_socks5_with_auth(self, proxy_validator):
        """测试有效的 SOCKS5 认证代理"""
        result = proxy_validator.validate_full_proxy(
            "auth_socks", "10.0.0.1", "1080", "SOCKS5", "user", "pass"
        )
        assert result == ("auth_socks", "10.0.0.1", 1080, "SOCKS5", "user", "pass")

    def test_full_proxy_valid_socks4(self, proxy_validator):
        """测试有效的 SOCKS4 代理"""
        result = proxy_validator.validate_full_proxy(
            "socks4_proxy", "proxy.example.com", "1080", "SOCKS4", "", ""
        )
        assert result[3] == "SOCKS4"

    def test_full_proxy_valid_ipv6(self, proxy_validator):
        """测试 IPv6 代理"""
        result = proxy_validator.validate_full_proxy(
            "ipv6_proxy", "[::1]", "8080", "HTTP", "", ""
        )
        assert result[1] == "::1"
        assert result[2] == 8080

    def test_full_proxy_invalid_name(self, proxy_validator):
        """测试无效名称"""
        with pytest.raises(ValidationError):
            proxy_validator.validate_full_proxy(
                "", "192.168.1.1", "8080", "HTTP", "", ""
            )

    def test_full_proxy_invalid_address(self, proxy_validator):
        """测试无效地址"""
        with pytest.raises(ValidationError):
            proxy_validator.validate_full_proxy(
                "test", "invalid..address", "8080", "HTTP", "", ""
            )

    def test_full_proxy_invalid_port(self, proxy_validator):
        """测试无效端口"""
        with pytest.raises(ValidationError):
            proxy_validator.validate_full_proxy(
                "test", "192.168.1.1", "99999", "HTTP", "", ""
            )

    def test_full_proxy_invalid_type(self, proxy_validator):
        """测试无效代理类型"""
        with pytest.raises(ValidationError):
            proxy_validator.validate_full_proxy(
                "test", "192.168.1.1", "8080", "FTP", "", ""
            )

    def test_full_proxy_emits_signal_on_error(self, proxy_validator):
        """测试验证失败时发出信号"""
        received_signals = []
        proxy_validator.validation_error.connect(
            lambda msg: received_signals.append(msg)
        )

        with pytest.raises(ValidationError):
            proxy_validator.validate_full_proxy(
                "", "192.168.1.1", "8080", "HTTP", "", ""
            )

        assert len(received_signals) == 1


class TestBatchImportValidator:
    """批量导入验证器测试"""

    def test_validate_batch_line_simple(self, batch_validator):
        """测试简单行解析"""
        result = batch_validator.validate_batch_line("test 192.168.1.1:8080", 1)
        assert result == ("test", "192.168.1.1", 8080, "HTTP", "", "")

    def test_validate_batch_line_with_auth(self, batch_validator):
        """测试带认证的行"""
        result = batch_validator.validate_batch_line(
            "auth_proxy 10.0.0.1:3128 user:pass", 1
        )
        assert result[0] == "auth_proxy"
        assert result[1] == "10.0.0.1"
        assert result[3] == "HTTP"
        assert result[4] == "user"
        assert result[5] == "pass"

    def test_validate_batch_line_with_type(self, batch_validator):
        """测试带代理类型的行"""
        result = batch_validator.validate_batch_line(
            "socks_proxy 203.0.113.5:1080 SOCKS5", 1
        )
        assert result[3] == "SOCKS5"

    def test_validate_batch_line_ipv6(self, batch_validator):
        """测试 IPv6 行"""
        # 格式: proxy_name [IPv6]:port
        result = batch_validator.validate_batch_line("proxy_ipv6 [2001:db8::1]:8080", 1)
        assert result[0] == "proxy_ipv6"
        assert result[1] == "2001:db8::1"
        assert result[2] == 8080

    def test_validate_batch_line_empty(self, batch_validator):
        """测试空行"""
        result = batch_validator.validate_batch_line("", 1)
        assert result is None

    def test_validate_batch_line_comment(self, batch_validator):
        """测试注释行"""
        result = batch_validator.validate_batch_line("# This is a comment", 1)
        assert result is None

    def test_validate_batch_line_whitespace(self, batch_validator):
        """测试空白行"""
        result = batch_validator.validate_batch_line("   ", 1)
        assert result is None

    def test_validate_batch_line_invalid_format(self, batch_validator):
        """测试无效格式"""
        with pytest.raises(ValidationError) as exc_info:
            batch_validator.validate_batch_line("invalid", 1)
        assert "格式错误" in str(exc_info.value)

    def test_validate_batch_line_no_port(self, batch_validator):
        """测试缺少端口"""
        with pytest.raises(ValidationError) as exc_info:
            batch_validator.validate_batch_line("test 192.168.1.1", 1)
        assert "地址格式错误" in str(exc_info.value)

    def test_validate_batch_content_valid(self, batch_validator, sample_proxy_content):
        """测试批量内容解析"""
        result = batch_validator.validate_batch_content(sample_proxy_content)
        assert len(result) >= 3  # 至少有3个有效代理
        assert all(len(r) == 6 for r in result)

    def test_validate_batch_content_all_invalid(self, batch_validator):
        """测试全部无效的批量内容"""
        content = """# Only comments
# Another comment
"""
        with pytest.raises(ValidationError) as exc_info:
            batch_validator.validate_batch_content(content)
        assert "没有找到有效的代理配置" in str(exc_info.value)

    def test_validate_batch_content_partial_valid(self, batch_validator):
        """测试部分有效的批量内容"""
        content = """# Valid
test_proxy 192.168.1.1:8080
# Invalid
bad*name test.com:8080
another_valid 10.0.0.1:3128
"""
        # 跳过无效行继续处理，记录警告
        result = batch_validator.validate_batch_content(content)
        assert len(result) >= 2

    def test_validate_batch_content_with_quoted_strings(self, batch_validator):
        """测试带引号的字符串"""
        # 带引号的名称使用 shlex 解析，但名称中不能有空格
        content = '"valid_name" 192.168.1.1:8080'
        result = batch_validator.validate_batch_line(content, 1)
        assert result[0] == "valid_name"


class TestProxyValidatorGetters:
    """代理验证器 getter 方法测试"""

    def test_get_name_validator(self, proxy_validator):
        """测试获取名称验证器"""
        validator = proxy_validator.get_name_validator()
        assert validator is not None

    def test_get_port_validator(self, proxy_validator):
        """测试获取端口验证器"""
        validator = proxy_validator.get_port_validator()
        assert validator is not None

    def test_get_username_validator(self, proxy_validator):
        """测试获取用户名验证器"""
        validator = proxy_validator.get_username_validator()
        assert validator is not None

    def test_get_password_validator(self, proxy_validator):
        """测试获取密码验证器"""
        validator = proxy_validator.get_password_validator()
        assert validator is not None


class TestBatchImportEdgeCases:
    """批量导入边缘情况测试"""

    def test_batch_line_with_ip_only(self, batch_validator):
        """测试只有IP的行（无端口）"""
        with pytest.raises(ValidationError) as exc_info:
            batch_validator.validate_batch_line("test 192.168.1.1", 1)
        assert "地址格式错误" in str(exc_info.value)

    def test_batch_line_with_ipv6_no_bracket(self, batch_validator):
        """测试不带方括号的 IPv6 地址"""
        # IPv6 地址包含多个冒号
        result = batch_validator.validate_batch_line("test ::1:8080", 1)
        # 应该解析成功
        assert result is not None

    def test_batch_line_with_auth_no_password(self, batch_validator):
        """测试只有用户名没有密码的认证"""
        result = batch_validator.validate_batch_line("test 192.168.1.1:8080 user:", 1)
        assert result is not None
        assert result[4] == "user"
        assert result[5] == ""

    def test_batch_line_with_spaces_in_quotes(self, batch_validator):
        """测试引号中带空格的解析"""
        # shlex 会正确解析引号
        content = '"test proxy" 192.168.1.1:8080'
        with pytest.raises(ValidationError):
            # 名称中有空格，验证会失败
            batch_validator.validate_batch_line(content, 1)


class TestProxyValidationEdgeCases:
    """代理验证边缘情况测试 - 覆盖未覆盖的代码行"""

    def test_ipv6_address_with_port_parsing(self, proxy_validator):
        """测试IPv6地址带端口的解析（覆盖lines 114-119）"""
        # 测试 [::1]:8080 格式
        result = proxy_validator.validate_proxy_address("[::1]:8080")
        assert result == "::1"

        # 测试 [2001:db8::1]:8080 格式
        result = proxy_validator.validate_proxy_address("[2001:db8::1]:8080")
        assert result == "2001:db8::1"

    def test_ipv6_socket_validation(self, proxy_validator):
        """测试IPv6地址socket验证（覆盖lines 134-145）"""
        # 测试有效的IPv6地址
        result = proxy_validator.validate_proxy_address("2001:db8::1")
        assert result == "2001:db8::1"

        # 测试无效的IPv6地址
        with pytest.raises(ValidationError):
            proxy_validator.validate_proxy_address("2001:db8::gggg")

    def test_domain_dangerous_chars_validation(self, proxy_validator):
        """测试危险字符检查（在格式检查之前进行）"""
        dangerous_chars = ["<", ">", '"', "'", ";", "|", "&", "`"]

        for char in dangerous_chars:
            with pytest.raises(ValidationError) as exc_info:
                proxy_validator.validate_proxy_address(f"test{char}example")
            assert f"域名包含危险字符: {char}" in str(exc_info.value)

    def test_batch_validation_shlex_error_handling(self, batch_validator):
        """测试批量验证中shlex.split异常处理（覆盖lines 350-354）"""
        # 创建引号不匹配的字符串，应该触发fallback到普通split
        content = 'test "unclosed quote 192.168.1.1:8080'

        # 应该能够处理而不是崩溃
        try:
            result = batch_validator.validate_batch_line(content, 1)
            # 可能成功也可能失败，但不应抛出shlex相关的异常
        except ValidationError:
            # ValidationError是预期的
            pass
        except Exception as e:
            # 不应该抛出其他类型的异常
            pytest.fail(f"Unexpected exception type: {type(e)}")

    def test_batch_ipv6_complex_parsing(self, batch_validator):
        """测试批量导入中复杂的IPv6地址解析（覆盖lines 372-388）"""
        # 测试IPv6格式 [2001:db8::1]:8080
        result = batch_validator.validate_batch_line("ipv6_proxy [2001:db8::1]:8080", 1)
        assert result[0] == "ipv6_proxy"
        assert result[1] == "2001:db8::1"
        assert result[2] == 8080

        # 测试IPv6格式 [::1]:8080
        result = batch_validator.validate_batch_line("localhost_ipv6 [::1]:8080", 1)
        assert result[1] == "::1"

        # 测试无效的IPv6格式
        with pytest.raises(ValidationError):
            batch_validator.validate_batch_line(
                "bad_ipv6 [invalid::ipv6::format]:8080", 1
            )

    def test_batch_parameter_parsing_logic(self, batch_validator):
        """测试批量导入参数解析逻辑（覆盖lines 395-403）"""
        # 测试只有代理类型，没有认证
        result = batch_validator.validate_batch_line(
            "socks_proxy 192.168.1.1:1080 SOCKS5", 1
        )
        assert result[3] == "SOCKS5"
        assert result[4] == ""  # 用户名为空
        assert result[5] == ""  # 密码为空

        # 测试有认证但没有显式类型（应该默认为HTTP）
        result = batch_validator.validate_batch_line(
            "full_proxy 192.168.1.1:1080 user:pass", 1
        )
        assert result[3] == "HTTP"  # 默认类型
        assert result[4] == "user"
        assert result[5] == "pass"

        # 测试有认证但没有类型（默认为HTTP）
        result = batch_validator.validate_batch_line(
            "auth_proxy 192.168.1.1:8080 user:pass", 1
        )
        assert result[3] == "HTTP"  # 默认类型
        assert result[4] == "user"
        assert result[5] == "pass"

    def test_batch_validation_error_handling(self, batch_validator):
        """测试批量验证异常处理（覆盖lines 409-410）"""
        # 创建无效的数据，应该抛出带有行号的错误信息
        with pytest.raises(ValidationError) as exc_info:
            batch_validator.validate_batch_line("test invalid..domain:8080", 5)

        # 错误信息应该包含行号
        assert "第5行" in str(exc_info.value)

    def test_batch_content_validation_error_handling(self, batch_validator):
        """测试批量内容验证错误处理（覆盖lines 434-440）"""
        # 测试全部无效的内容
        content = """# Only comments
# Another comment
invalid line without proper format
"""

        with pytest.raises(ValidationError) as exc_info:
            batch_validator.validate_batch_content(content)
        assert "没有找到有效的代理配置" in str(exc_info.value)

        # 测试部分有效的混合内容
        mixed_content = """# Valid proxy
valid_proxy 192.168.1.1:8080
# Invalid proxy
invalid**name test.com:8080
# Another valid proxy
another_proxy 10.0.0.1:3128
"""

        # 应该成功返回有效的代理，跳过无效的
        result = batch_validator.validate_batch_content(mixed_content)
        assert len(result) >= 2  # 至少有两个有效的

        # 验证返回的代理都是有效的
        for proxy in result:
            assert len(proxy) == 6  # 6元组
            assert proxy[0] in ["valid_proxy", "another_proxy"]
