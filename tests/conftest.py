#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyProxySwitch pytest configuration and fixtures

提供测试所需的 fixtures 和配置。
"""

import sys
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Generator, List, Tuple
import pytest

# 添加项目根目录到 Python 路径
# utils/conftest.py ->  utils/ -> 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """创建临时目录用于测试"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_config_dir(temp_dir: Path) -> Dict[str, Path]:
    """
    创建临时配置目录结构

    Returns:
        Dict with keys: 'root', 'cfg', 'logs', 'config_file', 'proxy_file'
    """
    cfg_dir = temp_dir / "cfg"
    logs_dir = temp_dir / "logs"
    cfg_dir.mkdir()
    logs_dir.mkdir()

    config_file = cfg_dir / "PPS.conf"
    proxy_file = cfg_dir / "proxy.txt"

    # 创建示例配置
    config = {
        "CMD": "3proxy",
        "DEBUG": 0,
        "DEFAULT_ITEM": "NoProxy",
        "FIRST_RUN": 0,
        "LANG": "en",
        "LAST_ITEM": "NoProxy",
        "LOCAL_PORT": 8888,
        "SHOW_WELCOME": 0,
    }

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f)

    # 创建示例代理列表
    proxy_content = """test_proxy 192.168.1.1:8080
auth_proxy 10.0.0.1:3128 user:pass
socks_proxy 203.0.113.5:1080 SOCKS5
"""
    proxy_file.write_text(proxy_content, encoding="utf-8")

    return {
        "root": temp_dir,
        "cfg": cfg_dir,
        "logs": logs_dir,
        "config_file": config_file,
        "proxy_file": proxy_file,
    }


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """返回示例配置字典"""
    return {
        "CMD": "3proxy",
        "DEBUG": 0,
        "DEFAULT_ITEM": "NoProxy",
        "FIRST_RUN": 0,
        "LANG": "en",
        "LAST_ITEM": "NoProxy",
        "LOCAL_PORT": 8888,
        "SHOW_WELCOME": 0,
    }


@pytest.fixture
def sample_proxy_list() -> List[Tuple[str, str, str, str, str, str]]:
    """返回示例代理列表"""
    return [
        ("test_proxy", "192.168.1.1", "8080", "HTTP", "", ""),
        ("auth_proxy", "10.0.0.1", "3128", "HTTP", "user", "pass"),
        ("socks_proxy", "203.0.113.5", "1080", "SOCKS5", "", ""),
    ]


@pytest.fixture
def sample_proxy_content() -> str:
    """返回示例代理列表文件内容"""
    return """# Test proxy list
test_proxy 192.168.1.1:8080
auth_proxy 10.0.0.1:3128 user:pass
socks_proxy 203.0.113.5:1080 SOCKS5
invalid_port_proxy test.example.com:99999
"""


@pytest.fixture
def proxy_validator():
    """创建代理验证器实例"""
    from src.proxy_validation import ProxyValidator

    return ProxyValidator()


@pytest.fixture
def batch_validator():
    """创建批量导入验证器实例"""
    from src.proxy_validation import BatchImportValidator

    return BatchImportValidator()


@pytest.fixture(autouse=True)
def reset_singleton():
    """每个测试后重置 ConfigManager 单例"""
    yield
    try:
        from src.config import ConfigManager

        ConfigManager.reset_singleton()
    except ImportError:
        pass


@pytest.fixture
def config_manager_with_temp(temp_config_dir: Dict[str, Path]):
    """创建使用临时目录的 ConfigManager 实例"""
    from src.config import ConfigManager

    # 重置单例
    ConfigManager.reset_singleton()

    # 先创建一个实例（多实例模式）
    config = ConfigManager(use_singleton=False)
    # 然后设置路径
    config.config_path = temp_config_dir["config_file"]
    config.proxy_list_path = temp_config_dir["proxy_file"]
    # 重新加载
    config.load()

    yield config

    # 清理
    ConfigManager.reset_singleton()


@pytest.fixture
def config_file_with_typo(temp_dir: Path) -> Path:
    """创建带有旧版本拼写错误 (FISRT_RUN) 的配置文件"""
    cfg_dir = temp_dir / "cfg"
    cfg_dir.mkdir()

    config = {
        "CMD": "3proxy",
        "FISRT_RUN": 1,  # 旧版本拼写错误
        "LANG": "en",
        "LOCAL_PORT": 8888,
    }

    config_file = cfg_dir / "PPS.conf"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f)

    return config_file


# Qt 相关 fixtures（仅在 Qt 可用时）
@pytest.fixture
def qapp():
    """创建 QApplication 实例用于 Qt 测试"""
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QCoreApplication
    except ImportError:
        pytest.skip("PySide6 not available")

    app = QCoreApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
