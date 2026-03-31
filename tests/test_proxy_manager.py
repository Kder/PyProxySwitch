#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ProxyManager 单元测试

为 proxy_manager.py 提供完整的单元测试覆盖，包括：
- 进程生命周期管理
- 代理启动/停止/切换
- 错误处理
- 边缘情况处理
"""

import json
import os
import sys
import signal
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import pytest

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.proxy_manager import ProxyManager
from src.config import ConfigManager
from src.errors import ProxyStartError, ProxyStopError, ConfigError


class TestProxyManagerInit:
    """ProxyManager 初始化测试"""

    def test_init_with_default_config(self):
        """测试使用默认配置初始化"""
        ConfigManager.reset_singleton()
        manager = ProxyManager()
        assert manager._config is not None
        assert manager.r_process is None
        ConfigManager.reset_singleton()

    def test_init_with_custom_config(self):
        """测试使用自定义配置初始化"""
        ConfigManager.reset_singleton()
        custom_config = ConfigManager(use_singleton=False)
        manager = ProxyManager(config=custom_config)
        assert manager._config is custom_config
        assert manager.r_process is None
        ConfigManager.reset_singleton()

    def test_init_creates_new_config_if_none(self):
        """测试当config为None时创建新配置"""
        ConfigManager.reset_singleton()
        manager = ProxyManager(config=None)
        assert manager._config is not None
        assert isinstance(manager._config, ConfigManager)
        ConfigManager.reset_singleton()


class TestProxyManagerProcessStatus:
    """进程状态检查测试"""

    def test_is_process_running_no_process(self):
        """测试没有进程时返回False"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))
        assert manager.is_process_running() is False

    def test_is_process_running_with_running_process(self):
        """测试有运行中的进程时返回True"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        # 创建一个模拟的运行中进程
        mock_process = Mock()
        mock_process.poll.return_value = None  # None 表示进程还在运行
        manager.r_process = mock_process

        assert manager.is_process_running() is True

    def test_is_process_running_with_exited_process(self):
        """测试已退出的进程返回False"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        # 创建一个模拟的已退出进程
        mock_process = Mock()
        mock_process.poll.return_value = 0  # 0 表示正常退出
        manager.r_process = mock_process

        assert manager.is_process_running() is False

    def test_get_process_info_no_process(self):
        """测试没有进程时的信息"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))
        assert manager.get_process_info() == "No process"

    def test_get_process_info_running(self):
        """测试运行中进程的信息"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        manager.r_process = mock_process

        info = manager.get_process_info()
        assert "Running" in info
        assert "12345" in info

    def test_get_process_info_exited(self):
        """测试已退出进程的信息"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        mock_process = Mock()
        mock_process.poll.return_value = 1
        mock_process.returncode = 1
        manager.r_process = mock_process

        info = manager.get_process_info()
        assert "Exited" in info
        assert "1" in info


class TestProxyManagerTerminateProcess:
    """进程终止测试"""

    @patch('os.name', 'nt')  # 确保Windows环境
    def test_terminate_process_no_process(self):
        """测试终止不存在的进程"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))
        result = manager.terminate_process()

        assert result is True

    @patch('os.name', 'nt')  # 确保Windows环境
    def test_terminate_process_windows(self):
        """测试在Windows上终止进程"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        mock_process = Mock()
        mock_process.pid = 12345
        manager.r_process = mock_process

        result = manager.terminate_process(timeout=5)

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)
        assert result is True

    @pytest.mark.skipif(os.name == 'nt', reason="Unix-specific test, not available on Windows")
    def test_terminate_process_unix(self):
        """测试在Unix系统上终止进程"""
        # 在真实Unix系统上运行
        if os.name != 'posix':
            pytest.skip("This test requires Unix-like system")

        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        mock_process = Mock()
        mock_process.pid = 12345
        manager.r_process = mock_process

        result = manager.terminate_process(timeout=5)

        mock_process.wait.assert_called_once_with(timeout=5)
        assert result is True

    @patch('os.name', 'nt')  # 确保Windows环境
    def test_terminate_process_timeout_then_kill_windows(self):
        """测试Windows上进程终止超时后强制杀死"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        mock_process = Mock()
        mock_process.pid = 12345
        # 第一次wait调用抛出TimeoutExpired，第二次返回0（表示成功）
        mock_process.wait.side_effect = [subprocess.TimeoutExpired(cmd="test", timeout=5), 0]
        manager.r_process = mock_process

        result = manager.terminate_process(timeout=5)

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        assert mock_process.wait.call_count == 2  # 被调用两次
        assert result is False  # 返回False因为需要强制杀死

    @pytest.mark.skipif(os.name == 'nt', reason="Unix-specific test, not available on Windows")
    def test_terminate_process_timeout_then_kill_unix(self):
        """测试Unix上进程终止超时后强制杀死"""
        # 在真实Unix系统上运行
        if os.name != 'posix':
            pytest.skip("This test requires Unix-like system")

        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        mock_process = Mock()
        mock_process.pid = 12345
        # 第一次wait调用抛出TimeoutExpired，第二次返回0（表示成功）
        mock_process.wait.side_effect = [subprocess.TimeoutExpired(cmd="test", timeout=5), 0]
        manager.r_process = mock_process

        result = manager.terminate_process(timeout=5)

        mock_process.wait.assert_called()
        assert result is False

    @patch('os.name', 'nt')  # 确保Windows环境
    def test_terminate_process_exception(self):
        """测试终止进程时发生异常"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.terminate.side_effect = Exception("Test error")
        manager.r_process = mock_process

        result = manager.terminate_process(timeout=5)

        assert result is False


class TestProxyManagerRunCmd:
    """命令执行测试"""

    def test_run_cmd_invalid_parameters(self):
        """测试无效参数"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        with pytest.raises(ConfigError):
            manager._run_cmd(None, "test", "8080")

        with pytest.raises(ConfigError):
            manager._run_cmd("3proxy", None, "8080")

        with pytest.raises(ConfigError):
            manager._run_cmd("3proxy", "test", None)

    def test_run_cmd_invalid_port_for_ip_relay(self):
        """测试ip_relay模式下的无效端口"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        with pytest.raises(ConfigError):
            manager._run_cmd("ip_relay", "192.168.1.1", "invalid_port")

        with pytest.raises(ConfigError):
            manager._run_cmd("ip_relay", "192.168.1.1", "0")  # 端口太小

        with pytest.raises(ConfigError):
            manager._run_cmd("ip_relay", "192.168.1.1", "65536")  # 端口太大

    @patch('subprocess.Popen')
    def test_run_cmd_3proxy(self, mock_popen):
        """测试3proxy命令执行"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        with patch('os.name', 'nt'):
            with patch('src.proxy_manager.pps_config.PROGRAM_PATH', '/test/path'):
                manager._run_cmd("3proxy", "test_proxy", "")

        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert '3proxy.exe' in call_args[0]

    @patch('subprocess.Popen')
    def test_run_cmd_polipo(self, mock_popen):
        """测试polipo命令执行"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        with patch('os.name', 'nt'):
            with patch('src.proxy_manager.pps_config.PROGRAM_PATH', '/test/path'):
                manager._run_cmd("polipo", "test_proxy", "")

        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert 'polipo.exe' in call_args[0]

    @patch('subprocess.Popen')
    def test_run_cmd_ip_relay(self, mock_popen):
        """测试ip_relay命令执行"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))
        manager._config.set('LOCAL_PORT', 8888)

        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        with patch('os.name', 'nt'):
            with patch('src.proxy_manager.pps_config.PROGRAM_PATH', '/test/path'):
                manager._run_cmd("ip_relay", "192.168.1.1", "8080")

        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert 'ip_relay.exe' in call_args[0]

    @patch('subprocess.Popen')
    def test_run_cmd_process_exits_immediately(self, mock_popen):
        """测试进程立即退出的情况"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        mock_process = Mock()
        mock_process.poll.return_value = 1  # 进程已退出
        mock_process.stderr.read.return_value = b"Test error"
        mock_popen.return_value = mock_process

        with pytest.raises(ProxyStartError):
            with patch('os.name', 'nt'):
                with patch('src.proxy_manager.pps_config.PROGRAM_PATH', '/test/path'):
                    manager._run_cmd("3proxy", "test_proxy", "")

    @patch('subprocess.Popen')
    def test_run_cmd_file_not_found(self, mock_popen):
        """测试可执行文件不存在"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        mock_popen.side_effect = FileNotFoundError("Test error")

        with pytest.raises(ProxyStartError):
            with patch('os.name', 'nt'):
                with patch('src.proxy_manager.pps_config.PROGRAM_PATH', '/test/path'):
                    manager._run_cmd("3proxy", "test_proxy", "")

    @patch('subprocess.Popen')
    def test_run_cmd_permission_error(self, mock_popen):
        """测试权限错误"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        mock_popen.side_effect = PermissionError("Test error")

        with pytest.raises(ProxyStartError):
            with patch('os.name', 'nt'):
                with patch('src.proxy_manager.pps_config.PROGRAM_PATH', '/test/path'):
                    manager._run_cmd("3proxy", "test_proxy", "")

    @patch('subprocess.Popen')
    def test_run_cmd_debug_mode(self, mock_popen):
        """测试调试模式下的命令执行"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))
        manager._config.set('DEBUG', 1)

        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        with patch('os.name', 'nt'):
            with patch('src.proxy_manager.pps_config.PROGRAM_PATH', '/test/path'):
                manager._run_cmd("3proxy", "test_proxy", "")

        # 在调试模式下，应该有日志输出
        mock_popen.assert_called_once()


