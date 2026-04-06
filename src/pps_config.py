#!/usr/bin/env python

# Copyright 2009-2026 Kder
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

"""
pps_config is a configuration tool for PyProxySwitch, used to add/delete
proxies.

= Usage =:

== Add a Proxy ==:

    pps_config add proxy_name address:port username:password proxy_type

    "username" and "password" are only required when the proxy needs
    authorization.

    "proxy_type" is optional. Default value is HTTP and supported values
    are SOCKS4 and SOCKS5.

    Examples:
        pps_config add test1 test1.com:8080
        pps_config add test2 test2.com:8080 user:pass
        pps_config add socks_proxy socksproxy.com:3128 SOCKS5
        pps_config add test3 1.2.3.4:80

== Add multiple proxies ==:
    Edit the file "proxy.txt"(with UTF-8 encoding) in "cfg" folder,
    add one proxy per line with the following format:
        proxy_name address:port username:password proxy_type
    "username:password" and "proxy_type" are optional. Refer to the proxy.txt
    file in "cfg" folder or see "Add a Proxy" metioned above for details.

== Delete Proxy/Proxies ==:
    pps_config del proxy_name1 proxy_name2 proxy_name3 ...

    Examples:
        pps_config del test1
        pps_config del test1 test2 test3
"""

__author__ = "Kder"
__copyright__ = "Copyright 2009-2026 Kder"
__credits__ = ["Kder"]

__version__ = "3.9.0"
__date__ = "2026-04-01"
__maintainer__ = "Kder"
__email__ = "<kderlin (#) gmail dot com>"
__url__ = "http://www.kder.info"
__license__ = "Apache License, Version 2.0"
__status__ = "Beta"

import gettext
import json
import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from src.proxy_validation import BatchImportValidator, ProxyValidator, ValidationError

# 全局变量存储配置管理器实例
_config_mgr = None

# 延迟导入logger以避免循环依赖
def _get_logger():
    """获取已配置的logger"""
    try:
        from src.logger_config import get_logger
        return get_logger()
    except ImportError:
        return logging.getLogger(__name__)

try:
    PATH0 = str(Path(__file__).parent)
except NameError:
    PATH0 = str(Path(sys.path[0]).parent)
PROGRAM_PATH = str(Path(PATH0).parent.parent) if Path(PATH0).is_file() else str(Path(PATH0).parent)
CONF = str(Path(PROGRAM_PATH) / "cfg" / "PPS.conf")
PROXY_LIST = str(Path(PROGRAM_PATH) / "cfg" / "proxy.txt")

def setup_paths():
    """设置应用程序路径 - 为了兼容性而提供的函数"""
    # 路径已经在模块加载时设置，这里只是为了兼容性提供接口
    pass


def pps_loadcfg(config_file: str) -> dict[str, Any]:
    """加载程序配置文件"""
    try:
        with open(config_file, encoding="utf-8") as json_file:
            config = json.load(json_file)
            if "FISRT_RUN" in config and "FIRST_RUN" not in config:
                config["FIRST_RUN"] = config.pop("FISRT_RUN")
            return config
    except (OSError, ValueError, FileNotFoundError):
        # 在测试环境中，返回默认配置
        if "test" in str(config_file).lower() or "pytest" in sys.argv[0].lower():
            return {"LANG": "en", "LOCAL_PORT": 8123, "DEBUG": False, "FIRST_RUN": True}
        # 返回最小默认配置
        return {"LANG": "en", "LOCAL_PORT": 8123, "DEBUG": False, "FIRST_RUN": True}


CONFIG = pps_loadcfg(CONF)


def update_config():
    """更新全局CONFIG变量，用于在运行时重新加载配置

    注意：推荐使用 ConfigManager 单例来管理配置。
    此函数保留是为了向后兼容。
    """
    global CONFIG
    CONFIG = pps_loadcfg(CONF)
    # 同时更新翻译
    global _
    _ = gettext.translation(
        "pps_config", str(Path(PROGRAM_PATH) / "i18n"), [CONFIG["LANG"]]
    ).gettext


def get_config() -> dict[str, Any]:
    """获取当前配置（推荐使用 ConfigManager）

    Returns:
        当前配置字典
    """
    return CONFIG


