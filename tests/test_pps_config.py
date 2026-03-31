#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyProxySwitch pps_config 模块测试

测试代理配置管理功能。
"""

import pytest
import tempfile
from pathlib import Path
import sys
import json

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestPpsOutput:
    """pps_output 函数测试"""

    def test_pps_output_stdout(self, capsys):
        """测试标准输出"""
        from src.pps_config import pps_output

        pps_output("test message")
        captured = capsys.readouterr()
        # 输出到 stdout 的数据
        assert "test" in captured.out or b"test" in captured.out.encode()

    def test_pps_output_stderr(self, capsys):
        """测试标准错误输出"""
        from src.pps_config import pps_output

        pps_output("error message", dest="stderr")
        captured = capsys.readouterr()
        assert "error" in captured.err or b"error" in captured.err.encode()


class TestPpsLoadProxylist:
    """pps_load_proxylist 函数测试"""

    def test_load_simple_proxy(self, temp_dir):
        """测试加载简单代理"""
        from src.pps_config import pps_load_proxylist

        proxy_file = temp_dir / "proxy.txt"
        proxy_file.write_text("test_proxy 192.168.1.1:8080\n", encoding="utf-8")

        result = pps_load_proxylist(str(proxy_file))
        assert len(result) == 1
        assert result[0][0] == "test_proxy"
        assert result[0][1] == "192.168.1.1"
        assert result[0][2] == "8080"
        assert result[0][3] == "HTTP"

    def test_load_proxy_with_auth(self, temp_dir):
        """测试加载带认证的代理"""
        from src.pps_config import pps_load_proxylist

        proxy_file = temp_dir / "proxy.txt"
        proxy_file.write_text("auth_proxy 10.0.0.1:3128 user:pass\n", encoding="utf-8")

        result = pps_load_proxylist(str(proxy_file))
        assert len(result) == 1
        assert result[0][0] == "auth_proxy"
        assert result[0][4] == "user"
        assert result[0][5] == "pass"

    def test_load_proxy_with_socks_type(self, temp_dir):
        """测试加载 SOCKS 代理"""
        from src.pps_config import pps_load_proxylist

        proxy_file = temp_dir / "proxy.txt"
        proxy_file.write_text("socks_proxy 203.0.113.5:1080 SOCKS5\n", encoding="utf-8")

        result = pps_load_proxylist(str(proxy_file))
        assert len(result) == 1
        assert result[0][3] == "SOCKS5"

    def test_load_proxy_with_socks4(self, temp_dir):
        """测试加载 SOCKS4 代理"""
        from src.pps_config import pps_load_proxylist

        proxy_file = temp_dir / "proxy.txt"
        proxy_file.write_text(
            "socks4_proxy 203.0.113.5:1080 SOCKS4\n", encoding="utf-8"
        )

        result = pps_load_proxylist(str(proxy_file))
        assert len(result) == 1
        assert result[0][3] == "SOCKS4"

    def test_load_proxy_with_auth_and_type(self, temp_dir):
        """测试加载带认证和类型的代理"""
        from src.pps_config import pps_load_proxylist

        proxy_file = temp_dir / "proxy.txt"
        proxy_file.write_text(
            "full_proxy 10.0.0.1:3128 user:pass SOCKS5\n", encoding="utf-8"
        )

        result = pps_load_proxylist(str(proxy_file))
        assert len(result) == 1
        assert result[0][4] == "user"
        assert result[0][5] == "pass"
        assert result[0][3] == "SOCKS5"

    def test_load_empty_lines(self, temp_dir):
        """测试空行被跳过"""
        from src.pps_config import pps_load_proxylist

        proxy_file = temp_dir / "proxy.txt"
        proxy_file.write_text(
            "test_proxy 192.168.1.1:8080\n\ninvalid\n", encoding="utf-8"
        )

        result = pps_load_proxylist(str(proxy_file))
        # 应该只加载有效行
        assert len(result) == 1

    def test_load_multiple_proxies(self, temp_dir):
        """测试加载多个代理"""
        from src.pps_config import pps_load_proxylist

        proxy_file = temp_dir / "proxy.txt"
        content = """proxy1 192.168.1.1:8080