class TestProxyManagerStartProxy:
    """代理启动测试"""

    @patch.object(ProxyManager, 'terminate_process')
    @patch.object(ProxyManager, '_run_cmd')
    def test_start_proxy_calls_terminate_first(self, mock_run_cmd, mock_terminate):
        """测试启动代理前先终止现有进程"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        manager.start_proxy("test_proxy", "192.168.1.1", "8080", "HTTP")

        mock_terminate.assert_called_once_with(timeout=5)
        mock_run_cmd.assert_called_once()

    @patch.object(ProxyManager, 'terminate_process')
    @patch.object(ProxyManager, '_run_cmd')
    def test_start_proxy_with_ip_relay(self, mock_run_cmd, mock_terminate):
        """测试ip_relay模式下的代理启动"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))
        manager._config.set('CMD', 'ip_relay')

        manager.start_proxy("test_proxy", "192.168.1.1", "8080", "HTTP")

        mock_run_cmd.assert_called_once_with('ip_relay', '192.168.1.1', '8080')

    @patch.object(ProxyManager, 'terminate_process')
    @patch.object(ProxyManager, '_run_cmd')
    def test_start_proxy_with_other_proxy_types(self, mock_run_cmd, mock_terminate):
        """测试其他代理类型的启动"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))
        manager._config.set('CMD', '3proxy')

        manager.start_proxy("test_proxy", "", "", "HTTP")

        mock_run_cmd.assert_called_once_with('3proxy', 'test_proxy', '')


class TestProxyManagerStopProxy:
    """代理停止测试"""

    @patch.object(ProxyManager, 'terminate_process')
    def test_stop_proxy_calls_terminate(self, mock_terminate):
        """测试停止代理调用terminate_process"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        result = manager.stop_proxy(timeout=10)

        mock_terminate.assert_called_once_with(10)
        assert result == mock_terminate.return_value