def get_local_port() -> int:
    """获取本地代理端口

    优先使用 ConfigManager 单例，回退到全局 CONFIG。

    Returns:
        本地端口号
    """
    if _config_mgr:
        return _config_mgr.get('LOCAL_PORT', 8888)
    return CONFIG.get('LOCAL_PORT', 8888)


def cleanup_backend_configs():
    """清理现有的后端配置文件（独立函数，不依赖QWidget）"""
    try:
        # 清理 3proxy 配置文件
        proxy3_dir = get_backend_config_dir("3proxy")
        if proxy3_dir.exists():
            for conf_file in proxy3_dir.glob("*.conf"):
                if conf_file.name != "NoProxy.conf":  # 保留NoProxy配置
                    try:
                        conf_file.unlink()
                    except Exception as e:
                        _get_logger().warning(f"Failed to remove {conf_file}: {e}")

        # 清理 polipo 配置文件
        polipo_dir = get_backend_config_dir("polipo")
        if polipo_dir.exists():
            for conf_file in polipo_dir.glob("*.conf"):
                if conf_file.name != "NoProxy.conf":  # 保留NoProxy配置
                    try:
                        conf_file.unlink()
                    except Exception as e:
                        _get_logger().warning(f"Failed to remove {conf_file}: {e}")

    except Exception as e:
        _get_logger().warning(f"Failed to cleanup backend configs: {e}")


def generate_noproxy_configs(local_port):
    """生成NoProxy配置文件（独立函数，不依赖QWidget）"""
    try:
        import re
        from pathlib import Path

        # 生成3proxy NoProxy配置
        proxy3_dir = get_backend_config_dir("3proxy")
        proxy3_dir.mkdir(parents=True, exist_ok=True)

        # 示例配置位于程序目录下，下同
        example_3proxy = Path(PROGRAM_PATH) / "cfg" / "3proxy" / "NoProxy.conf.example"
        noproxy_3proxy = proxy3_dir / "NoProxy.conf"

        if example_3proxy.exists():
            with open(example_3proxy, encoding='utf-8') as f:
                content = f.read()

            # 替换端口配置
            content = re.sub(r'proxy -n -a -p\d+', f'proxy -n -a -p{local_port}', content)

            with open(noproxy_3proxy, 'w', encoding='utf-8') as f:
                f.write(content)

            _get_logger().info(f"Generated 3proxy NoProxy.conf with port {local_port}")

        # 生成polipo NoProxy配置
        polipo_dir = get_backend_config_dir("polipo")
        polipo_dir.mkdir(parents=True, exist_ok=True)

        example_polipo = Path(PROGRAM_PATH) / "cfg" / "polipo" / "NoProxy.conf.example"
        noproxy_polipo = polipo_dir / "NoProxy.conf"

        if example_polipo.exists():
            with open(example_polipo, encoding='utf-8') as f:
                content = f.read()

            # 替换端口配置
            content = re.sub(r'proxyPort = \d+', f'proxyPort = {local_port}', content)

            with open(noproxy_polipo, 'w', encoding='utf-8') as f:
                f.write(content)

            _get_logger().info(f"Generated polipo NoProxy.conf with port {local_port}")

    except Exception as e:
        _get_logger().error(f"Failed to generate NoProxy configurations: {e}")


def regenerate_all_configs(proxies, local_port):
    """重新生成所有配置文件（独立函数，不依赖QWidget）"""
    global logger
    try:
        # 清理现有的配置文件
        cleanup_backend_configs()

        # 生成NoProxy配置文件
        generate_noproxy_configs(local_port)

        # 为每个代理生成配置文件
        for proxy in proxies:
            _get_logger().info(f"Regenerating config for proxy: {proxy}")
            if len(proxy) >= 3:
                # 确保代理数据格式正确
                proxy_name = proxy[0]
                proxy_data = list(proxy)

                # 添加默认值以确保格式正确
                while len(proxy_data) < 6:
                    proxy_data.append("")

                # 确定代理类型
                ptype = "HTTP"  # 默认类型
                if len(proxy) >= 4 and proxy[3] in ["HTTP", "SOCKS4", "SOCKS5"]:
                    ptype = proxy[3]
                elif len(proxy) >= 6:
                    ptype = proxy[3] if proxy[3] in ["HTTP", "SOCKS4", "SOCKS5"] else "HTTP"

                # 调用 add_proxy 函数生成配置文件
                try:
                    add_proxy(proxy_data, ptype)
                except Exception:
                    _get_logger().warning(f"Failed to generate config for proxy {proxy_name}: {traceback.format_exc()}")
        _get_logger().info("All backend configuration files regenerated successfully")
    except Exception as e:
        _get_logger().error(f"Failed to regenerate backend configurations: {e}")


