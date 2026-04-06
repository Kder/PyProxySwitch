#!/usr/bin/env python3

"""
代理管理器模块

提供ProxyManager类用于管理代理进程的启动、停止和切换，
将业务逻辑从GUI代码中分离出来，提高可测试性。
"""

import os
import re
import shlex
import signal
import subprocess
import time
from pathlib import Path

import src.pps_config as pps_config
from src.config import ConfigManager
from src.errors import ConfigError, ProxyStartError
from src.logger_config import get_logger

logger = get_logger()


class ProxyManager:
    """
    代理管理器 - 负责代理进程的生命周期管理

    此类包含所有代理管理的业务逻辑，可以在没有GUI环境的情况下独立使用。
    """

    def __init__(self, config: ConfigManager | None = None):
        """
        初始化代理管理器

        Args:
            config: 配置管理器实例，如果为None则创建新的实例
        """
        self._config = config or ConfigManager()
        self.r_process = None  # subprocess.Popen 对象

    def start_proxy(self, proxy_name: str, proxy_address: str = "",
                   proxy_port: str = "", proxy_type: str = "HTTP") -> None:
        """
        启动指定的代理

        Args:
            proxy_name: 代理名称
            proxy_address: 代理地址（ip_relay模式需要）
            proxy_port: 代理端口（ip_relay模式需要）
            proxy_type: 代理类型

        Raises:
            ProxyStartError: 启动代理失败时抛出
            ConfigError: 配置错误时抛出
        """
        # 先终止现有进程
        self.terminate_process(timeout=5)

        cmd = self._config.get('CMD')

        # 对于ip_relay，使用实际的地址和端口
        if cmd == 'ip_relay':
            item = proxy_address
            port = proxy_port
        else:
            item = proxy_name
            port = ''

        try:
            self._run_cmd(cmd, item, port)
        except (ProxyStartError, ConfigError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error starting proxy: {e}")
            raise ProxyStartError("Failed to start proxy service", str(e)) from e

    def is_process_running(self) -> bool:
        """检查代理进程是否正在运行"""
        return self.r_process is not None and self.r_process.poll() is None

    def get_process_info(self) -> str:
        """获取进程信息"""
        if self.r_process is None:
            return "No process"

        if self.r_process.poll() is None:
            return f"Running (PID: {self.r_process.pid})"
        else:
            # 进程已退出，获取退出码
            return f"Exited with code: {self.r_process.returncode}"

    def stop_proxy(self, timeout: int = 5) -> bool:
        """
        停止当前运行的代理

        Args:
            timeout: 等待超时秒数

        Returns:
            bool: 成功停止返回True，否则返回False
        """
        return self.terminate_process(timeout)

    def terminate_process(self, timeout: int = 5) -> bool:
        """
        终止代理进程

        Args:
            timeout: 等待超时秒数

        Returns:
            bool: 成功为 True，失败为 False
        """
        if self.r_process is None:
            return True

        try:
            if os.name == 'nt':
                self.r_process.terminate()
                self.r_process.wait(timeout=timeout)
            else:
                os.killpg(os.getpgid(self.r_process.pid), signal.SIGTERM)
                self.r_process.wait(timeout=timeout)
            return True
        except subprocess.TimeoutExpired:
            logger.warning("Process did not terminate gracefully, killing...")
            if os.name == 'nt':
                self.r_process.kill()
            else:
                os.killpg(os.getpgid(self.r_process.pid), signal.SIGKILL)
            self.r_process.wait()
            return False
        except Exception as e:
            logger.error(f"Process termination error: {e}")
            return False

    def _run_cmd(self, cmd: str, item: str, port: str) -> None:
        """开启代理进程（内部方法）"""
        # 验证参数
        if not isinstance(cmd, str) or not isinstance(item, str) or port is None:
            raise ConfigError("Invalid command parameters", "Invalid command parameters provided to run_cmd")

        # 验证端口
        port_int = None
        if cmd == 'ip_relay':
            try:
                port_int = int(port)
                if port_int < 1 or port_int > 65535:
                    user_msg = f"Invalid port number: {port}"
                    log_msg = f"Invalid port number: {port}. Must be between 1 and 65535"
                    raise ConfigError(user_msg, log_msg)
            except (ValueError, TypeError):
                user_msg = f"Invalid port number: {port}"
                log_msg = f"Invalid port number: {port}. Must be a valid integer"
                raise ConfigError(user_msg, log_msg) from None

        # 构建命令二进制路径
        if os.name == 'nt':
            cmd_bin = Path(pps_config.PROGRAM_PATH) / 'bin' / cmd / (cmd + '.exe')
        else:
            cmd_bin = Path(pps_config.PROGRAM_PATH) / 'bin' / cmd / cmd

        # 使用 shlex.quote 进行最安全的参数引用
        cmd_bin = shlex.quote(str(cmd_bin))

        cmd_option = '-c'

        # 构建配置文件路径
        # 验证文件名，防止路径遍历
        safe_filename = re.sub(r'[^\w\-\.]', '_', item)
        # 使用 pps_config.get_backend_config_dir 获取配置目录，并拼接安全的文件名
        conf_path = pps_config.get_backend_config_dir(cmd) / (safe_filename + '.conf')
        cmd_args = shlex.quote(str(conf_path))

        # 3proxy 和 ip_relay 的特殊处理
        if cmd == '3proxy':
            cmd_option = ''
        elif cmd == 'ip_relay':
            cmd_option = ''
            # 使用 shlex.quote 安全地拼接 ip_relay 的所有参数
            cmd_args = ' '.join([
                shlex.quote(str(self._config.get('LOCAL_PORT'))),
                shlex.quote(item),
                str(port_int)  # 端口已经是数字，且由系统执行，不需要引号
            ])

        # 最终命令拼接 - 不再需要额外的 pps_quote，因为 shlex.quote 已经处理
        cmd = f'{cmd_bin} {cmd_option} {cmd_args}'

        # 使用 subprocess.Popen 替代 QProcess
        try:
            # 将命令分割为参数列表
            cmd_parts = []

            # cmd_bin 已经被 shlex.quote 过，可以直接使用
            # 如果 cmd_bin 包含空格，需要先解析
            cmd_bin_parts = shlex.split(cmd_bin)
            cmd_parts.extend(cmd_bin_parts)

            # 添加选项和参数
            if cmd_option:
                cmd_parts.append(cmd_option)
            if cmd_args:
                # 如果 cmd_args 是带引号的字符串，需要解析
                cmd_args_parts = shlex.split(cmd_args)
                cmd_parts.extend(cmd_args_parts)

            # 如果开启了调试模式，打印命令
            logger.debug(f"Executing command: {' '.join(cmd_parts)}")

            # 在 Windows 和 Unix-like 系统上使用不同的启动方式
            if os.name == 'nt':
                # Windows 上 Popen 接受列表
                self.r_process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    # creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    shell=False
                )
            else:
                # Unix-like 系统
                self.r_process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid  # 创建新的会话组，便于终止整个进程树
                )

            # 检查进程是否成功启动
            if self.r_process.poll() is not None:
                # 如果进程已经退出，读取错误输出
                stderr_output = self.r_process.stderr.read().decode('utf-8', errors='ignore')
                user_msg = "Failed to start proxy service"
                log_msg = f"Process exited immediately. Error: {stderr_output}"
                raise ProxyStartError(user_msg, log_msg)

            # 等待进程启动
            # subprocess.Popen 立即返回，所以我们需要短暂等待
            time.sleep(0.1)

        except FileNotFoundError:
            user_msg = f"Cannot find proxy executable: {cmd}"
            log_msg = f"Cannot find proxy executable at {cmd_bin}"
            raise ProxyStartError(user_msg, log_msg) from None
        except PermissionError:
            user_msg = "Permission denied to execute proxy"
            log_msg = f"Permission denied to execute {cmd_bin}"
            raise ProxyStartError(user_msg, log_msg) from None
        except ProxyStartError:
            # Re-raise our custom exception
            raise
        except Exception as e:
            logger.error(f"Unexpected error starting proxy: {e}")
            raise ProxyStartError("Failed to start proxy service", str(e)) from e

