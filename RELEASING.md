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

1. 从 `master` 的干净工作区开始，拉取远端最新提交。
2. 确认变更记录和文档已经更新。
3. 按 `AGENTS.md` 的要求，通过 uv 定位的系统 Python 3.14 同步锁定依赖。
4. 运行完整测试、Ruff、mypy、UI 生成检查和翻译生成检查。
5. 确认准备发布的提交已经推送且 GitHub Tests 工作流通过。

## 创建版本

为已经验证的提交创建签名 annotated tag，并单独推送该标签：

```shell
git switch master
git pull --ff-only
git status --short
git tag -s vX.Y.Z -m "PyProxySwitch X.Y.Z"
git push origin vX.Y.Z
```

`.github/workflows/publish.yml` 仅由 `v[0-9]*` 标签触发。工作流获取完整 Git 历史，构建 wheel 和 sdist，并在 OIDC 上传 PyPI 前校验两个制品的版本元数据都与标签一致。

## 发布失败

不要移动、删除或复用已经推送或发布的 tag。修复问题并重新完成检查，然后使用新的补丁版本标签发布。