def check_missing_configs(proxies):
    """检查缺失的配置文件

    Args:
        proxies: 代理列表，格式为[(name, address, port, type, user, pass), ...]

    Returns:
        缺失配置文件的代理列表
    """
    missing_proxies = []

    for proxy in proxies:
        if len(proxy) >= 1:
            proxy_name = proxy[0]

            # 检查3proxy配置文件
            proxy3_path = get_backend_config_dir("3proxy") / f"{proxy_name}.conf"
            # 检查polipo配置文件
            polipo_path = get_backend_config_dir("polipo") / f"{proxy_name}.conf"

            if not proxy3_path.exists() or not polipo_path.exists():
                missing_proxies.append(proxy)
                _get_logger().debug(f"Missing config for proxy {proxy_name}: 3proxy={not proxy3_path.exists()}, polipo={not polipo_path.exists()}")

    return missing_proxies


def set_config_manager(config_mgr):
    """设置配置管理器实例用于路径解析"""
    global _config_mgr
    _config_mgr = config_mgr
    _update_paths()


def _update_paths():
    """根据config_mgr更新所有路径"""
    global CONF, PROXY_LIST

    if _config_mgr:
        CONF = str(_config_mgr.get_config_path())
        PROXY_LIST = str(_config_mgr.get_proxy_list_path())
        # 注意：不修改PROGRAM_PATH，保持静态文件(i18n, bin)路径不变


def get_backend_config_dir(backend_type: str) -> Path:
    """获取后端配置目录"""
    if _config_mgr:
        return _config_mgr.get_backend_config_dir(backend_type)
    else:
        # 向后兼容：使用原来的硬编码路径
        return Path(PROGRAM_PATH) / "cfg" / backend_type


_ = gettext.translation(
    "pps_config", str(Path(PROGRAM_PATH) / "i18n"), [CONFIG["LANG"]]
).gettext

PPS_MSG = {
    "SUCCESS_ADD": _('"%s" added.'),
    "INFO_DEL": _('Deleting "%s" ...'),
    "ERR_DEL_FILE": _(
        'Error when deleting proxy: \
Config files of "%s" does not exist or permission denied.'
    ),
    "USAGE_ADD": _("""
Usage:

Add a Proxy:

    pps_config add proxy_name address:port username:password proxy_type

    "username" and "password" are only required when the proxy needs
    authorization.
    "proxy_type" is optional. Default value is HTTP and supported values are
    SOCKS4 and SOCKS5.

    Examples:
        pps_config add test1 test1.com:8080
        pps_config add test2 test2.com:8080 user:pass
        pps_config add socks_proxy socksproxy.com:3128 SOCKS5
        pps_config add test3 1.2.3.4:80


Add multiple proxies:

    Edit the file "proxy.txt"(with UTF-8 encoding) in "cfg" folder,
    add one proxy per line with the following format:
        proxy_name address:port username:password proxy_type
    "username:password" and "proxy_type" are optional. Refer to the proxy.txt
    file in "cfg" folder
    or see "Add a Proxy" metioned above for details.
"""),
    "ERR_OPEN_CFG": _(
        "Config file reading error: Please make sure that \
cfg/PPS.conf exists and is read-writable."
    ),
    "SUCCESS_DEL": _("Deleted successfully."),
    "ERR_SPECIAL_CHAR": _("No special characters, please."),
    "USAGE_DEL": _("""
Usage:

Delete Proxy/Proxies:
    pps_config del proxy_name1 proxy_name2 proxy_name3 ...

    Examples:
        pps_config del test1
        pps_config del test1 test2 test3
"""),
    "ERR_NAME_NOT_EXIST": _('The proxy "%s" does not exist.'),
    "ERR_CMD_FORMAT": _("Invalid command format.\n"),
    "ERR_SAVE_CFG": _(
        'Config file saving error: Please make sure that each \
subdirectory of "cfg" directory exists and is read-writable.'
    ),
    "ERR_LOAD_LIST": _("Error format of the proxy list file: %s."),
}
USAGE = _("""
= Usage =:

== Add a Proxy ==:
    pps_config add proxy_name address:port username:password proxy_type

    "username" and "password" are only required when the proxy needs
    authorization.
    "proxy_type" is optional. Default value is HTTP and supported values are
    SOCKS4 and SOCKS5.

    Examples:
        pps_config add test1 test1.com:8080
        pps_config add test2 test2.com:8080 user:pass
        pps_config add socks_proxy socksproxy.com:3128 SOCKS5
        pps_config add test3 1.2.3.4:80

== Add multiple proxies ==:
    Edit the file "proxy.txt"(with UTF-8 encoding) in "cfg" folder,
    add one proxy per line with the following format:
        proxy_name address:port username:password proxy_type
    "username:password" and "proxy_type" are optional. Refer to the proxy.txt
    file in "cfg" folder
    or see "Add a Proxy" metioned above for details.

== Delete Proxy/Proxies ==:
    pps_config del proxy_name1 proxy_name2 proxy_name3 ...

    Examples:
        pps_config del test1
        pps_config del test1 test2 test3
""")