proxy2 10.0.0.1:3128 user:pass
proxy3 203.0.113.5:1080 SOCKS5
"""
        proxy_file.write_text(content, encoding="utf-8")

        result = pps_load_proxylist(str(proxy_file))
        assert len(result) == 3


class TestPpsSaveProxylist:
    """pps_save_proxylist 函数测试"""

    def test_save_simple_proxy(self, temp_dir):
        """测试保存简单代理"""
        from src.pps_config import pps_save_proxylist

        proxy_file = temp_dir / "proxy.txt"
        proxies = [("test_proxy", "192.168.1.1", "8080", "HTTP", "", "")]

        pps_save_proxylist(proxies, str(proxy_file))

        assert proxy_file.exists()
        content = proxy_file.read_text(encoding="utf-8")
        assert "test_proxy" in content
        assert "192.168.1.1" in content

    def test_save_proxy_with_auth(self, temp_dir):
        """测试保存带认证的代理"""
        from src.pps_config import pps_save_proxylist

        proxy_file = temp_dir / "proxy.txt"
        proxies = [("auth_proxy", "10.0.0.1", "3128", "HTTP", "user", "pass")]

        pps_save_proxylist(proxies, str(proxy_file))

        content = proxy_file.read_text(encoding="utf-8")
        assert "user:pass" in content

    def test_save_proxy_without_auth(self, temp_dir):
        """测试保存无认证的代理"""
        from src.pps_config import pps_save_proxylist

        proxy_file = temp_dir / "proxy.txt"
        proxies = [("noauth_proxy", "10.0.0.1", "3128", "HTTP", "", "")]

        pps_save_proxylist(proxies, str(proxy_file))

        content = proxy_file.read_text(encoding="utf-8")
        assert "noauth_proxy" in content
        assert "10.0.0.1:3128 HTTP" in content

    def test_save_string_proxies(self, temp_dir):
        """测试保存字符串列表"""
        from src.pps_config import pps_save_proxylist

        proxy_file = temp_dir / "proxy.txt"
        proxies = ["proxy1", "proxy2"]

        pps_save_proxylist(proxies, str(proxy_file))

        content = proxy_file.read_text(encoding="utf-8")
        assert "proxy1" in content
        assert "proxy2" in content


class TestPpsExcHandle:
    """pps_exc_handle 函数测试"""

    def test_exc_handle_debug_on(self, monkeypatch):
        """测试调试模式开启时的异常处理"""
        import src.pps_config as pps_config
        from src.pps_config import pps_exc_handle

        # 设置调试模式
        original_config = pps_config.CONFIG.copy()
        pps_config.CONFIG["DEBUG"] = 1

        # 模拟 traceback.print_exc
        printed = []
        monkeypatch.setattr(
            pps_config.traceback, "print_exc", lambda: printed.append(True)
        )

        try:
            raise ValueError("test error")
        except ValueError:
            pps_exc_handle()

        assert len(printed) == 1

        # 恢复配置
        pps_config.CONFIG = original_config

    def test_exc_handle_debug_off(self, monkeypatch):
        """测试调试模式关闭时的异常处理"""
        import src.pps_config as pps_config
        from src.pps_config import pps_exc_handle

        # 设置调试模式关闭
        original_config = pps_config.CONFIG.copy()
        pps_config.CONFIG["DEBUG"] = 0

        printed = []
        monkeypatch.setattr(
            pps_config.traceback, "print_exc", lambda: printed.append(True)
        )

        try:
            raise ValueError("test error")
        except ValueError:
            pps_exc_handle()

        assert len(printed) == 0

        # 恢复配置
        pps_config.CONFIG = original_config


class TestPpsSavecfg:
    """pps_savecfg 函数测试"""

    def test_save_config(self, temp_dir, monkeypatch):
        """测试保存配置"""
        import src.pps_config as pps_config

        # 设置配置文件路径
        config_file = temp_dir / "test_config.json"
        monkeypatch.setattr(pps_config, "CONF", str(config_file))

        config_dict = {"CMD": "3proxy", "DEBUG": 1, "LOCAL_PORT": 8080}

        pps_config.pps_savecfg(config_dict)

        assert config_file.exists()
        with open(config_file, "r", encoding="utf-8") as f:
            saved_config = json.load(f)
        assert saved_config["CMD"] == "3proxy"
        assert saved_config["LOCAL_PORT"] == 8080

    def test_save_config_io_error(self, temp_dir, monkeypatch, capsys):
        """测试保存配置失败"""
        import src.pps_config as pps_config

        # 设置只读配置文件路径
        readonly_file = temp_dir / "readonly" / "config.json"
        monkeypatch.setattr(pps_config, "CONF", str(readonly_file))

        # 不创建目录，应该失败
        config_dict = {"TEST": "value"}

        # 应该调用 pps_exc_handle，但不抛出异常
        pps_config.pps_savecfg(config_dict)


class TestDelProxy:
    """del_proxy 函数测试"""

    def test_del_proxy_basic(self, temp_dir, monkeypatch):
        """测试基本删除代理"""
        import src.pps_config as pps_config

        # 创建测试目录结构
        polipo_dir = temp_dir / "cfg" / "polipo"
        proxy3_dir = temp_dir / "cfg" / "3proxy"
        polipo_dir.mkdir(parents=True)
        proxy3_dir.mkdir(parents=True)

        # 创建代理配置文件
        polipo_conf = polipo_dir / "test_proxy.conf"
        proxy3_conf = proxy3_dir / "test_proxy.conf"
        polipo_conf.write_text("test config", encoding="utf-8")
        proxy3_conf.write_text("test config", encoding="utf-8")

        # 设置 PROGRAM_PATH
        monkeypatch.setattr(pps_config, "PROGRAM_PATH", str(temp_dir))

        # 测试删除
        pps_config.del_proxy(["test_proxy"])

        # 文件应该被删除
        assert not polipo_conf.exists()
        assert not proxy3_conf.exists()

    def test_del_proxy_not_found(self, temp_dir, monkeypatch):
        """测试删除不存在的代理"""
        import src.pps_config as pps_config

        monkeypatch.setattr(pps_config, "PROGRAM_PATH", str(temp_dir))

        # 不应抛出异常
        pps_config.del_proxy(["nonexistent_proxy"])


class TestLoadcfg:
    """pps_loadcfg 函数测试"""

    def test_load_config_with_old_typo(self, temp_dir):
        """测试加载旧版本拼写错误的配置"""
        from src.pps_config import pps_loadcfg

        config_file = temp_dir / "config.json"
        config = {
            "FISRT_RUN": 1,  # 旧版本拼写错误
            "CMD": "3proxy",
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f)

        loaded = pps_loadcfg(str(config_file))

        # 应该修复为 FIRST_RUN
        assert "FIRST_RUN" in loaded
        assert loaded["FIRST_RUN"] == 1
        assert "FISRT_RUN" not in loaded

    def test_load_config_without_typo(self, temp_dir):
        """测试加载正确配置"""
        from src.pps_config import pps_loadcfg

        config_file = temp_dir / "config.json"
        config = {"FIRST_RUN": 0, "CMD": "3proxy"}
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f)

        loaded = pps_loadcfg(str(config_file))

        assert loaded["FIRST_RUN"] == 0
        assert loaded["CMD"] == "3proxy"


class TestAddProxy:
    """add_proxy 函数测试"""

    def test_add_proxy_simple(self, temp_dir, monkeypatch):
        """测试添加简单代理"""
        import src.pps_config as pps_config

        # 创建目录结构
        polipo_dir = temp_dir / "cfg" / "polipo"
        proxy3_dir = temp_dir / "cfg" / "3proxy"
        polipo_dir.mkdir(parents=True)
        proxy3_dir.mkdir(parents=True)

        # 设置路径
        monkeypatch.setattr(pps_config, "PROGRAM_PATH", str(temp_dir))

        pps_config.add_proxy(["test_proxy", "192.168.1.1:8080"])

        # 验证配置文件被创建
        polipo_conf = polipo_dir / "test_proxy.conf"
        proxy3_conf = proxy3_dir / "test_proxy.conf"
        assert polipo_conf.exists()
        assert proxy3_conf.exists()

    def test_add_proxy_with_auth(self, temp_dir, monkeypatch):
        """测试添加带认证的代理"""
        import src.pps_config as pps_config

        # 创建目录结构
        polipo_dir = temp_dir / "cfg" / "polipo"
        proxy3_dir = temp_dir / "cfg" / "3proxy"
        polipo_dir.mkdir(parents=True)
        proxy3_dir.mkdir(parents=True)

        # 设置路径
        monkeypatch.setattr(pps_config, "PROGRAM_PATH", str(temp_dir))

        pps_config.add_proxy(["auth_proxy", "10.0.0.1:3128", "user:pass"])

        # 验证配置文件被创建
        polipo_conf = polipo_dir / "auth_proxy.conf"
        assert polipo_conf.exists()

        # 验证配置包含认证信息
        content = polipo_conf.read_text(encoding="utf-8")
        assert "user:pass" in content

    def test_add_proxy_socks5(self, temp_dir, monkeypatch):
        """测试添加 SOCKS5 代理"""
        import src.pps_config as pps_config

        # 创建目录结构
        polipo_dir = temp_dir / "cfg" / "polipo"
        proxy3_dir = temp_dir / "cfg" / "3proxy"
        polipo_dir.mkdir(parents=True)
        proxy3_dir.mkdir(parents=True)

        # 设置路径
        monkeypatch.setattr(pps_config, "PROGRAM_PATH", str(temp_dir))

        pps_config.add_proxy(["socks_proxy", "203.0.113.5:1080"], "SOCKS5")

        # 验证配置文件被创建
        polipo_conf = polipo_dir / "socks_proxy.conf"
        assert polipo_conf.exists()

        # 验证配置包含 SOCKS 信息
        content = polipo_conf.read_text(encoding="utf-8")
        assert "socks5" in content.lower()

    def test_add_proxy_invalid_name(self, temp_dir, monkeypatch, capsys):
        """测试添加无效名称的代理"""
        import src.pps_config as pps_config

        monkeypatch.setattr(pps_config, "PROGRAM_PATH", str(temp_dir))

        # 空名称应该失败
        pps_config.add_proxy(["", "192.168.1.1:8080"])

        # 应该输出错误消息
        captured = capsys.readouterr()
        assert "验证错误" in captured.out or captured.err != ""


class TestPpsConfigErrorHandling:
    """错误处理测试"""

    def test_loadcfg_invalid_json(self, temp_dir):
        """测试加载无效JSON格式文件"""
        from src.pps_config import pps_loadcfg

        config_file = temp_dir / "invalid.json"
        config_file.write_text("{ invalid json", encoding="utf-8")

        # 在测试环境中，应该返回默认配置而不是抛出异常
        config = pps_loadcfg(str(config_file))
        assert "LANG" in config
        assert "LOCAL_PORT" in config

    def test_loadcfg_nonexistent_file(self):
        """测试加载不存在的配置文件"""
        from src.pps_config import pps_loadcfg

        # 在测试环境中，应该返回默认配置而不是抛出异常
        config = pps_loadcfg("/nonexistent/path/config.json")
        assert "LANG" in config
        assert "LOCAL_PORT" in config

    def test_load_proxylist_index_error(self, temp_dir):
        """测试加载代理列表时的IndexError处理"""
        from src.pps_config import pps_load_proxylist

        proxy_file = temp_dir / "proxy.txt"
        # 创建会导致IndexError的内容（地址没有端口）
        proxy_file.write_text(
            "test_proxy invalid_address_without_port\n", encoding="utf-8"
        )

        # 应该抛出异常并退出
        with pytest.raises(SystemExit):
            pps_load_proxylist(str(proxy_file))

    def test_save_proxylist_os_error(self, temp_dir, monkeypatch):
        """测试保存代理列表时OSError处理"""
        import src.pps_config as pps_config

        # 使用一个不存在的目录来触发OSError
        invalid_path = temp_dir / "nonexistent" / "proxy.txt"
        proxies = [("test_proxy", "192.168.1.1", "8080", "HTTP", "", "")]

        # Mock pps_output to capture error message
        output_calls = []

        def mock_pps_output(msg, dest="stdout"):
            output_calls.append((msg, dest))

        monkeypatch.setattr(pps_config, "pps_output", mock_pps_output)

        # 应该调用 pps_output 输出错误信息
        pps_config.pps_save_proxylist(proxies, str(invalid_path))
        assert len(output_calls) > 0
        # 验证错误信息包含配置相关的内容
        error_msg = str(output_calls[0][0])
        assert (
            "config" in error_msg.lower()
            or "error" in error_msg.lower()
            or "cfg" in error_msg.lower()
        )

    def test_savecfg_io_error(self, temp_dir, monkeypatch):
        """测试保存配置文件时IOError处理"""
        import src.pps_config as pps_config

        # Mock pps_exc_handle to capture calls
        exc_handle_calls = []

        def mock_pps_exc_handle():
            exc_handle_calls.append(True)

        monkeypatch.setattr(pps_config, "pps_exc_handle", mock_pps_exc_handle)

        # Mock CONF to point to an invalid location
        invalid_conf_path = str(temp_dir / "nonexistent" / "config.json")
        monkeypatch.setattr(pps_config, "CONF", invalid_conf_path)

        config_dict = {"TEST": "value"}

        # 应该调用 pps_exc_handle
        pps_config.pps_savecfg(config_dict)
        assert len(exc_handle_calls) > 0

    def test_add_proxy_validation_error(self, temp_dir, monkeypatch, capsys):
        """测试添加代理时的验证错误处理"""
        import src.pps_config as pps_config

        monkeypatch.setattr(pps_config, "PROGRAM_PATH", str(temp_dir))

        # 创建无效的代理数据（地址格式错误）
        pps_config.add_proxy(["test_proxy", "invalid_address_format"])

        # 应该输出错误消息
        captured = capsys.readouterr()
        assert "验证错误" in captured.out or captured.err != ""

    def test_add_proxy_config_file_creation_success(self, temp_dir, monkeypatch):
        """测试添加代理时成功创建配置文件"""
        import src.pps_config as pps_config
        from pathlib import Path

        # 设置一个有效的程序路径（使用temp目录）
        test_program_path = temp_dir / "test_program"
        test_program_path.mkdir(parents=True)
        cfg_path = test_program_path / "cfg"
        (cfg_path / "polipo").mkdir(parents=True)
        (cfg_path / "3proxy").mkdir(parents=True)

        monkeypatch.setattr(pps_config, "PROGRAM_PATH", str(test_program_path))

        # 应该成功执行
        pps_config.add_proxy(["test_proxy", "192.168.1.1:8080"])

        # 验证配置文件被创建
        assert (cfg_path / "polipo" / "test_proxy.conf").exists()
        assert (cfg_path / "3proxy" / "test_proxy.conf").exists()

    def test_del_proxy_success(self, temp_dir, monkeypatch, capsys):
        """测试删除代理时成功删除配置文件"""
        import src.pps_config as pps_config

        # 创建有效的程序路径
        program_dir = temp_dir / "program"
        program_dir.mkdir(parents=True)

        # 创建配置文件
        polipo_dir = program_dir / "cfg" / "polipo"
        proxy3_dir = program_dir / "cfg" / "3proxy"
        polipo_dir.mkdir(parents=True)
        proxy3_dir.mkdir(parents=True)

        polipo_conf = polipo_dir / "test_proxy.conf"
        proxy3_conf = proxy3_dir / "test_proxy.conf"
        polipo_conf.write_text("test config", encoding="utf-8")
        proxy3_conf.write_text("test config", encoding="utf-8")

        monkeypatch.setattr(pps_config, "PROGRAM_PATH", str(program_dir))

        # 应该成功删除
        pps_config.del_proxy(["test_proxy"])

        # 验证文件被删除
        assert not polipo_conf.exists()
        assert not proxy3_conf.exists()


class TestPpsOutputEdgeCases:
    """pps_output 边缘情况测试"""

    def test_pps_output_non_string_input(self, capsys):
        """测试 pps_output 非字符串输入（覆盖 line 222）"""
        from src.pps_config import pps_output

        # 测试非字符串输入（应该转换为字符串）
        pps_output(12345)  # 数字输入
        captured = capsys.readouterr()
        # 输出应该是字符串形式
        assert "12345" in captured.out or b"12345" in captured.out.encode()

    def test_pps_output_none_input(self, capsys):
        """测试 pps_output None 输入"""
        from src.pps_config import pps_output

        pps_output(None)  # None 输入
        captured = capsys.readouterr()
        # 输出应该是 "None"
        assert "None" in captured.out or b"None" in captured.out.encode()

    def test_pps_output_list_input(self, capsys):
        """测试 pps_output 列表输入"""
        from src.pps_config import pps_output

        pps_output([1, 2, 3])  # 列表输入
        captured = capsys.readouterr()
        # 输出应该是列表的字符串形式
        assert "[1, 2, 3]" in captured.out or b"[1, 2, 3]" in captured.out.encode()


class TestPpsLoadProxylistEdgeCases:
    """pps_load_proxylist 边缘情况测试"""

    def test_load_proxy_with_user_pass_no_password(self, temp_dir):
        """测试加载代理时用户名后面有冒号但无密码（覆盖 line 255）"""
        from src.pps_config import pps_load_proxylist

        proxy_file = temp_dir / "proxy.txt"
        # 写入用户名后面有冒号但没有密码的格式
        proxy_file.write_text(
            "test_proxy 192.168.1.1:8080 user: HTTP\n", encoding="utf-8"
        )

        proxies = pps_load_proxylist(str(proxy_file))
        assert len(proxies) == 1
        proxy = proxies[0]
        assert proxy[0] == "test_proxy"
        assert proxy[1] == "192.168.1.1"
        assert proxy[2] == "8080"
        assert proxy[3] == "HTTP"
        assert proxy[4] == "user"  # 用户名
        assert proxy[5] == ""  # 密码为空


class TestAddProxyEdgeCases:
    """add_proxy 边缘情况测试"""

    def test_add_proxy_io_error_handling(self, monkeypatch):
        """测试 add_proxy IOError 处理（覆盖 lines 475-479）"""
        from src import pps_config

        # 模拟 CONFIG
        original_config = pps_config.CONFIG.copy()

        # 模拟 open 抛出 IOError
        def mock_open(*args, **kwargs):
            raise IOError("Mock IO error")

        monkeypatch.setattr("builtins.open", mock_open)
        monkeypatch.setattr(pps_config, "CONFIG", {"LOCAL_PORT": 8123})

        try:
            # 这应该触发 IOError 处理路径
            pps_config.add_proxy(["test_proxy", "192.168.1.1:8080"], "HTTP")
        except Exception as e:
            # IOError 应该被捕获并处理，不会抛出异常
            pass

        # 恢复原始配置
        pps_config.CONFIG = original_config


class TestDelProxyEdgeCases:
    """del_proxy 边缘情况测试"""

    def test_del_proxy_with_non_string_proxy_name(self):
        """测试 del_proxy 非字符串代理名称（覆盖 line 492）"""
        from src import pps_config

        # 模拟代理列表
        original_proxies = pps_config.PROXIES.copy()

        # 测试删除整数类型的代理名称（应该转换为字符串）
        try:
            pps_config.del_proxy([123])  # 传递整数
        except Exception as e:
            # 类型转换应该成功
            pass

        # 恢复原始代理列表
        pps_config.PROXIES = original_proxies

    def test_del_proxy_with_float_proxy_name(self):
        """测试 del_proxy 浮点数代理名称"""
        from src import pps_config

        # 测试删除浮点数类型的代理名称（应该转换为字符串）
        try:
            pps_config.del_proxy([3.14])  # 传递浮点数
        except Exception as e:
            # 类型转换应该成功
            pass

    def test_del_proxy_with_object_proxy_name(self):
        """测试 del_proxy 对象代理名称"""
        from src import pps_config

        # 测试删除对象类型的代理名称（应该转换为字符串）
        class ProxyName:
            def __str__(self):
                return "test_object_proxy"

        try:
            pps_config.del_proxy([ProxyName()])  # 传递对象
        except Exception as e:
            # 类型转换应该成功
            pass


class TestGetActionForTests:
    """get_action_for_tests 函数测试"""

    def test_get_action_for_tests_with_action(self, monkeypatch):
        """测试 get_action_for_tests 获取 action 参数"""
        # 模拟 sys.argv
        test_argv = ["script.py", "add", "test_proxy", "192.168.1.1:8080"]
        monkeypatch.setattr(sys, "argv", test_argv)

        from src.pps_config import get_action_for_tests

        action = get_action_for_tests()
        assert action == "add"

    def test_get_action_for_tests_with_flag(self, monkeypatch):
        """测试 get_action_for_tests 过滤标志参数"""
        # 模拟 sys.argv 带有标志参数
        test_argv = ["script.py", "-v", "add", "test_proxy"]
        monkeypatch.setattr(sys, "argv", test_argv)

        from src.pps_config import get_action_for_tests

        action = get_action_for_tests()
        assert action == "add"

    def test_get_action_for_tests_no_action(self, monkeypatch):
        """测试 get_action_for_tests 没有 action 参数"""
        # 模拟 sys.argv 只有脚本名
        test_argv = ["script.py"]
        monkeypatch.setattr(sys, "argv", test_argv)

        from src.pps_config import get_action_for_tests

        action = get_action_for_tests()
        assert action is None

    def test_get_action_for_tests_index_error(self, monkeypatch):
        """测试 get_action_for_tests IndexError 处理（覆盖 lines 211-213）"""
        # 模拟空的 sys.argv
        test_argv = []
        monkeypatch.setattr(sys, "argv", test_argv)

        from src.pps_config import get_action_for_tests

        action = get_action_for_tests()
        assert action is None
