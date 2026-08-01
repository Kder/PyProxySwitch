# 开发、构建与发布流程

以下命令均在项目根目录的 PowerShell 中运行。正式发布统一通过
`tools/release.py` 编排；“按需高级操作参考”中的单项命令用于日常开发或故障排查，
不是每次发布前都要重复执行的清单。

## 环境初始化

```powershell
$PYTHON = uv python find --system --no-managed-python --no-python-downloads --resolve-links 3.14
git submodule update --init --recursive
uv sync --python $PYTHON --no-managed-python --no-python-downloads --extra dev --group build --reinstall-package PyProxySwitch
```

每次打开新终端后重新设置 `$PYTHON`。

## 常规发布

### 1. 更新发布信息

从最新的 `master` 开始：

```powershell
git switch master
git pull --ff-only
git submodule update --init --recursive
```

在 `releases.toml` 顶部添加 `X.Y.Z`、发布日期、中英文摘要和变更项。

### 2. 自动准备并检查

```powershell
uv run --python $PYTHON --extra dev python tools/release.py prepare X.Y.Z
```

`prepare` 会一次性完成以下工作：

- 校验分支、版本信息以及已有的本地和远端版本标签；
- 同步并复查 `CHANGELOG.md` 和网站发布内容；
- 检查网站、UI 生成文件和翻译文件；
- 运行 Ruff、mypy 和完整测试；
- 在 `build/release-check/` 构建并校验 wheel 与 sdist；
- 显示主仓库和 `htdocs` submodule 的待提交改动。

常规发布不需要再逐项手动执行上述命令。

### 3. 复核、提交并推送

`prepare` 不会替维护者提交或推送分支内容。复核其输出和实际差异；如果 `htdocs`
有改动，先提交并推送 submodule：

```powershell
git -C htdocs status --short
git -C htdocs add -A
git -C htdocs commit -m "发布 X.Y.Z"
git -C htdocs push origin master
```

然后提交并推送主仓库：

```powershell
git add -A
git commit -m "发布 X.Y.Z"
git push origin master
```

### 4. 创建版本

待该提交的 GitHub Tests 工作流成功后运行：

```powershell
uv run --python $PYTHON python tools/release.py publish X.Y.Z
```

`publish` 会自动复核工作区和 submodule、远端 `master`、发布文档以及 GitHub
Tests，然后创建并推送签名 annotated tag。它不会提交或推送分支内容。

若标签推送中断，可重新执行同一命令。脚本只会复用签名有效、指向当前 `HEAD`
且与远端一致的标签；任何本地或远端标签冲突都会明确拒绝。

标签推送后，GitHub Actions 会构建正式制品、创建 GitHub Release 并发布到
PyPI，无需维护者再次手工构建或上传。

## 一次性配置

本机需要已登录的 GitHub CLI 和可用的 Git 签名密钥：

```powershell
gh auth status
git config --get user.signingkey
```

在 PyPI Trusted Publishers 中配置：

- Owner：`Kder`
- Repository：`PyProxySwitch`
- Workflow：`release.yml`
- Environment：`pypi`

在 GitHub 仓库 Settings → Environments 中创建 `pypi` environment。仓库不保存
PyPI API token。

SourceForge 镜像需要仓库 secret：`SOURCEFORGE_SSH_KEY`。

## 版本模型

- Git tag 是正式版本的唯一来源。
- `setuptools-scm` 根据 tag 和 Git 历史生成 `pyproxyswitch/_version.py`。
- `_version.py` 是构建产物，不应手工修改或提交。
- 精确位于 `vX.Y.Z` 标签上的制品版本为 `X.Y.Z`；标签后的提交使用 PEP 440
  开发版本。

## 按需高级操作参考

以下命令用于单独生成文件、定位失败或验证局部改动。`prepare` 已包含发布所需的
生成内容同步、检查、测试和 Python 制品构建，常规发布时无需重复运行本节。

### 单独更新生成文件

```powershell
# 修改 pyproxyswitch/resources/*.ui 后
uv run --python $PYTHON python tools/generate_ui.py

# 修改界面文案后：更新 TS，翻译 i18n/*.ts，再编译 QM
uv run --python $PYTHON python tools/generate_i18n.py update
uv run --python $PYTHON python tools/generate_i18n.py compile

# 修改 releases.toml 后
uv run --python $PYTHON python tools/sync_release_docs.py --write
```

`sync_release_docs.py --write` 可能同时修改主仓库和 `htdocs` submodule。

### 单独运行检查

```powershell
uv run --python $PYTHON python tools/sync_release_docs.py --check
uv run --python $PYTHON python htdocs/tools/validate_site.py
uv run --python $PYTHON --extra dev python -m ruff check .
uv run --python $PYTHON python tools/generate_ui.py --check
uv run --python $PYTHON python tools/generate_i18n.py --check
uv run --python $PYTHON --extra dev python -m mypy pyproxyswitch --ignore-missing-imports
uv run --python $PYTHON --extra dev python -m pytest
git diff --check
git status --short
git submodule status --recursive
```

### 单独构建本地制品

```powershell
# wheel + sdist
uv build --python $PYTHON --no-managed-python --no-python-downloads --out-dir dist

# Windows portable zip
uv run --python $PYTHON --group build python tools/build_nuitka.py --clean
```

输出：

- `dist/*.whl`、`dist/*.tar.gz`
- `release/PyProxySwitch-<版本>-windows-x64-portable.zip`

这些本地制品用于开发验证；正式发布工作流会独立重新构建和校验。

### 排查 GitHub Actions

```powershell
$HEAD_SHA = git rev-parse HEAD
$RUN_ID = gh run list --workflow test.yml --commit $HEAD_SHA --limit 1 --json databaseId --jq '.[0].databaseId'
gh run view $RUN_ID --log-failed
gh run rerun $RUN_ID --failed
gh run watch $RUN_ID --exit-status
```

工作流瞬时故障可重跑；代码或制品问题必须修复后发布新的补丁版本。不要移动、删除
已经推送或发布的 tag，也不要让它指向另一提交或版本。

## 自动工作流

| 文件 | 触发 | 结果 |
| --- | --- | --- |
| `.github/workflows/test.yml` | push/PR → `master`、`develop` | Ruff、mypy、生成文件检查；3 个系统 × Python 3.11–3.14 测试 |
| `.github/workflows/release.yml` | `v[0-9]*` tag | Windows portable zip + 一次构建的 Linux wheel/sdist → GitHub Release 与 PyPI OIDC |
| `.github/workflows/mirror-sourceforge.yml` | push、delete、手动 | `master` → SourceForge `github-mirror`，同步全部 tag |

`release.yml` 只构建一次 wheel/sdist，GitHub Release 和 PyPI 发布任务下载并消费
同一份 `python-distributions` artifact。工作流要求 tag 版本等于
`releases.toml` 首个版本。