# For tests, make ACTION evaluate sys.argv at access time
def get_action_for_tests():
    try:
        # In test environments, sys.argv[0] might be pytest, so look for actual script arguments
        args = [arg for arg in sys.argv if not arg.startswith("-")]
        if len(args) > 1:
            return args[1]  # Return the first non-flag argument after script name
        return None
    except IndexError:
        return None


ACTION = get_action_for_tests()


def pps_output(msg: str, dest: str = "stdout") -> None:
    """PPS控制台字符串输出函数，支持Python 3+"""
    if not isinstance(msg, str):
        msg = str(msg)
    if dest == "stderr":
        sys.stderr.buffer.write(msg.encode("utf-8") + b"\n")
    else:
        sys.stdout.buffer.write(msg.encode("utf-8") + b"\n")


def pps_load_proxylist(list_file: str) -> list[tuple[str, str, str, str, str, str]]:
    """从文件加载代理列表，返回一个6元组(名称, 地址, 端口, 类型, 用户, 密码)
    组成的代理列表
    """
    proxy_list:list[tuple[str, str, str, str, str, str]] = []
    try:
        with open(list_file, encoding="utf-8") as l_file:
            for line in l_file.readlines():
                try:
                    proxy = BatchImportValidator.parse_proxy_line(line)
                    if proxy:
                        # _get_logger().info(f"pps config loaded proxy: {proxy}")
                        proxy_list.append(proxy)
                except ValidationError:
                    # 跳过格式错误的行
                    continue
                except IndexError as e:
                    # 只有当错误信息包含"地址格式错误，必须包含端口"时才退出
                    if "地址格式错误，必须包含端口" in str(e):
                        raise
                    else:
                        # 其他IndexError也跳过
                        continue
        return proxy_list
    except IndexError:
        pps_output(PPS_MSG["ERR_LOAD_LIST"] % PROXY_LIST, "stderr")
        sys.exit(11)


PROXIES = pps_load_proxylist(PROXY_LIST)
PROXY_NAMES = [p_item[0] for p_item in PROXIES]


def pps_save_proxylist(
    proxies: list[tuple[str, ...]] | list[str], list_file: str
) -> None:
    """保存代理列表到文件，列表可为元组的列表或字符串的列表"""
    try:
        with open(list_file, "w", encoding="utf-8") as l_file:
            lines = []
            for i in proxies:
                if isinstance(i, tuple):
                    if i[5]:  # 密码不为空
                        proxy_i = f"{i[0]} {i[1]}:{i[2]} {i[4]}:{i[5]} {i[3]}\r\n"
                    else:
                        proxy_i = f"{i[0]} {i[1]}:{i[2]} {i[3]}\r\n"
                else:
                    proxy_i = f"{i}\r\n"
                lines.append(proxy_i)
            l_file.writelines(lines)
    except OSError:
        pps_output(PPS_MSG["ERR_SAVE_CFG"], "stderr")


