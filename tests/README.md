# PyProxySwitch 测试套件

本目录包含 PyProxySwitch 项目的单元测试和集成测试。

## 目录结构

```
tests/
├── __init__.py              # 测试包初始化
├── conftest.py              # pytest fixtures 和配置
├── fixtures/                # 测试用配置文件
│   ├── __init__.py
│   ├── sample_config.json   # 示例配置文件
│   └── sample_proxy.txt     # 示例代理列表
├── test_proxy_validation.py # 代理验证模块测试
├── test_config_manager.py   # 配置管理器测试
├── test_errors.py           # 异常类测试
└── test_logger_config.py    # 日志配置测试
```

## 安装测试依赖

```bash
# 安装所有依赖（包括开发依赖）
pip install -e ".[dev]"

# 或仅安装测试依赖
pip install pytest pytest-qt pytest-cov pytest-mock
```

## 运行测试

```bash
# 进入测试目录
cd utils

# 运行所有测试
pytest tests/

# 运行所有测试（详细输出）
pytest tests/ -v

# 运行所有测试并生成覆盖率报告
pytest tests/ --cov=src --cov-report=html

# 运行特定测试文件
pytest tests/test_proxy_validation.py

# 运行特定测试类
pytest tests/test_proxy_validation.py::TestProxyValidatorName

# 运行特定测试函数
pytest tests/test_proxy_validation.py::TestProxyValidatorName::test_valid_name_simple
```

## 测试模块说明

### test_proxy_validation.py

测试 `src/proxy_validation.py` 模块：

- `TestProxyValidatorName` - 代理名称验证
- `TestProxyValidatorAddress` - 代理地址验证
- `TestProxyValidatorPort` - 代理端口验证
- `TestProxyValidatorType` - 代理类型验证
- `TestProxyValidatorUsername` - 用户名验证
- `TestProxyValidatorPassword` - 密码验证
- `TestProxyValidatorFullProxy` - 完整代理验证
- `TestBatchImportValidator` - 批量导入验证

### test_config_manager.py

测试 `src/config.py` 模块：

- `TestConfigManagerInit` - 初始化测试
- `TestConfigManagerLoad` - 配置加载测试
- `TestConfigManagerGet` - 配置获取测试
- `TestConfigManagerSet` - 配置设置测试
- `TestConfigManagerUpdate` - 批量更新测试
- `TestConfigManagerSave` - 配置保存测试
- `TestConfigManagerReload` - 配置重载测试
- `TestConfigManagerReset` - 配置重置测试
- `TestConfigManagerProxy` - 代理列表测试

### test_errors.py

测试 `src/errors.py` 模块：

- `TestProxyError` - 基础代理异常
- `TestProxyStartError` - 代理启动错误
- `TestProxyStopError` - 代理停止错误
- `TestConfigError` - 配置错误
- `TestExceptionInheritance` - 异常继承层次

### test_logger_config.py

测试 `src/logger_config.py` 模块：

- `TestFormatter` - 日志格式化器测试
- `TestSetupLogger` - 日志设置测试
- `TestLoggerModule` - 模块级 logger 测试
- `TestLogLevels` - 日志级别测试

## CI/CD

GitHub Actions 配置位于 `.github/workflows/test.yml`。

CI 流程包括：
1. **Lint** - 代码风格检查 (flake8, pylint)
2. **Type Check** - 类型检查 (mypy)
3. **Test** - 多平台测试 (Ubuntu, Windows, macOS)
4. **Coverage** - 覆盖率报告生成

## 覆盖率

运行测试后查看覆盖率报告：

```bash
# HTML 报告
pytest tests/ --cov=src --cov-report=html
# 打开 utils/htmlcov/index.html 查看

# 终端输出
pytest tests/ --cov=src --cov-report=term-missing

# XML 报告（用于 CI）
pytest tests/ --cov=src --cov-report=xml
```

## 编写新测试

1. 在 `tests/` 目录创建 `test_*.py` 文件
2. 导入被测模块
3. 创建测试类（`Test*`）或测试函数（`test_*`）
4. 使用 `pytest.fixture` 定义测试数据

示例：

```python
import pytest
from src.proxy_validation import ProxyValidator, ValidationError

@pytest.fixture
def validator():
    return ProxyValidator()

class TestMyFeature:
    def test_something(self, validator):
        result = validator.some_method()
        assert result == expected
```
