#!/usr/bin/env python3
"""
PyProxySwitch 启动脚本

这是一个跨平台的代理切换器应用程序，提供系统托盘界面用于快速切换不同的代理配置。

用法:
    python PyProxySwitch.py
    python PyProxySwitch.py --debug
    python PyProxySwitch.py --config /path/to/config

版本: 3.9.0
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from src.logger_config import get_logger


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
    required_dirs = ["cfg", "bin", "logs"]
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
        # 检查是否需要重新生成配置文件
        port_changed = False
        if args.port_specified and config_port is not None and args.port != config_port:
            logger.info(f"检测到端口变更: 配置文件端口 {config_port} -> 命令行端口 {args.port}")
            port_changed = True

        # 导入并启动主应用程序
        import src.main

        # 导入必要的模块
        from src.config import ConfigManager

        # 根据--config参数计算相关路径
        config_path = Path(args.config)
        base_config_dir = config_path.parent

        # 计算相关配置文件路径
        proxy_list_path = base_config_dir / "proxy.txt"

        # 初始化配置管理器
        config_mgr = ConfigManager()
        config_mgr.set_config_path(str(config_path))
        config_mgr.set_proxy_list_path(str(proxy_list_path))
        config_mgr.set_backend_config_base(str(base_config_dir))

        # 设置pps_config使用相同的配置管理器
        import src.pps_config as pps_config
        pps_config.set_config_manager(config_mgr)
        logger.debug(f"Config file path: {config_mgr.get_config_path()}")
        logger.debug(f"Proxy list file path: {config_mgr.get_proxy_list_path()}")

        # 如果需要，重新生成配置文件
        if port_changed:
            logger.info("正在重新生成代理配置文件...")
            try:
                # 更新配置文件中的端口
                config_mgr.set('LOCAL_PORT', args.port)
                config_mgr.save()

                # 更新pps_config中的全局CONFIG
                pps_config.update_config()

                # 重新生成所有配置文件
                proxies = config_mgr.get_proxies()
                if proxies:
                    # 使用独立的函数重新生成配置文件，避免QWidget依赖
                    pps_config.regenerate_all_configs(proxies, args.port)
                    logger.info("代理配置文件重新生成完成")
                else:
                    logger.info("没有代理配置需要重新生成")

            except Exception as e:
                logger.error(f"重新生成配置文件失败: {e}")
                # 继续执行，不阻止程序启动

        # 检查是否有缺失的配置文件
        try:
            proxies = config_mgr.get_proxies()
            if proxies:
                missing_proxies = pps_config.check_missing_configs(proxies)
                if missing_proxies:
                    logger.info(f"检测到 {len(missing_proxies)} 个代理缺失配置文件，正在重新生成...")
                    pps_config.regenerate_all_configs(proxies, args.port)
                    logger.info("缺失的配置文件已重新生成")
                else:
                    logger.debug("所有代理配置文件完整")
            else:
                logger.debug("没有代理配置需要检查")
        except Exception as e:
            logger.warning(f"配置文件检查失败: {e}，跳过检查继续启动")

        # 启动应用
        src.main.main(log_level=log_level)

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
