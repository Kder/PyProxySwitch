[![Tests](https://github.com/Kder/PyProxySwitch/actions/workflows/test.yml/badge.svg)](https://github.com/Kder/PyProxySwitch/actions/workflows/test.yml)

PyProxySwitch

作者: Kder <kderlin (#) gmail dot com>，如果有什么建议，欢迎给我发邮件  
网站: http://www.kder.info  
项目主页: http://pyproxyswitch.kder.info/  
最近更新: 2026-07-18
许可: Apache License, Version 2.0  

# 简介

PyProxySwitch（PPS）是一个跨平台的上游代理切换程序。4.0 起，本地代理服务器完全由 Python 标准库实现，不再启动或依赖 3proxy、polipo、IP Relay 等第三方二进制文件。

内置服务器在同一个本地端口自动识别 HTTP、SOCKS4/SOCKS4a 和 SOCKS5 客户端协议；上游支持 HTTP、SOCKS4 和 SOCKS5（含 HTTP Basic、SOCKS5 用户名/密码认证）。选择 `NoProxy` 时直接连接目标。

切换上游只原子替换内存中的路由快照，不重启监听套接字或事件循环。已建立连接继续使用切换前的上游，新连接立即使用新上游。

# 用法

- 解压后运行 `python PyProxySwitch.py`（源代码版本）或者 PyProxySwitch.exe（Windows 可执行文件版本），然后把浏览器或其他应用的 HTTP 或 SOCKS 代理设置为 `127.0.0.1:8888`。右击系统托盘图标即可热切换上游。
- 双击系统托盘图标（或者右击系统托盘图标，点击“设置”），会弹出设置对话框，可进行添加/删除/修改代理、设置本地端口、语言等操作。
- 为避免意外成为局域网公开代理，默认仅监听 `127.0.0.1`；可通过 `PPS.conf` 的 `LOCAL_ADDRESS` 显式调整。

## 批量添加代理

可在设置界面批量编辑，也可以直接编辑 UTF-8 编码的 `proxy.txt`。无论通过源码还是 pip 运行，`PPS.conf` 和 `proxy.txt` 都位于当前用户的配置目录（Windows 为 `%APPDATA%\Kder\PyProxySwitch`），首次运行时由包内默认值创建。每行格式为“代理名称 代理地址:端口 用户名:密码 代理类型”；认证信息和类型可省略，默认类型为 HTTP。例如：
```
      test1 test1.com:8080  
      test2 test2.com:8080 user:pass  
      test3 1.2.3.4:80  
      socks_proxy socksproxy.com:3128 SOCKS5  
```

代理列表在运行时直接读取，不再生成各后端的 `.conf` 文件。

# 实现与性能

代理核心使用独立后台线程中的单个 `asyncio` 事件循环，采用每方向 512 KiB 分块、传输层背压、TCP_NODELAY/KEEPALIVE 和 2 MiB 写缓冲高水位。数据转发路径是网络 I/O 受限，不做内容解析、缓存或逐字节 Python 运算，因此目前没有引入 Cython；这也避免了额外编译链和平台相关二进制。若后续基准显示 CPU 成为瓶颈，可在不改变协议层 API 的前提下替换转发泵。

普通明文 HTTP 请求为了正确处理跨主机连接复用，会显式使用 `Connection: close`；HTTPS `CONNECT` 和 SOCKS 隧道不受此限制。

当前核心面向 TCP 代理：支持 HTTP 转发/CONNECT 与 SOCKS CONNECT，不实现 SOCKS BIND、SOCKS5 UDP ASSOCIATE 或内容缓存。

# 开发

修改 `pyproxyswitch/resources` 中的 Qt Designer `.ui` 文件后，运行 `python tools/generate_ui.py` 重新生成对应的 `*_ui.py` 文件。提交前可运行 `python tools/generate_ui.py --check` 检查生成文件是否为最新版本。

运行 `python tools/generate_i18n.py update` 从 Python 和 `.ui` 文件更新 Qt `.ts` 翻译源，完成翻译后运行 `python tools/generate_i18n.py compile` 生成应用使用的 `.qm` 文件；省略子命令会依次执行这两个阶段。提交前可运行 `python tools/generate_i18n.py --check` 检查所有翻译产物。两个生成脚本都会自动使用当前 Python 环境中的 PySide6 工具，支持 Windows、Linux 和 macOS。

# 系统要求

* 源代码版本：Python 3.10+ 和 PySide6
* 代理核心仅使用 Python 标准库


# 更新历史

* 4.0.1 清理旧版二进制文件、后端配置生成器及其过时测试，统一使用用户配置目录 2026-07-18
* 4.0.0 使用 Python 原生 HTTP/SOCKS 代理核心，实现无进程重启的上游热切换，移除运行时第三方二进制依赖 2026-07-17
* 3.9.0 界面代码重构，改进配置管理和命令行参数支持
* 3.8.0 重构代码，改进进程处理、异常处理和日志功能 2026-03-17  
* 3.7   迁移至PySide6 2026-03-09  
* 3.6   新增代理验证模块，实现严格的代理参数验证机制；从PyQt4迁移至PyQt6；重构配置处理逻辑；移除过时的构建脚本 2026-03-08  
* 3.5.2   修复Windows版本启动时找不到模块的问题；修正一个Python3.2相关的input问题；修复一个路径相关的问题 2011-3-26  
* 3.5.1   Windows版本去掉3proxy支持（因3proxy被多个杀软报告为危险程序）；完善对中文路径的支持；清理目录结构，针对不同平台优化打包策略，使bin目录更加清晰；对于windows版本，为生成的exe文件添加版本信息；修复iprelay无法启动的bug  
* 3.5     增加新功能：图形界面批量添加/修改/删除代理；修改代理列表显示控件为tableView，替代treeView；重构与优化代码，改进异常处理，增加一个示例文件proxy.txt.example，更新docstring；界面微调：对话框设置为固定大小，控件间距调整 2011-03-02  
* 3.4.0   改进配置文件结构，【注意】PPS.conf与上一版本不再兼容，直接使用proxy.txt作为列表配置文件；为添加代理对话框设置输入验证；将添加/删除代理的操作设置为点击确定之后再执行；修正了一个bug:不断双击图标配置对话框会重复出现 2011-2-25  
* 3.3.2   解决系统托盘右键菜单无法消失的问题；更新README文档；从右击托盘图标就刷新菜单项目，更改为在设置界面点击确定后再刷新菜单，提高效率 2011-2-24  
* 3.3.1   更新配置文件结构；增加一个配置文件示例PPS.conf.example；完善中文支持  
* 3.3.0   重构代码，去除了大部分不必要的全局变量，使代码更加模块化 2011-2-21  
* 3.2.1   改用JSON作为配置格式；将gui_config.py合并到PyProxySwitch.pyw中；完善国际化支持,清理目录结构 2011-2-20  
* 3.1.2   增加图形界面配置工具；完善国际化支持；改进架构 2011-2-19  
* 2.1.1   改进批量添加代理的方式：现在可以直接运行pps_config.py或pps_config.exe来批量添加了，去除了已经不需要的batch_add_proxy.bat和sh两个文件；pps_config代码重构，完善了批量添加和国际化支持  
* 2.1.0   增加对Python2.7的支持，现在PPS在Python2.7+PyQt4.7或Python3.1+PyQt4.7下都可以运行了  
* 2.0     【里程碑版本】代码转移到Python3.x，同时界面库也转到了PyQt（因为wxPython暂不支持Python3）  
* 1.1.1   更改了Windows版的目录结构，将PyProxySwitch.exe和库文件移到bin目录下；修正了路径中含有中文字符时程序无法启动的bug；更改Windows版的编译方式为cx_freeze，因为测试中发现py2exe编译的exe程序图标在Vista下无法正常显示（2010-8-7）  
* 1.1.0   更新polipo为1.0.4.1版本；修复了一个程序启动时polipo未自动启动的bug （2010-8-5）  
* 1.0.9   因为部分杀软报3proxy.exe为可疑软件，将Windows版3proxy.exe移除，保留Linux版的3proxy；并将polipo设置为默认代理切换程序。2010-4-15  
* 1.0.8   将所有文件的编码改为UTF-8，增强对中文的支持  
* 1.0.7   支持添加需要认证的代理  
* 1.0.6   修正ip_relay模式下程序不能启动的问题  
* 1.0.5   修正了程序在Linux下的一些bug  
* 1.0.3   改进了程序的启动方式，不再出现命令行窗口，源代码主程序修改为PyProxySwitch.pyw，精简了部分代码　2009-10-15  
* 1.0.2   改进了Windows下隐藏Console窗口的实现方法，修正了自带的3proxy配置文件Tor.conf的一个小错误  2009-10-6  
* 1.0.1   代理名称现在支持中文了　2009-9-26  
* 1.0    【里程碑版本】实现批量添加/删除代理的功能（现支持Windows平台）2009-9-25  
* 0.9.9.9 修复了几个bug，改进了程序文件/目录的结构 16:02 2009-9-24  
* 0.9.9.8 新增代理配置程序pps_config，现在支持在命令行下添加/删除代理并定义菜单项 2009-9-23  
* 0.9.9.7 修正了Windows版读取配置文件时的一个问题　18:08 2009-9-22  
* 0.9.9.6 初步实现中文/英文界面切换 2009-9-20  
* 0.9.9.5 修正了用py2exe编译为exe文件时的bug，几处小改进 15:32 2009-9-16  
* 0.9.9.3 重构代码，polipo linux binary added 2009-09-12 10:07:52  
* 0.9.9.1 增加了对polipo的支持  
* 0.9.9 修正了一些bug，提高了在Windows & Linux上的兼容性,在Arch Linux 2009.08, Slackware 13.0, Windows Xp sp3下测试通过   
* 0.9.8 修正了在 Linux Python < 2.6下的几个bug  
* 0.9.7 使用py文件作为配置文件，可扩展性更强  
* 0.9.6 改进config文件结构，改进读写配置的相关函数  
* 0.9.5 更名为PyProxySwitch?，增强扩展性，同时支持3proxy和iprelay（sf.net）  
* 0.9.3 重构,添加平台相关代码  
* 0.9.2 增加读取配置文件的功能，支持添加代理，自动保存设置  
* 0.9.1 改进数据结构，精简优化代码  
* 0.9.0 解决CreatePopupMenu问题 2009-08-20   

