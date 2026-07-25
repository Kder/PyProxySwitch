# PyProxySwitch 发布与绿色版改造实施报告

日期：2026-07-25  
基线：`master` 分支提交 `8accebd`  
需求来源：

- `utils/PyProxySwitch-发布与绿色版改造.docx`
- `utils/PyProxySwitch评测.docx`

## 1. 完成结论

两份文档中对仓库提出的要求均已落实：

1. 新增 PyPI OIDC 可信发布工作流；
2. 中英文 README 补齐安装、卸载、用户数据清理和绿色版说明；
3. 实现环境变量与冻结程序标记两种便携路径；
4. 新增可真实生成 Windows 绿色版目录和 zip 的 Nuitka 构建脚本；
5. 新增便携路径与构建工具测试，并完成全量回归；
6. 将 Nuitka 构建脚本纳入 sdist；
7. 使用 Git 分阶段提交并推送到 `origin/master`。

## 2. 需求与实现对照

### 2.1 PyPI 发布

文件：`.github/workflows/publish.yml`

- `v*` 标签和手工触发均可启动构建；
- 标签发布时校验标签版本与 `pyproxyswitch/_version.py` 一致；
- 构建 sdist 和 wheel 并通过 Actions artifact 在任务间传递；
- 发布任务使用 `pypi` environment 和 OIDC `id-token: write`；
- 使用 `pypa/gh-action-pypi-publish@release/v1`，仓库无需保存 PyPI API token。

README 已记录首次发布前的外部一次性配置：

- PyPI pending publisher：owner `Kder`、repository `PyProxySwitch`、
  workflow `publish.yml`、environment `pypi`；
- GitHub 仓库创建 `pypi` environment；
- 发版标签必须与包版本一致。

本次没有创建新版本标签或上传 PyPI；该动作属于正式发版，不是仓库改造验证的一部分。

### 2.2 安装与卸载说明

文件：`README.md`、`README_EN.txt`

- 记录 `pip`、`pipx` 和 Git 仓库安装方式；
- 记录 GUI、CLI 两个命令入口；
- 明确 `pip uninstall` / `pipx uninstall` 的区别；
- 明确卸载按 Python 通行惯例保留用户数据；
- 列出 Windows、Linux、macOS 的配置与日志清理路径；
- 说明直接使用 `pip` 时依赖包不会自动卸载。

### 2.3 便携路径

文件：`pyproxyswitch/paths.py`

运行时路径优先级为：

1. `PYPROXYSWITCH_HOME`；
2. 冻结程序旁的 `portable.ini`；
3. `platformdirs` 返回的系统用户目录。

环境变量方式适用于源码、pip 和冻结程序。`portable.ini` 只对 Nuitka /
PyInstaller 等冻结程序生效。冻结检测兼容 `sys.frozen` 与 Nuitka 的
`__compiled__`。

环境变量方式将 `PPS.conf`、`proxy.txt` 放在指定目录，日志放在其
`logs/` 子目录。标记文件方式将配置放在程序旁的 `config/`，日志放在
`logs/`。

### 2.4 Nuitka 绿色版构建

文件：`tools/build_nuitka.py`

- 默认生成 standalone 单目录版；
- Nuitka 中间产物写入 `build/nuitka/`；
- 可分发目录和 zip 写入 `release/`；
- `dist/` 仅保留 Python wheel 和 sdist；
- 支持 `--onefile`、`--no-zip`、`--lto`、`--debug`、`--jobs`、
  `--output-dir`、`--release-dir`、`--clean`、`--dry-run`；
- 注入 Windows 图标、公司名、产品名、文件版本和产品版本；
- 打包默认配置、代理列表、应用翻译和 Qt 基础翻译；
- 自动植入 `portable.ini`；
- 携带中英文 README 与 LICENSE；
- 生成带版本、平台、架构信息的 portable zip；
- 检查 Nuitka 及非 Windows 平台的必要构建工具；
- `--clean` 拒绝删除仓库根目录、仓库父目录、文件系统根目录和用户主目录。

文件：`MANIFEST.in`

- `tools/build_nuitka.py` 已纳入 sdist，源码发行包可直接执行绿色版构建。

### 2.5 自动测试

文件：`tests/test_paths_portable.py`

- 环境变量高于标记文件；
- 冻结程序标记路径正确；
- 冻结程序无标记时回退用户目录；
- 普通启动默认使用用户目录；
- 默认配置初始化不覆盖用户修改。

文件：`tests/test_build_nuitka.py`