def pps_exc_handle() -> None:
    """PPS异常处理函数"""
    if get_config().get("DEBUG") == 1:
        traceback.print_exc()


def pps_savecfg(config_dict: dict[str, Any], config_path: str | None = None) -> None:
    """保存程序配置字典到配置文件
    Use json to dump the config dict to file

    Args:
        config_dict: 要保存的配置字典
        config_path: 配置文件路径，如果为None则使用当前配置的路径
    """
    try:
        # 优先使用传入的路径，其次使用ConfigManager的路径，最后使用全局CONF
        if config_path is not None:
            save_path = config_path
        elif _config_mgr:
            save_path = str(_config_mgr.get_config_path())
        else:
            save_path = CONF

        with open(save_path, "w", encoding="utf-8") as c_file:
            json.dump(config_dict, c_file, indent=2, sort_keys=True)
    except (OSError, TypeError):
        pps_exc_handle()
    # ~ return out_str


def _build_proxy_line_from_params(
    proxy: list[str] | tuple[str, ...], proxy_type: str = "HTTP"
) -> str:
    """
    将代理参数构建为proxy_line格式，以便复用parse_proxy_line

    Args:
        proxy: 代理参数列表/元组，格式为(name, address, port, type, user, pass)或命令行格式
        proxy_type: 代理类型

    Returns:
        str: 格式化的代理行
    """
    if len(proxy) < 2:
        raise ValidationError("代理参数至少需要名称和地址")

    # 构建基本的代理行: name address:port
    proxy_name = proxy[0]

    # 判断输入格式：如果长度>=6，则认为是(name, address, port, type, user, pass)格式
    # 否则认为是命令行格式
    if len(proxy) >= 6:
        # 标准格式: (name, address, port, type, user, pass)
        address = str(proxy[1])
        port = str(proxy[2])
        user = str(proxy[4]) if len(proxy) > 4 else ""
        password = str(proxy[5]) if len(proxy) > 5 else ""

        address_port = f"{address}:{port}"
        line_parts = [proxy_name, address_port]

        # 添加用户名密码（如果有）
        if user or password:
            line_parts.append(f"{user}:{password}")

        # 添加代理类型（如果与默认值不同）
        actual_type = str(proxy[3]) if len(proxy) > 3 else proxy_type
        if actual_type != "HTTP":
            line_parts.append(actual_type)
    else:
        # 命令行格式: name address:port [user:pass] [type]
        address_port = proxy[1]

        # 检查是否已有端口
        if ":" not in address_port and len(proxy) > 2 and ":" not in str(proxy[2]):
            # 如果地址中没有端口，且第三个参数不是user:pass格式，则使用第三个参数作为端口
            address_port = f"{address_port}:{proxy[2]}"

        line_parts = [proxy_name, address_port]

        # 添加用户名密码（如果有）
        if len(proxy) > 2:
            if ":" in str(proxy[2]):
                # 第三个参数是用户名:密码格式
                line_parts.append(str(proxy[2]))
            elif len(proxy) > 3 and ":" in str(proxy[3]):
                # 第四个参数是用户名:密码格式
                line_parts.append(str(proxy[3]))

        # 添加代理类型（如果与默认值不同或显式指定）
        if proxy_type != "HTTP" or (len(proxy) > 2 and str(proxy[-1]) in ["HTTP", "SOCKS4", "SOCKS5"]):
            line_parts.append(proxy_type)

    return " ".join(line_parts)


