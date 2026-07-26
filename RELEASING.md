# 开发、构建与发布流程

以下命令均在项目根目录的 PowerShell 中运行。

## 初始化

```powershell
$PYTHON = uv python find --system --no-managed-python --no-python-downloads --resolve-links 3.14
git submodule update --init --recursive
uv sync --python $PYTHON --no-managed-python --no-python-downloads --extra dev --group build
```

每次打开新终端后重新设置 `$PYTHON`。

## 修改与生成

只运行与本次修改相关的命令：

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

## 提交前检查

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

## 本地构建

```powershell
# wheel + sdist
uv build --python $PYTHON --no-managed-python --no-python-downloads --out-dir dist

# Windows portable zip
uv run --python $PYTHON --group build python tools/build_nuitka.py --clean
```

输出：

- `dist/*.whl`、`dist/*.tar.gz`
- `release/PyProxySwitch-<版本>-windows-x64-portable.zip`

## 版本模型

- Git tag 是正式版本的唯一来源。
- `setuptools-scm` 根据 tag 和 Git 历史生成 `pyproxyswitch/_version.py`。
- `_version.py` 是构建产物，不应手工修改或提交。
- 精确位于 `vX.Y.Z` 标签上的制品版本为 `X.Y.Z`；标签后的提交使用 PEP 440 开发版本。

## 一次性配置

在 PyPI Trusted Publishers 中配置：

- Owner：`Kder`
- Repository：`PyProxySwitch`
- Workflow：`publish.yml`
- Environment：`pypi`

在 GitHub 仓库 Settings → Environments 中创建 `pypi` environment。仓库不保存 PyPI API token。

```powershell
gh auth status
git config --get user.signingkey
```

SourceForge 镜像需要仓库 secret：`SOURCEFORGE_SSH_KEY`。

## 发布检查

```powershell
git switch master
git pull --ff-only
git submodule update --init --recursive
```

在 `releases.toml` 顶部添加 `X.Y.Z`、发布日期、中英文摘要和变更项，然后运行：

```powershell
uv run --python $PYTHON --extra dev python tools/release.py prepare X.Y.Z

# htdocs 有变更时先提交 submodule
git -C htdocs status --short
git -C htdocs add -A
git -C htdocs commit -m "发布 X.Y.Z"
git -C htdocs push origin master

# 再提交主仓库
git add -A
git commit -m "发布 X.Y.Z"
git push origin master

$HEAD_SHA = git rev-parse HEAD
gh run list --workflow test.yml --commit $HEAD_SHA
$RUN_ID = gh run list --workflow test.yml --commit $HEAD_SHA --limit 1 --json databaseId --jq '.[0].databaseId'
gh run watch $RUN_ID --exit-status
```

`prepare` 会同步发布文档，检查网站/UI/翻译，运行 Ruff、mypy 和完整测试，
并在 `build/release-check/` 构建、校验 wheel 与 sdist。

## 创建版本

通过发布命令复核工作区、submodule、远端 `master`、发布文档和 GitHub
Tests，然后创建并推送签名 annotated tag：

```powershell
uv run --python $PYTHON python tools/release.py publish X.Y.Z
```

本机需要已登录的 GitHub CLI（`gh auth status`）和可用的 Git 签名密钥。
`publish` 不会提交或推送分支内容；如果工作区不干净、`HEAD` 不等于
`origin/master` 或对应 Tests 未成功，它会拒绝发布。若标签推送中断，可重新执行
同一命令：脚本只会复用签名有效、指向当前 `HEAD` 且与远端一致的 annotated tag；
任何本地/远端标签冲突都会明确拒绝。

## 自动工作流

| 文件 | 触发 | 结果 |
| --- | --- | --- |
| `.github/workflows/test.yml` | push/PR → `master`、`develop` | Ruff、mypy、生成文件检查；3 个系统 × Python 3.11–3.14 测试 |
| `.github/workflows/release.yml` | `v[0-9]*` tag | Windows portable zip + Linux wheel/sdist → GitHub Release |
| `.github/workflows/publish.yml` | `v[0-9]*` tag | wheel/sdist → PyPI OIDC |
| `.github/workflows/mirror-sourceforge.yml` | push、delete、手动 | `master` → SourceForge `github-mirror`，同步全部 tag |

`release.yml` 与 `publish.yml` 独立构建和校验；前者不发布 PyPI，后者不创建
GitHub Release。两个工作流都要求 tag 版本等于 `releases.toml` 首个版本。

## 发布失败

```powershell
gh run view $RUN_ID --log-failed
gh run rerun $RUN_ID --failed
gh run watch $RUN_ID --exit-status
```

标签推送的瞬时故障可重新执行 `publish`；若远端已经收到同一标签，命令会验证后
安全结束。工作流瞬时故障可重跑；代码或制品问题必须修复后发布新的补丁版本。
不要移动、删除已经推送或发布的 tag，也不要让它指向另一提交或版本。
