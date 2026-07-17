#!/usr/bin/env python3
"""
PyProxySwitch 启动脚本

这是一个跨平台的代理切换器应用程序，提供系统托盘界面用于快速切换不同的代理配置。

用法:
    python PyProxySwitch.py
    python PyProxySwitch.py --debug
    python PyProxySwitch.py --config /path/to/config

版本: 4.0.0
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from pyproxyswitch.logger_config import get_logger


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="PyProxySwitch - 跨平台代理切换器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python PyProxySwitch.py              # 正常启动
  python PyProxySwitch.py --debug      # 启用调试模式
  python PyProxySwitch.py --config cfg/PPS.conf  # 指定配置文件
        """
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式，显示详细日志信息"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="cfg/PPS.conf",
        help="指定配置文件路径 (默认: cfg/PPS.conf)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,  # 使用None作为默认值，以便区分是否指定了端口
        help="本地代理端口 (默认: 从配置文件读取)"
    )

    args = parser.parse_args()

    # 标记端口是否被显式指定
    args.port_specified = args.port is not None

    return args

def check_environment():
    """检查运行环境"""
    # 检查Python版本
    if sys.version_info < (3, 10):  # noqa: UP036
        print("错误: 需要Python 3.10或更高版本")
        print(f"当前Python版本: {sys.version}")
        return False

    # 检查必要的目录结构
    required_dirs = ["cfg"]
    for dir_name in required_dirs:
        if not Path(dir_name).exists():
            print(f"警告: 缺少必要目录 {dir_name}")

    return True

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()

    # 检查环境
    if not check_environment():
        sys.exit(1)

    # 确定日志级别：命令行参数优先，其次配置文件，默认 INFO
    log_level = logging.INFO  # 默认值

    # 尝试从配置文件加载 DEBUG 和 LOCAL_PORT 设置
    config_file = Path(args.config)
    config_port = None
    if config_file.exists():
        try:
            with open(config_file, encoding='utf-8') as f:
                config_data = json.load(f)
                # 如果配置文件中 DEBUG 为 1，且未使用 --debug 参数，则使用 DEBUG 级别
                if not args.debug and config_data.get('DEBUG', 0) == 1:
                    log_level = logging.DEBUG

                # 保存配置文件中的端口值
                config_port = config_data.get('LOCAL_PORT')

                # 如果配置文件中指定了 LOCAL_PORT，且未使用 --port 参数，则使用配置文件中的端口
                if not args.port_specified and config_port:
                    args.port = config_port
                elif not args.port_specified:
                    # 如果既没有指定端口，配置文件中也没有，使用默认值8888
                    args.port = 8888
        except (OSError, json.JSONDecodeError):
            pass  # 配置文件读取失败，继续使用默认级别

    # 命令行 --debug 参数最高优先级
    if args.debug:
        log_level = logging.DEBUG

    config_path = Path(args.config)
    base_config_dir = config_path.parent
    proxy_list_path = base_config_dir / "proxy.txt"
    from pyproxyswitch.config import ConfigManager

    config_mgr = ConfigManager(
        config_path=str(config_path),
        proxy_list_path=str(proxy_list_path),
        backend_config_base=str(base_config_dir),
    )

    logger = get_logger()

    # 确保console handler的级别正确
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setLevel(log_level)

    logger.info("=" * 50)
    logger.info("PyProxySwitch 启动")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info(f"配置文件: {args.config}")
    logger.info(f"本地端口: {args.port}")
    logger.info(f"日志级别: {logger.level}")
    logger.info("=" * 50)

    try:
        logger.debug(f"Config file path: {config_mgr.get_config_path()}")
        logger.debug(f"Proxy list file path: {config_mgr.get_proxy_list_path()}")

        if args.port_specified and args.port != config_port:
            logger.info(f"使用命令行指定的本地端口: {args.port}")
            config_mgr.set('LOCAL_PORT', args.port)

        from pyproxyswitch.main import main as gui_main
        gui_main(log_level=log_level)

    except ImportError as e:
        logger.error(f"导入错误: {e}")
        logger.error("请确保所有依赖项已正确安装")
        sys.exit(1)
    except Exception as e:
        logger.error(f"启动失败: {e}")
        if args.debug:
            import traceback
            logger.debug(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
