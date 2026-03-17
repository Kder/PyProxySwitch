#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyProxySwitch 启动脚本

这是一个跨平台的代理切换器应用程序，提供系统托盘界面用于快速切换不同的代理配置。

用法:
    python PyProxySwitch.py
    python PyProxySwitch.py --debug
    python PyProxySwitch.py --config /path/to/config

版本: 3.8.0
"""

import sys
import os
import argparse
from pathlib import Path

# 添加src目录到Python路径
#src_path = Path(__file__).parent / "src"
#sys.path.insert(0, str(src_path))

# 日志配置已移至 src/logger_config.py

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
        default=8888,
        help="本地代理端口 (默认: 8888)"
    )

    return parser.parse_args()

def check_environment():
    """检查运行环境"""
    # 检查Python版本
    if sys.version_info < (3, 10):
        print("错误: 需要Python 3.10或更高版本")
        print(f"当前Python版本: {sys.version}")
        return False

    # 检查必要的目录结构
    required_dirs = ["cfg", "bin", "logs"]
    for dir_name in required_dirs:
        if not Path(dir_name).exists():
            print(f"警告: 缺少必要目录 {dir_name}")

    # 检查必要的文件
    #required_files = ["src/main.py"]
    #for file_name in required_files:
    #    if not Path(file_name).exists():
    #        print(f"错误: 缺少必要文件 {file_name}")
    #        return False

    return True

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()

    # 检查环境
    if not check_environment():
        sys.exit(1)

    # 设置日志
    import logging
    import json
    from src.logger_config import setup_logger
    
    # 确定日志级别：命令行参数优先，其次配置文件，默认 INFO
    log_level = logging.INFO  # 默认值
    
    # 尝试从配置文件加载 DEBUG 设置
    config_file = Path(args.config)
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                # 如果配置文件中 DEBUG 为 1，且未使用 --debug 参数，则使用 DEBUG 级别
                if not args.debug and config_data.get('DEBUG', 0) == 1:
                    log_level = logging.DEBUG
        except (json.JSONDecodeError, IOError):
            pass  # 配置文件读取失败，继续使用默认级别
    
    # 命令行 --debug 参数最高优先级
    if args.debug:
        log_level = logging.DEBUG
    
    logger = setup_logger(log_level=log_level)

    logger.info("=" * 50)
    logger.info("PyProxySwitch 启动")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info(f"配置文件: {args.config}")
    logger.info(f"本地端口: {args.port}")
    logger.info("=" * 50)

    try:
        # 导入并启动主应用程序
        import src.main

        # 启动应用
        logger.info("正在启动PyProxySwitch应用程序...")
        src.main.main()

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