- 版本读取与 Windows 文件版本转换；
- Nuitka 命令包含 standalone、PySide6 和运行时数据；
- 默认构建和发布路径不会占用 `dist/`；
- 单目录 staging、`portable.ini`、文档和 zip 内容；
- `--dry-run` 不创建目录、不要求本机已安装 Nuitka；
- `--clean` 拒绝仓库根目录等危险目标。

## 3. Git 阶段记录

| 提交 | 内容 | 推送状态 |
|---|---|---|
| `e288c88` | 实现便携模式路径解析 | 已推送 `origin/master` |
| `30c7142` | 补充 PyPI 发布与安装卸载文档 | 已推送 `origin/master` |
| `2ff9614` | 新增 Nuitka 绿色版构建工具 | 已推送 `origin/master` |
| `8a4d9d0` | 完善发布说明与构建安全校验 | 已推送 `origin/master` |

## 4. 验证记录

所有 Python 命令均使用项目指定解释器
`D:\apps\python312\python.exe`。

### 4.1 全量自动测试

命令：

```text
D:\apps\python312\python.exe -m pytest --cov=pyproxyswitch \
  --cov-report=term-missing --cov-report=xml --cov-report=html
```

结果：

- `203 passed`；
- 总覆盖率 `74.84%`；
- `pyproxyswitch/paths.py` 语句与分支覆盖率 `100%`；
- 生成 `coverage.xml` 和 `htmlcov/`。

### 4.2 静态与生成文件检查

| 检查 | 结果 |
|---|---|
| `python -m ruff check .` | 通过 |
| 改动 Python 文件 `ruff format --check` | 通过 |
| `python -m mypy pyproxyswitch --ignore-missing-imports` | 24 个源文件通过 |
| `python tools/generate_ui.py --check` | UI 生成文件最新 |
| `python tools/generate_i18n.py --check` | TS/QM 翻译产物最新 |
| `git diff --check` | 通过 |

### 4.3 Python 发行包

命令：

```text
D:\apps\python312\python.exe -m build
```

结果：

- 成功生成 `pyproxyswitch-4.0.1.tar.gz`；
- 成功生成 `pyproxyswitch-4.0.1-py3-none-any.whl`；
- sdist 已包含 `tools/build_nuitka.py`；
- wheel 已包含 `PPS.conf`、`proxy.txt`、`en.qm`、`zh_CN.qm`。

### 4.4 Nuitka 真实构建与运行

命令：

```text
D:\apps\python312\python.exe tools\build_nuitka.py --clean
```

构建环境与结果：

- Python `3.12.10`；
- Nuitka `4.0.5`；
- MSVC `14.3`；
- 成功生成
  `build/nuitka/PyProxySwitch.dist/PyProxySwitch.exe`；
- 成功生成
  `release/PyProxySwitch-4.0.1-windows-x64-portable/`；
- 成功生成
  `release/PyProxySwitch-4.0.1-windows-x64-portable.zip`；
- zip CRC 检查通过，共 447 项，包含顶层目录、exe 和 `portable.ini`。

随后短暂启动 staging 目录中的冻结程序并等待初始化，观测到：

- `config/PPS.conf` 已创建；
- `config/proxy.txt` 已创建；
- `logs/PyProxySwitch.log` 已创建；
- 程序仍正常运行，验证进程随后由测试命令主动关闭。

这次真实运行同时证明 Nuitka 冻结环境能识别 `portable.ini`，且可变应用数据
落在程序目录。

## 5. 产物与版本控制说明

- 源码改动和本报告均由 Git 跟踪；
- `build/`、`dist/`、`release/`、覆盖率文件等构建产物按现有
  `.gitignore` 保持不入库；
- `dist/` 当前仅包含 `.whl` 和 `.tar.gz`；
- Nuitka 中间目录保留在本地 `build/nuitka/`；
- Windows 绿色版目录和 zip 保留在本地 `release/`，可用于复核；
- 正式 PyPI 上传需要仓库所有者完成一次性 Trusted Publisher /
  GitHub Environment 设置，并在准备发版时更新版本后推送匹配标签。

## 6. 后续目录规范化

根据 Python 社区对 `dist/` 的常见约定，后续调整将 Nuitka 产物从
`dist/nuitka/` 迁出：

- 编译中间目录：`build/nuitka/`；
- 最终绿色版目录和 zip：`release/`；
- Python 发行包：`dist/*.whl`、`dist/*.tar.gz`。

旧的 `dist/nuitka/` 和 `dist/PyProxySwitch.build/` 已删除；二者均为可由
构建脚本重新生成的忽略产物。迁移后重新执行真实 Nuitka 构建并启动
`release/` 中的 exe，配置、代理列表和日志仍正确创建在绿色版目录中，
zip CRC 检查通过，共 447 项。
