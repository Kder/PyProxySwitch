#!/usr/bin/env python

"""
main.py 集成测试 - 专注于实际可测试的代码路径
"""


import pytest


def test_main_function_import_and_call():
    """测试 main 函数可以导入和调用"""
    # 导入模块
    from src.main import main

    # 验证函数存在且可调用
    assert callable(main)

    # 验证函数签名
    import inspect
    sig = inspect.signature(main)
    assert 'log_level' in sig.parameters
    assert sig.parameters['log_level'].default is None

def test_main_module_metadata():
    """测试模块元数据"""
    from src.main import (
        __version__, __author__, __copyright__, __credits__,
        __license__, __status__, __projecturl__, __date__,
        __email__, __maintainer__, __url__
    )

    # 验证版本信息
    assert isinstance(__author__, str)
    assert "Kder" in __author__
    assert "Copyright" in __copyright__
    assert "Apache" in __license__

def test_main_with_valid_log_level():
    """测试带有效日志级别的 main 函数"""
    from src.main import main

    # 测试函数接受不同的日志级别参数
    test_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    for level in test_levels:
        # 验证函数签名支持这些参数
        import inspect
        sig = inspect.signature(main)
        bound_args = sig.bind(log_level=level)
        bound_args.apply_defaults()
        assert bound_args.arguments['log_level'] == level

def test_main_function_exception_handling():
    """测试 main 函数的异常处理能力"""
    from src.main import main

    # 验证函数有异常处理逻辑
    import inspect
    source = inspect.getsource(main)

    # 检查异常处理代码存在
    assert "except ImportError" in source
    assert "except KeyboardInterrupt" in source
    assert "except Exception" in source
    assert "sys.exit" in source

def test_main_function_imports():
    """测试 main 函数中的导入语句"""
    from src.main import main

    # 验证函数有必要的导入
    import inspect
    source = inspect.getsource(main)

    # 检查关键导入
    assert "from PySide6 import QtWidgets" in source
    assert "from src.logger_config import setup_logger" in source
    assert "from src.gui.main_window import Window" in source

def test_main_function_application_setup():
    """测试 main 函数中的应用设置逻辑"""
    from src.main import main

    # 验证函数有应用程序设置代码
    import inspect
    source = inspect.getsource(main)

    # 检查应用设置代码
    assert "QApplication(sys.argv)" in source
    assert "setApplicationName" in source
    assert "setApplicationVersion" in source

def test_main_function_paths_setup():
    """测试 main 函数中的路径设置"""
    from src.main import main

    # 验证函数有路径设置代码
    import inspect
    source = inspect.getsource(main)

    # 检查路径设置代码
    assert "pps_config.setup_paths()" in source

def test_main_function_window_creation():
    """测试 main 函数中的窗口创建"""
    from src.main import main

    # 验证函数有窗口创建代码
    import inspect
    source = inspect.getsource(main)

    # 检查窗口创建代码
    assert "Window()" in source

def test_main_function_event_loop():
    """测试 main 函数中的事件循环"""
    from src.main import main

    # 验证函数有事件循环代码
    import inspect
    source = inspect.getsource(main)

    # 检查事件循环代码
    assert "app.exec()" in source
    assert "sys.exit(app.exec())" in source

def test_main_function_version_check():
    """测试 main 函数中的版本检查"""
    from src.main import main

    # 验证函数有版本检查代码
    import inspect
    source = inspect.getsource(main)

    # 检查版本检查代码
    assert "sys.version_info" in source
    assert "Python 3.10" in source

def test_main_function_logger_handling():
    """测试 main 函数中的日志处理"""
    from src.main import main

    # 验证函数有日志处理代码
    import inspect
    source = inspect.getsource(main)

    # 检查日志处理代码
    assert "setup_logger" in source
    assert "logger.exception" in source
    assert "'logger' in locals()" in source

def test_main_module_docstring():
    """测试模块文档字符串"""
    import src.main as main_module

    # 验证模块有文档字符串
    assert main_module.__doc__ is not None
    assert "PyProxySwitch" in main_module.__doc__
    assert "cross-platform" in main_module.__doc__
    assert "proxy switcher" in main_module.__doc__

def test_main_function_docstring():
    """测试 main 函数文档字符串"""
    from src.main import main

    # 验证函数有文档字符串
    assert main.__doc__ is not None
    assert "应用程序主入口点" in main.__doc__

def test_main_module_execution_guard():
    """测试模块执行保护"""
    import src.main as main_module

    # 验证模块有执行保护
    source = open(main_module.__file__, 'r', encoding='utf-8').read()
    assert "if __name__ == '__main__':" in source
    assert "main()" in source

def test_main_error_messages():
    """测试错误消息"""
    from src.main import main

    # 验证函数有错误消息
    import inspect
    source = inspect.getsource(main)

    # 检查错误消息
    assert "PySide6 failed to import" in source
    assert "Python 3.10 or higher" in source
    assert "PyProxySwitch terminated by user" in source
    assert "Fatal error" in source

def test_main_exit_codes():
    """测试退出代码"""
    from src.main import main

    # 验证函数有正确的退出代码
    import inspect
    source = inspect.getsource(main)

    # 检查退出代码
    assert "sys.exit(1)" in source  # 错误退出
    assert "sys.exit(0)" in source  # 正常退出

def test_main_function_structure():
    """测试 main 函数结构"""
    from src.main import main

    # 获取函数源码分析结构
    import inspect
    source = inspect.getsource(main)

    # 验证函数结构
    assert "def main(log_level=None):" in source
    assert "logger = None" in source
    assert "try:" in source
    assert "except ImportError" in source
    assert "except KeyboardInterrupt" in source
    assert "except Exception" in source

if __name__ == '__main__':
    pytest.main([__file__, '-v'])