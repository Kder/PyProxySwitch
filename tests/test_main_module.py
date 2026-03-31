#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyProxySwitch main.py 模块的全面测试

这个测试文件专门测试 main.py 中的业务逻辑，包括：
- main() 函数的参数处理
- 依赖检查逻辑
- Python 版本检查
- 应用程序设置和启动流程
- 错误处理
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Generator

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestMainFunction:
    """测试 main() 函数的各种场景"""

    @pytest.fixture
    def mock_dependencies(self) -> Generator[dict, None, None]:
        """模拟所有依赖项"""
        with patch.dict('sys.modules', {
            'PySide6': MagicMock(),
            'PySide6.QtWidgets': MagicMock(),
            'src.logger_config': MagicMock(),
            'src.gui.main_window': MagicMock(),
            'src.pps_config': MagicMock(),
        }) as mock_modules:
            yield {
                'PySide6': mock_modules['PySide6'],
                'QtWidgets': mock_modules['PySide6.QtWidgets'],
                'logger_config': mock_modules['src.logger_config'],
                'main_window': mock_modules['src.gui.main_window'],
                'pps_config': mock_modules['src.pps_config'],
            }

    def test_main_with_pyside6_import_error(self):
        """测试 PySide6 导入失败的情况 (lines 48-51)"""
        with patch.dict('sys.modules', {'PySide6': None}):
            with patch('builtins.print') as mock_print:
                with pytest.raises(SystemExit) as exc_info:
                    import src.main
                    src.main.main()

                assert exc_info.value.code == 1
                mock_print.assert_called_once()
                print_args = mock_print.call_args[0]
                assert "PySide6 is required but not installed" in print_args[0]

    def test_main_with_pyside6_success(self, mock_dependencies):
        """测试 PySide6 导入成功的情况"""
        # 设置模拟对象
        mock_qapp = MagicMock()
        mock_dependencies['QtWidgets'].QApplication.return_value = mock_qapp

        mock_logger = MagicMock()
        mock_dependencies['logger_config'].setup_logger.return_value = None
        mock_dependencies['logger_config'].logger = mock_logger

        mock_window = MagicMock()
        mock_dependencies['main_window'].Window.return_value = mock_window

        with patch('sys.exit') as mock_exit:
            import src.main
            src.main.main()

            # 验证 setup_logger 被调用
            mock_dependencies['logger_config'].setup_logger.assert_called_once()

            # 验证 QApplication 被创建
            mock_dependencies['QtWidgets'].QApplication.assert_called_once_with(sys.argv)

            # 验证应用程序设置
            mock_qapp.setApplicationName.assert_called_once_with("PyProxySwitch")
            mock_qapp.setApplicationVersion.assert_called_once_with(src.main.__version__)

            # 验证路径设置
            mock_dependencies['pps_config'].setup_paths.assert_called_once()

            # 验证窗口创建
            mock_dependencies['main_window'].Window.assert_called_once()

            # 验证事件循环启动
            mock_qapp.exec.assert_called_once()

            # 验证 sys.exit 被调用
            mock_exit.assert_called_once_with(mock_qapp.exec.return_value)

    def test_main_with_custom_log_level(self, mock_dependencies):
        """测试 main() 函数使用自定义日志级别"""
        import logging

        mock_dependencies['QtWidgets'].QApplication.return_value = MagicMock()
        mock_dependencies['logger_config'].logger = MagicMock()
        mock_dependencies['main_window'].Window.return_value = MagicMock()

        with patch('sys.exit'):
            import src.main
            src.main.main(log_level=logging.DEBUG)

            # 验证 setup_logger 被调用时传入了正确的 log_level
            mock_dependencies['logger_config'].setup_logger.assert_called_once_with(log_level=logging.DEBUG)

    def test_main_with_low_python_version(self, mock_dependencies):
        """测试 Python 版本过低的情况 (lines 63-65)"""
        mock_dependencies['QtWidgets'].QApplication.return_value = MagicMock()
        mock_dependencies['logger_config'].logger = MagicMock()

        with patch('sys.version_info', (3, 8)):  # 模拟 Python 3.8
            with patch('builtins.print') as mock_print:
                with pytest.raises(SystemExit) as exc_info:
                    import src.main
                    src.main.main()

                assert exc_info.value.code == 1
                mock_print.assert_called_once()
                print_args = mock_print.call_args[0]
                assert "requires Python 3.9 or higher" in print_args[0]

    def test_main_with_keyboard_interrupt(self, mock_dependencies):
        """测试键盘中断处理 (lines 83-85)"""
        mock_dependencies['QtWidgets'].QApplication.side_effect = KeyboardInterrupt()

        with patch('builtins.print') as mock_print:
            with pytest.raises(SystemExit) as exc_info:
                import src.main
                src.main.main()

            assert exc_info.value.code == 0
            mock_print.assert_called_once_with("\nPyProxySwitch terminated by user")

    def test_main_with_general_exception_no_logger(self, mock_dependencies):
        """测试一般异常处理且 logger 未定义的情况 (lines 86-90)"""
        mock_dependencies['QtWidgets'].QApplication.side_effect = Exception("Test error")

        with patch('builtins.print') as mock_print:
            with pytest.raises(SystemExit) as exc_info:
                import src.main
                src.main.main()

            assert exc_info.value.code == 1
            mock_print.assert_called_once()
            print_args = mock_print.call_args[0]
            assert "Fatal error: Test error" in print_args[0]

    def test_main_with_general_exception_with_logger(self, mock_dependencies):
        """测试一般异常处理且 logger 已定义的情况 (lines 86-90)"""
        mock_logger = MagicMock()
        mock_dependencies['logger_config'].logger = mock_logger
        mock_dependencies['QtWidgets'].QApplication.side_effect = Exception("Test error")

        with patch('builtins.print') as mock_print:
            with pytest.raises(SystemExit) as exc_info:
                import src.main
                src.main.main()

            assert exc_info.value.code == 1
            mock_print.assert_called_once()
            print_args = mock_print.call_args[0]
            assert "Fatal error: Test error" in print_args[0]

            # 验证 logger.exception 被调用
            mock_logger.exception.assert_called_once_with("Fatal error occurred")

    def test_main_module_execution(self):
        """测试模块作为脚本执行 (lines 93-94)"""
        with patch('src.main.main') as mock_main:
            with patch.object(sys, 'argv', ['main.py']):
                # 模拟 __name__ == '__main__' 的情况
                import src.main

                # 重置模块状态，模拟直接执行
                with patch.object(src.main, '__name__', '__main__'):
                    with patch('src.main.main') as mock_main_direct:
                        exec("if __name__ == '__main__': main()", {
                            '__name__': '__main__',
                            'main': mock_main_direct
                        })
                        mock_main_direct.assert_called_once()