def add_proxy(
    proxy: list[str] | tuple[str, ...], proxy_type: str = "HTTP"
) -> tuple[str, str, str, str, str, str] | None:
    """添加代理，proxy为一包含(名称, 地址, 端口, 类型, 用户, 密码)
    的列表或元组
    """
    proxy_check = True
    proxy_name = ""
    proxy_address = ""
    proxy_port = ""
    proxy_user = ""
    proxy_pass = ""
    host_port = []
    user_pass = []

    validator = ProxyValidator()

    try:
        # 将代理参数转换为行格式，以便复用parse_proxy_line
        proxy_line = _build_proxy_line_from_params(proxy, proxy_type)

        # 使用parse_proxy_line解析代理参数
        parsed_proxy = BatchImportValidator.parse_proxy_line(proxy_line)
        if parsed_proxy is None:
            raise ValidationError("无法解析代理参数")

        # 使用验证器验证所有参数
        validated_proxy = validator.validate_full_proxy(*parsed_proxy)

        # 使用验证后的参数
        proxy_name = validated_proxy[0]
        proxy_address = validated_proxy[1]
        proxy_port = validated_proxy[2]
        proxy_type = validated_proxy[3]
        proxy_user = validated_proxy[4]
        proxy_pass = validated_proxy[5]

        host_port = [proxy_address, proxy_port]
        user_pass = [proxy_user, proxy_pass]

        host_port_str = f"{proxy_address}:{proxy_port}"

    except (ValueError, IndexError, ValidationError) as e:
        proxy_check = False
        pps_output(f"验证错误: {e}")
        pps_exc_handle()

    if proxy_check:
        # 开始添加代理项目
        proxy_tuple = (
            proxy_name,
            host_port[0],
            host_port[1],
            proxy_type,
            user_pass[0],
            user_pass[1],
        )

        # 添加对应的配置文件（无论作为主程序还是模块都应该执行）
        isauth = user_pass[0] != ""
        ishttp = proxy_type == "HTTP"
        type_map = {
            "HTTP": ["", ""],
            "SOCKS4": ["socks4a", "socks4+"],
            "SOCKS5": ["socks5", "socks5+"],
        }

        local_port = get_local_port()

        conf_file_tpl = {
            True: {
                True: [
                    (
                        f"parentProxy = {host_port_str}\r\n"
                        f"parentAuthCredentials = {user_pass[0]}:{user_pass[1]}\r\n"
                        f"proxyPort = {local_port}\r\n"
                    ),
                    (
                        f"internal 127.0.0.1\r\n"
                        f"auth iponly\r\n"
                        f"allow * 127.0.0.1\r\n"
                        f"parent 1000 http {host_port[0]} {host_port[1]} {user_pass[0]} {user_pass[1]}\r\n"
                        f"socks -n -a -p{local_port}\r\n"
                    ),
                ],
                False: [
                    f"parentProxy = {host_port_str}\r\nproxyPort = {local_port}\r\n",
                    f"internal 127.0.0.1\r\n"
                    f"auth iponly\r\n"
                    f"allow * 127.0.0.1\r\n"
                    f"parent 1000 http {host_port[0]} {host_port[1]}\r\n"
                    f"socks -n -a -p{local_port}\r\n",
                ],
            },
            False: {
                True: [
                    (
                        f"socksProxyType = {type_map[proxy_type][0]}\r\n"
                        f"parentAuthCredentials = {user_pass[0]}:{user_pass[1]}\r\n"
                        f"socksParentProxy = {host_port_str}\r\n"
                        f"proxyPort = {local_port}\r\n"
                    ),
                    (
                        f"internal 127.0.0.1\r\n"
                        f"auth iponly\r\n"
                        f"allow * 127.0.0.1\r\n"
                        f"parent 1000 {type_map[proxy_type][1]} {host_port[0]} {host_port[1]} {user_pass[0]} {user_pass[1]}\r\n"
                        f"socks -n -a -p{local_port}\r\n"
                    ),
                ],
                False: [
                    f"socksProxyType = {type_map[proxy_type][0]}\r\n"
                    f"socksParentProxy = {host_port_str}\r\n"
                    f"proxyPort = {local_port}\r\n",
                    f"internal 127.0.0.1\r\n"
                    f"auth iponly\r\n"
                    f"allow * 127.0.0.1\r\n"
                    f"parent 1000 {type_map[proxy_type][1]} {host_port[0]} {host_port[1]}\r\n"
                    f"socks -n -a -p{local_port}\r\n",
                ],
            },
        }

        conf_polipo = conf_file_tpl[ishttp][isauth][0]

        try:
            polipo_dir = get_backend_config_dir("polipo")
            polipo_dir.mkdir(parents=True, exist_ok=True)
            polipo_path = polipo_dir / (proxy_name + ".conf")
            with open(polipo_path, "w", encoding="utf-8") as cfg_file:
                cfg_file.write(conf_polipo)

            conf_3proxy = conf_file_tpl[ishttp][isauth][1]
            proxy3_dir = get_backend_config_dir("3proxy")
            proxy3_dir.mkdir(parents=True, exist_ok=True)
            proxy3_path = proxy3_dir / (proxy_name + ".conf")
            with open(proxy3_path, "w", encoding="utf-8") as cfg_file:
                cfg_file.write(conf_3proxy)

        except OSError:
            pps_output(PPS_MSG["ERR_SAVE_CFG"])
            pps_exc_handle()
            if __name__ == "__main__":
                sys.exit(2)

        # 当作为主程序运行时，修改全局PROXIES
        if __name__ == "__main__":
            for proxy_ in PROXIES:
                if proxy_[0] == proxy_name:
                    PROXIES.remove(proxy_)
            PROXIES.append(proxy_tuple)
            pps_output(PPS_MSG["SUCCESS_ADD"] % proxy_name)

        # 当作为模块导入时，返回代理元组供调用者处理
        else:
            return proxy_tuple
    elif proxy_check is False and ACTION is not None:
        pps_output(PPS_MSG["ERR_CMD_FORMAT"] + PPS_MSG["USAGE_ADD"])


