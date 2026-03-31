#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PyProxySwitch main.py 模块的简化测试

这个测试文件专门测试 main.py 中的业务逻辑，避免复杂的 fixture 依赖。
"""

import sys
import pytest
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestMainModuleSimple:
    """简化版 main.py 测试"""

    def test_main_with_pyside6_import_error(self):
        """测试 PySide6 导入失败的情况"""
        with patch.dict('sys.modules', {'PySide6': None}):
            with patch('builtins.print') as mock_print:
                with pytest.raises(SystemExit) as exc_info:
                    import src.main
                    src.main.main()

                assert exc_info.value.code == 1
                mock_print.assert_called_once()
                print_args = mock_print.call_args[0]
                assert "PySide6 is required but not installed" in print_args[0]

    def test_main_with_low_python_version(self):
        """测试 Python 版本过低的情况"""
        with patch('sys.version_info', (3, 8)):  # 模拟 Python 3.8
            with patch('builtins.print') as mock_print:
                with pytest.raises(SystemExit) as exc_info:
                    import src.main
                    src.main.main()

                assert exc_info.value.code == 1
                mock_print.assert_called_once()
                print_args = mock_print.call_args[0]
                assert "requires Python 3.9 or higher" in print_args[0]

    def test_main_with_keyboard_interrupt(self):
        """测试键盘中断处理"""
        with patch.dict('sys.modules', {
            'PySide6': MagicMock(),
            'PySide6.QtWidgets': MagicMock(),
            'src.logger_config': MagicMock(),
        }):
            # Mock logger_config module
            mock_logger_config = MagicMock()
            mock_logger_config.setup_logger.return_value = None
            mock_logger_config.logger = MagicMock()

            with patch.dict('sys.modules', {'src.logger_config': mock_logger_config}):
                with patch('builtins.print') as mock_print:
                    # 模拟 QApplication 抛出 KeyboardInterrupt
                    import PySide6.QtWidgets
                    PySide6.QtWidgets.QApplication.side_effect = KeyboardInterrupt()

                    with pytest.raises(SystemExit) as exc_info:
                        import src.main
                        src.main.main()

                    assert exc_info.value.code == 0
                    mock_print.assert_called_once_with("\nPyProxySwitch terminated by user")

    def test_main_with_general_exception(self):
        """测试一般异常处理"""
        with patch.dict('sys.modules', {
            'PySide6': MagicMock(),
            'PySide6.QtWidgets': MagicMock(),
            'src.logger_config': MagicMock(),
        }):
            # Mock logger_config module
            mock_logger_config = MagicMock()
            mock_logger_config.setup_logger.return_value = None
            mock_logger_config.logger = MagicMock()

            with patch.dict('sys.modules', {'src.logger_config': mock_logger_config}):
                with patch('builtins.print') as mock_print:
                    # 模拟 QApplication 抛出一般异常
                    import PySide6.QtWidgets
                    PySide6.QtWidgets.QApplication.side_effect = Exception("Test error")

                    with pytest.raises(SystemExit) as exc_info:
                        import src.main
                        src.main.main()

                    assert exc_info.value.code == 1
                    mock_print.assert_called_once()
                    print_args = mock_print.call_args[0]
                    assert "Fatal error: Test error" in print_args[0]

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

    def test_main_function_signature(self):
        """测试 main 函数的签名"""
        import src.main as main_module
        import inspect

        # 检查 main 函数的参数
        sig = inspect.signature(main_module.main)
        params = list(sig.parameters.keys())

        # 应该有一个 log_level 参数
        assert 'log_level' in params

        # log_level 参数应该有默认值 None
        log_level_param = sig.parameters['log_level']
        assert log_level_param.default is None


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])