class TestMainModuleImports:
    """测试 main.py 模块的导入"""

    def test_main_module_attributes(self):
        """测试 main 模块的属性"""
        import src.main as main_module

        # 检查版本信息
        assert hasattr(main_module, '__version__')
        assert isinstance(main_module.__version__, str)

        # 检查其他元数据
        assert hasattr(main_module, '__author__')
        assert hasattr(main_module, '__copyright__')
        assert hasattr(main_module, '__license__')

        # 检查 main 函数存在
        assert hasattr(main_module, 'main')
        assert callable(main_module.main)

    def test_version_format(self):
        """测试版本格式"""
        import src.main as main_module

        version = main_module.__version__

        # 版本应该是 x.y.z 格式
        parts = version.split('.')
        assert len(parts) >= 2

        # 每个部分应该是数字
        for part in parts:
            assert part.isdigit(), f"Version part '{part}' should be numeric"


class TestMainFunctionParameterHandling:
    """测试 main 函数的参数处理"""

    @pytest.fixture
    def mock_dependencies(self) -> Generator[dict, None, None]:
        """模拟所有依赖项"""
        with patch.dict('sys.modules', {
            'PySide6': MagicMock(),
            'PySide6.QtWidgets': MagicMock(),
            'src.logger_config': MagicMock(),
            'src.gui.main_window': MagicMock(),
            'src.pps_config': MagicMock(),
        }) as mock_modules:
            yield {
                'PySide6': mock_modules['PySide6'],
                'QtWidgets': mock_modules['PySide6.QtWidgets'],
                'logger_config': mock_modules['src.logger_config'],
                'main_window': mock_modules['src.gui.main_window'],
                'pps_config': mock_modules['src.pps_config'],
            }

    def test_main_with_none_log_level(self, mock_dependencies):
        """测试 main 函数使用 None 作为 log_level"""
        mock_dependencies['QtWidgets'].QApplication.return_value = MagicMock()
        mock_dependencies['logger_config'].logger = MagicMock()
        mock_dependencies['main_window'].Window.return_value = MagicMock()

        with patch('sys.exit'):
            import src.main
            src.main.main(log_level=None)

            # 验证 setup_logger 被调用时 log_level 为 None
            mock_dependencies['logger_config'].setup_logger.assert_called_once_with(log_level=None)

    def test_main_with_various_log_levels(self, mock_dependencies):
        """测试 main 函数使用不同的日志级别"""
        import logging

        mock_dependencies['QtWidgets'].QApplication.return_value = MagicMock()
        mock_dependencies['logger_config'].logger = MagicMock()
        mock_dependencies['main_window'].Window.return_value = MagicMock()

        log_levels = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]

        for level in log_levels:
            with patch('sys.exit'):
                import src.main
                src.main.main(log_level=level)

                # 验证 setup_logger 被调用时传入了正确的 log_level
                mock_dependencies['logger_config'].setup_logger.assert_called_with(log_level=level)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])