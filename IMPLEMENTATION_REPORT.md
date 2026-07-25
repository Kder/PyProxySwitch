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
7. 使用 Git 分阶段提交并推送到 `origin/master`；
8. 以 Git 标签作为唯一版本源，自动生成运行时版本模块。

## 2. 需求与实现对照

### 2.1 PyPI 发布

文件：`.github/workflows/publish.yml`

- 仅推送 `v[0-9]*` 标签时启动正式发布，取消可能绕过版本语义的手工触发；
- `setuptools-scm` 从完整 Git 历史和标签推导版本，并在构建时生成
  `pyproxyswitch/_version.py`；
- 标签发布时读取 wheel 与 sdist 的包元数据，分别校验其版本与标签一致；
- 构建 sdist 和 wheel 并通过 Actions artifact 在任务间传递；
- 发布任务使用 `pypi` environment 和 OIDC `id-token: write`；
- 使用 `pypa/gh-action-pypi-publish@release/v1`，仓库无需保存 PyPI API token。

README 已记录首次发布前的外部一次性配置：

- PyPI pending publisher：owner `Kder`、repository `PyProxySwitch`、
  workflow `publish.yml`、environment `pypi`；
- GitHub 仓库创建 `pypi` environment；
- 发版标签是正式版本的唯一来源。

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

本节记录初始改造时使用 Python 3.12 完成的验证；当前项目的 Python
3.14 uv 验证见第 7 节。

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
  GitHub Environment 设置，并在准备发版时为待发布提交创建并推送签名标签。

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

## 7. uv 系统 Python 3.14 复测

项目 `.python-version` 当前固定为 `3.14`。执行：

```text
uv python find --system --no-managed-python --no-python-downloads \
  --resolve-links 3.14
```

uv `0.11.21` 定位到系统解释器：

```text
C:\Users\216\AppData\Local\Programs\Python\Python314\python.exe
```

该解释器版本为 Python `3.14.0`。使用它作为 uv 项目环境的基础解释器，
`.venv` 中的 `sys._base_executable` 已核对为上述路径。版本自动化新增
`setuptools-scm` 构建依赖后重新生成并提交 `uv.lock`，随后使用以下命令
按锁文件同步：

```text
uv sync --frozen --python <系统 Python 3.14 路径> --extra dev
```

首次 Python 3.14 全量测试发现一个 Windows Proactor 关闭竞态：
对端先关闭套接字时，CPython 3.14 的连接丢失回调可能抛出
`WinError 10022`，使 transport 未从 `asyncio.Server` 脱离，
`Server.wait_closed()` 因此无法返回。修复在所有客户端任务完成后对
server 关闭等待设置上限，并在超时时中止残留 transport，避免代理线程
停止超时。新增了永不脱离 transport 的回归测试，原失败场景另连续重复
执行 20 次，全部通过。

最终 Python 3.14 验证结果：

| 检查 | 结果 |
|---|---|
| 完整 pytest + coverage | `209 passed`，总覆盖率 `75.36%` |
| 原失败 SOCKS5 场景重复 20 次 | 全部通过 |
| `ruff check .` | 通过 |
| `mypy pyproxyswitch --ignore-missing-imports` | 24 个源文件通过 |
| UI / i18n 生成一致性 | 通过 |
| sdist / wheel 构建 | 通过，`dist/` 仍仅含 `.whl`、`.tar.gz` |
| Nuitka `--dry-run` | 通过 |

另使用 uv 的 Python 3.14 基础环境和 Nuitka `4.1.3` 完成真实 Windows
standalone 构建。Nuitka 将 Python 3.14 标记为实验性支持，但构建成功；
启动生成的绿色版后 `config/PPS.conf`、`config/proxy.txt` 和日志均正确
创建，portable zip CRC 检查通过，共 444 项。

根目录 `AGENTS.md` 已更新并纳入 Git 跟踪，后续 Python 命令要求先用 uv
定位非 uv 托管的系统 Python 3.14，再通过 `uv run --python
<resolved-path>` 执行；旧的固定 Python 3.12 路径约定已移除。

## 8. Git 标签与运行时版本自动联动

项目版本模型已迁移为 Git 标签单一事实来源：

- `pyproject.toml` 使用动态版本和 `setuptools-scm`；
- `pyproxyswitch/_version.py` 由构建后端生成，已从 Git 索引移除并加入
  `.gitignore`，不再人工修改；
- 位于精确标签的提交使用标签版本，例如 `v4.0.2` 生成 `4.0.2`；
- 普通提交自动生成 PEP 440 开发版本，包含距最近标签的提交数与提交标识；
- 应用运行时版本、wheel/sdist 元数据和 Nuitka 文件版本均消费同一生成值。

发布工作流使用 `fetch-depth: 0` 获取完整标签历史，只允许标签触发。新增
`tools/verify_release_artifacts.py`，在上传 PyPI 前直接读取 wheel 的
`METADATA` 和 sdist 的顶层 `PKG-INFO`，要求二者都与标签去除 `v` 后的
版本完全一致。对应自动化测试覆盖项目配置、工作流约束、运行时包元数据
一致性以及 wheel/sdist 校验器的成功和失败路径。

在 uv 定位的系统 Python 3.14 下，临时构建实际生成了 wheel 与 sdist；
两个制品的版本和当前 Git 派生开发版本完全一致，sdist 同时包含生成的
`_version.py` 与制品校验工具。临时制品已在验证后清理，项目 `dist/`
未写入非发行包文件。

本次只完成版本与发布自动化，没有创建或推送正式版本标签，也没有触发
PyPI 发布。正式发布应在干净、已验证的提交上创建签名且不可复用的
`vX.Y.Z` 标签，然后单独推送该标签。