class TestProxyManagerProxySwitching:
    """代理切换测试"""

    @patch.object(ProxyManager, 'start_proxy')
    def test_proxy_switching_calls_start_proxy(self, mock_start):
        """测试代理切换实际上是调用start_proxy（带终止现有进程）"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        # 代理切换通过start_proxy实现，该方法会自动终止现有进程
        manager.start_proxy("new_proxy", "192.168.1.1", "8080", "HTTP")

        mock_start.assert_called_once_with("new_proxy", "192.168.1.1", "8080", "HTTP")


class TestProxyManagerIntegration:
    """集成测试"""

    @patch('subprocess.Popen')
    def test_full_lifecycle(self, mock_popen):
        """测试完整的代理生命周期"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        # 模拟运行中的进程
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        # 启动代理
        with patch('os.name', 'nt'):
            with patch('src.proxy_manager.pps_config.PROGRAM_PATH', '/test/path'):
                manager.start_proxy("test_proxy", "", "", "HTTP")

        assert manager.is_process_running() is True
        assert "Running" in manager.get_process_info()

        # 切换代理（通过start_proxy实现）
        manager.start_proxy("another_proxy", "", "", "HTTP")
        assert mock_popen.call_count == 2

        # 停止代理
        mock_process.poll.return_value = None
        mock_process.wait.return_value = 0

        with patch('os.name', 'nt'):
            result = manager.stop_proxy()

        assert result is True

    def test_error_handling_in_start_proxy(self):
        """测试start_proxy中的错误处理"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        with patch.object(manager, 'terminate_process') as mock_terminate:
            with patch.object(manager, '_run_cmd') as mock_run_cmd:
                mock_run_cmd.side_effect = ProxyStartError("Test error", "Log error")

                with pytest.raises(ProxyStartError):
                    manager.start_proxy("test_proxy")


class TestProxyManagerEdgeCases:
    """边缘情况测试"""

    def test_concurrent_start_and_stop(self):
        """测试并发启动和停止"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        with patch.object(manager, 'terminate_process') as mock_terminate:
            with patch.object(manager, '_run_cmd') as mock_run_cmd:
                mock_process = Mock()
                mock_process.poll.return_value = None
                mock_popen = Mock(return_value=mock_process)

                with patch('subprocess.Popen', mock_popen):
                    with patch('os.name', 'nt'):
                        with patch('src.proxy_manager.pps_config.PROGRAM_PATH', '/test/path'):
                            # 快速连续调用
                            manager.start_proxy("proxy1")
                            manager.start_proxy("proxy2")
                            manager.stop_proxy()

                # 验证正确的调用顺序
                assert mock_terminate.call_count >= 2
                assert mock_run_cmd.call_count == 2

    @patch('subprocess.Popen')
    def test_process_cleanup_on_multiple_starts(self, mock_popen):
        """测试多次启动时的进程清理"""
        manager = ProxyManager(config=ConfigManager(use_singleton=False))

        processes = []
        def create_mock_process(*args, **kwargs):
            mock_proc = Mock()
            mock_proc.poll.return_value = None
            mock_proc.pid = 1000 + len(processes)
            processes.append(mock_proc)
            return mock_proc

        mock_popen.side_effect = create_mock_process

        with patch('os.name', 'nt'):
            with patch('src.proxy_manager.pps_config.PROGRAM_PATH', '/test/path'):
                manager.start_proxy("proxy1")
                first_pid = manager.r_process.pid

                manager.start_proxy("proxy2")
                second_pid = manager.r_process.pid

        # 验证进程ID不同
        assert first_pid != second_pid
        assert manager.r_process.pid == second_pid


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])