def del_proxy(proxy: list[str] | tuple[str, ...] | set[str]) -> None:
    """删除代理项，proxy为一由代理名称组成的序列（元组、列表或集合）"""
    deleted = True

    for proxy_name in proxy:
        if not isinstance(proxy_name, str):
            proxy_name = str(proxy_name)

        if __name__ == "__main__":
            for i in PROXIES[:]:  # 使用副本避免迭代时修改
                if i[0] == proxy_name:
                    PROXIES.remove(i)
            pps_output(PPS_MSG["INFO_DEL"] % proxy_name)

        # 移除对应的配置文件
        try:
            polipo_path = get_backend_config_dir("polipo") / (proxy_name + ".conf")
            os.remove(polipo_path)

            proxy3_path = get_backend_config_dir("3proxy") / (proxy_name + ".conf")
            os.remove(proxy3_path)
        except OSError:
            pps_output(PPS_MSG["ERR_DEL_FILE"] % proxy_name, "stderr")
            deleted = False
            pps_exc_handle()
    if __name__ == "__main__" and deleted:
        pps_output(PPS_MSG["SUCCESS_DEL"])


if __name__ == "__main__":
    # 简单的命令行参数处理

    # 添加单个代理
    if ACTION == "add":
        if len(sys.argv) < 4:
            pps_output(PPS_MSG["ERR_CMD_FORMAT"] + PPS_MSG["USAGE_ADD"])
            sys.exit(10)
        if sys.argv[-1] in ["HTTP", "SOCKS4", "SOCKS5"]:
            add_proxy(sys.argv[2:-1], sys.argv[-1])
        else:
            add_proxy(sys.argv[2:])

    # 批量添加代理
    elif ACTION is None:
        with open(PROXY_LIST, encoding="utf-8") as file1:
            for proxy_line in file1.readlines():
                proxy_item = proxy_line.split()
                if proxy_item[-1] in ["HTTP", "SOCKS4", "SOCKS5"]:
                    add_proxy(proxy_item[0:-1], proxy_item[-1])
                else:
                    add_proxy(proxy_item)

    # 删除单个/多个代理
    elif ACTION == "del":
        if len(sys.argv) == 2:
            pps_output(PPS_MSG["ERR_CMD_FORMAT"] + PPS_MSG["USAGE_DEL"])
            sys.exit(8)
        del_proxy(sys.argv[2:])

    # 显示帮助信息
    else:
        pps_output(PPS_MSG["ERR_CMD_FORMAT"] + USAGE)
        sys.exit(6)

    pps_save_proxylist(PROXIES, PROXY_LIST)
    sys.exit(0)

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
