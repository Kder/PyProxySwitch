# 发布流程

本文档面向项目维护者。用户安装与使用说明保留在 README，PyPI 发布细节集中维护在此处。

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

## 发布检查

1. 从 `master` 的干净工作区开始，拉取远端和 `htdocs` submodule 的最新提交。
2. 在 `releases.toml` 顶部添加新版本、明确的发布日期、中英文摘要和变更项。
3. 按 `AGENTS.md` 的要求，通过 uv 定位的系统 Python 3.14 运行发布准备：

   ```powershell
   uv run --python <系统 Python 3.14 路径> --extra dev python tools/release.py prepare X.Y.Z
   ```

   `prepare` 会生成并检查发布文档，验证网站、UI 和翻译生成结果，运行
   Ruff、mypy 和完整测试，并在 `build/release-check/` 构建和验证 wheel
   与 sdist。发布日期只读取 `releases.toml`。

4. 查看命令输出的主仓库和 `htdocs` 差异。
5. 先提交并推送 `htdocs`，再在主仓库提交更新后的 submodule 指针和其他改动。
6. 确认准备发布的提交已经推送且 GitHub Tests 工作流通过。

## 创建版本

通过发布命令复核工作区、submodule、远端 `master`、发布文档和 GitHub
Tests，然后创建并推送签名 annotated tag：

```powershell
uv run --python <系统 Python 3.14 路径> python tools/release.py publish X.Y.Z
```

本机需要已登录的 GitHub CLI（`gh auth status`）和可用的 Git 签名密钥。
`publish` 不会提交或推送分支内容；如果工作区不干净、`HEAD` 不等于
`origin/master`、对应 Tests 未成功或标签已存在，它会拒绝发布。

`.github/workflows/publish.yml` 仅由 `v[0-9]*` 标签触发。工作流获取完整 Git 历史，构建 wheel 和 sdist，并在 OIDC 上传 PyPI 前校验两个制品的版本元数据都与标签一致。

发布工作流还会要求标签版本等于 `releases.toml` 的首个版本，并检查
`CHANGELOG.md` 和网站生成文件没有过期。发布日期只读取
`releases.toml`，不会使用工作流运行当天。

## 发布失败

不要移动、删除或复用已经推送或发布的 tag。修复问题并重新完成检查，然后使用新的补丁版本标签发布。
