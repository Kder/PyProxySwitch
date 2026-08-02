[![Tests](https://github.com/Kder/PyProxySwitch/actions/workflows/test.yml/badge.svg)](https://github.com/Kder/PyProxySwitch/actions/workflows/test.yml)

PyProxySwitch

作者: Kder <kderlin (#) gmail dot com>，如果有什么建议，欢迎给我发邮件  
网站: http://www.kder.info  
项目主页: http://pyproxyswitch.kder.info/  
更新记录: [CHANGELOG.md](CHANGELOG.md)
许可: Apache License, Version 2.0  

# 简介

PyProxySwitch（PPS）是一个跨平台的上游代理切换程序。4.0 起，本地代理服务器完全由 Python 标准库实现，不再启动或依赖 3proxy、polipo、IP Relay 等第三方二进制文件。

内置服务器在同一个本地端口自动识别 HTTP、SOCKS4/SOCKS4a 和 SOCKS5 客户端协议；上游支持 HTTP、SOCKS4 和 SOCKS5（含 HTTP Basic、SOCKS5 用户名/密码认证）。SOCKS4 认证字段仅表示 User ID，不支持密码。选择 `NoProxy` 时直接连接目标。

切换上游只原子替换内存中的路由快照，不重启监听套接字或事件循环。已建立连接继续使用切换前的上游，新连接立即使用新上游。

# 安装

```shell
pip install PyProxySwitch
```

推荐使用 `pipx` 在隔离环境中安装，同时让命令全局可用：

```shell
pipx install PyProxySwitch
```

也可以直接从仓库安装：

```shell
pip install git+https://github.com/Kder/PyProxySwitch.git
```

安装后运行 `pyproxyswitch` 启动图形界面。目前尚未提供无头 CLI。

# 卸载

```shell
pip uninstall PyProxySwitch
# 使用 pipx 安装时：
pipx uninstall PyProxySwitch
```

卸载只移除程序本体与命令入口。按 Python 应用的通行惯例，用户数据会被保留；如需彻底删除，请手动移除以下目录：

- Windows 配置：`%APPDATA%\Kder\PyProxySwitch`（`PPS.conf`、`proxy.txt`）
- Windows 日志：`%LOCALAPPDATA%\Kder\PyProxySwitch\Logs`（或 `PPS.conf` 中 `LOG_PATH` 指定的目录）
- Linux：`~/.config/PyProxySwitch` 与 `~/.local/state/PyProxySwitch/log`
- macOS：`~/Library/Application Support/PyProxySwitch` 与 `~/Library/Logs/PyProxySwitch`

使用 `pip`（而非 `pipx`）安装时，依赖包 PySide6、platformdirs 也会保留，不需要时请另行卸载。

# 绿色版（便携模式）

绿色版的配置与日志保存在程序自身目录，不向系统用户目录写入应用数据，“卸载”只需删除程序文件夹。

- **Windows 便携版：**从 [GitHub Releases](https://github.com/Kder/PyProxySwitch/releases) 下载 portable zip，解压后直接运行 `PyProxySwitch.exe`。包内的 `portable.ini` 标记使配置写入程序目录下的 `config/`、日志写入 `logs/`；删除该标记即恢复使用系统用户目录。
- **环境变量方式：**任意运行方式（源码、pip、exe）下，将 `PYPROXYSWITCH_HOME` 指向便携目录（例如 U 盘中的文件夹），`PPS.conf`、`proxy.txt` 与 `logs/` 均保存在该目录下。

路径优先级为：`PYPROXYSWITCH_HOME` > `portable.ini`（仅打包后的可执行文件生效）> 系统用户目录。

需要自行构建便携版的开发者请参阅 [RELEASING.md 的本地制品构建说明](RELEASING.md#单独构建本地制品)。

# 用法

- 源代码版本须先在仓库目录执行 `pip install -e .`，再运行 `pyproxyswitch`；Windows 便携版直接运行 `PyProxySwitch.exe`。然后把浏览器或其他应用的 HTTP 或 SOCKS 代理设置为 `127.0.0.1:8888`，右击系统托盘图标即可热切换上游。
- 双击系统托盘图标（或者右击系统托盘图标，点击“设置”），会弹出设置对话框，可进行添加/删除/修改代理、设置本地端口、语言等操作。
- 内置代理没有客户端认证，因此应用只允许回环监听；将 `PPS.conf` 的 `LOCAL_ADDRESS` 改为 `0.0.0.0` 或其他非回环地址会被拒绝，避免意外成为开放代理。

## 批量添加代理

可在设置界面批量编辑，也可以直接编辑 UTF-8 编码的 `proxy.txt`。无论通过源码还是 pip 运行，`PPS.conf` 和 `proxy.txt` 都位于当前用户的配置目录（Windows 为 `%APPDATA%\Kder\PyProxySwitch`），首次运行时由包内默认值创建。每行格式为“代理名称 代理地址:端口 用户名:密码 代理类型”；认证信息和类型可省略，默认类型为 HTTP。SOCKS4 的认证字段应写作 `UserID:`，冒号后的密码必须留空。例如：
```
      test1 test1.com:8080  
      test2 test2.com:8080 user:pass  
      test3 1.2.3.4:80  
      socks_proxy socksproxy.com:3128 SOCKS5  
      socks4_proxy socks4.example.com:1080 alice: SOCKS4
```

最后一行中的 `alice:` 表示 SOCKS4 User ID 为 `alice`；末尾冒号不可省略，并且冒号后不能填写密码。

代理列表在运行时直接读取，不再生成各后端的 `.conf` 文件。

# 实现与性能

代理核心使用独立后台线程中的单个 `asyncio` 事件循环，采用每方向 64 KiB 分块、传输层背压、TCP_NODELAY/KEEPALIVE 和 512 KiB 写缓冲高水位。Windows Python 3.14 为规避 Proactor 清理竞态使用 SelectorEventLoop，并把有效连接上限安全地限制为 200；其他环境仍使用默认事件循环和 512 的连接上限。转发时，程序只在客户端与上游连接之间按块传递数据，不解析、缓存或逐字节处理内容；实际吞吐主要取决于客户端、上游代理、目标服务器和网络状况。因此目前没有为转发泵引入 Cython，也避免了额外的编译链和平台相关二进制。若后续基准显示 Python 处理占用成为瓶颈，可在不改变协议层 API 的前提下替换转发泵。

普通明文 HTTP 请求为了正确处理跨主机连接复用，会显式使用 `Connection: close`；HTTPS `CONNECT` 和 SOCKS 隧道不受此限制。

当前核心面向 TCP 代理：支持 HTTP 转发/CONNECT 与 SOCKS CONNECT，不实现 SOCKS BIND、SOCKS5 UDP ASSOCIATE 或内容缓存。

# 开发

完整的环境初始化、生成文件、检查、构建和发布命令见 [RELEASING.md](RELEASING.md)。

修改 `pyproxyswitch/resources` 中的 Qt Designer `.ui` 文件后，运行 `python tools/generate_ui.py` 重新生成对应的 `*_ui.py` 文件。提交前可运行 `python tools/generate_ui.py --check` 检查生成文件是否为最新版本。

运行 `python tools/generate_i18n.py update` 从 Python 和 `.ui` 文件更新 Qt `.ts` 翻译源，完成翻译后运行 `python tools/generate_i18n.py compile` 生成应用使用的 `.qm` 文件；省略子命令会依次执行这两个阶段。提交前可运行 `python tools/generate_i18n.py --check` 检查所有翻译产物。两个生成脚本都会自动使用当前 Python 环境中的 PySide6 工具，支持 Windows、Linux 和 macOS。

# 系统要求

* 源代码版本：Python 3.11+ 和 PySide6
* 代理核心仅使用 Python 标准库
