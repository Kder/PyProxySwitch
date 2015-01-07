# -*- coding: utf-8 -*- 

PyProxySwitch  版本: 3.5.2

作者: Kder <kderlin (#) gmail dot com>，如果有什么建议，欢迎给我发邮件
网站: http://www.kder.info
项目主页: http://pyproxyswitch.kder.info/
最近更新: 2011-03-26
许可: Apache License, Version 2.0
    本程序用到了以下三个开源软件的二进制文件：
      polipo： http://www.pps.jussieu.fr/~jch/software/polipo/
      3proxy： http://www.3proxy.ru/
      iprelay：http://iprelay.sourceforge.net/
    (它们的许可请见licenses目录)

= 简介 =

    PyProxySwitch(PPS)是一个跨平台的代理切换程序，本程序的主要结构是 本地代理服务器（基于polipo/3proxy/iprelay） + 快速切换父级代理（基于Python+PyQt），实现快速切换各种应用程序（如浏览器等）的代理设置。 

= 用法 =

    解压后运行src下的PyProxySwitch.pyw（源代码版本）或者bin下的PyProxySwitch.exe（Windows可执行文件版本），然后把浏览器或其他需要设置代理的程序的代理设置为127.0.0.1:8888，右击右下角系统托盘中的图标即可快速切换代理。 
    双击系统托盘图标（或者右击系统托盘图标，点击“设置”），会弹出设置对话框，可进行添加/删除/修改代理、设置本地端口、语言等操作。

== 批量添加代理 ==

    使用src目录下的pps_config.py（Windows平台用bin目录下的pps_config.exe）
    首先将各个代理以“代理名称 代理地址:端口 用户名:密码 代理类型”的形式（代理名称可以是自定义的任何名字,[用户名:密码]仅用于需要认证的代理,一般情况下不需要,可省略。代理类型也可省略（默认是HTTP），支持的类型有SOCKS4和SOCKS5），每行一个，名称不要使用特殊字符/标点符号，最好使用字母、数字和下划线等，如：
      test1 test1.com:8080
      test2 test2.com:8080 user:pass
      test3 1.2.3.4:80
      socks_proxy socksproxy.com:3128 SOCKS5
   （可参考自带的proxy.txt的示例）
    添加到cfg目录下的proxy.txt文件中【必须是UTF-8编码】，双击pps_config.py或pps_config.exe即可批量导入代理。 

== 批量删除代理 ==

    使用bin下的pps_config，用法：pps_config del 代理名称1 代理名称2 代理名称3 …… 

    例如 pps_config del test1 test2 

= 自定义代理及菜单项 =

    使用pps_config(py源代码或者exe可执行文件)【推荐】

    pps_config 是PyProxySwitch(PPS)的配置程序，可以为PPS添加或者删除代理 

== pps_config用法： ==

  添加代理(仅支持添加单个代理，批量添加请使用pps_config配合proxy.txt，见上面的说明)：

    pps_config add 代理名称 代理地址:端口 用户名:密码 代理类型
         代理名称可以是自定义的任何名字，[用户名:密码]仅用于需要认证的代理，一般情况下不需要，可省略
         代理类型也可省略（默认是HTTP），支持的类型有SOCKS4和SOCKS5
    例如：pps_config add test1 test1.com:8080 
          pps_config add test2 test2.com:8080 user:pass
          pps_config add socks_proxy socksproxy.com:3128 SOCKS5
    或者：pps_config add test3 1.2.3.4:80


  删除代理(支持批量删除)：

    pps_config del 代理名称1 代理名称2 ...
    例如：pps_config del test1
          pps_config del test1 test2 test3


==【不推荐】手动设置代理及菜单项==
    cfg目录下的配置文件PPS.conf中可以定义菜单项，3proxy/polipo目录下是各个菜单项对应的配置文件，用户可根据需要进行自定义，其中最主要的是父级代理parentProxy的设置，其他更高级的用法可参见3proxy/polipo/iprelay各自的文档。 
    
    以polipo为例，比如你的代理地址是1.2.3.4:80 ，类型为HTTP：

   1. 打开cfg/polipo目录下一个配置文件，例如Tor.conf，找到类似这一行 parentProxy = "127.0.0.1:9050"，将其改为你的代理地址：parentProxy = "1.2.3.4:80"，保存。
   2. 然后把Tor.conf改为你想要的名称，例如proxy1.conf 。
   3. 修改proxy.txt，添加一行： proxy1 1.2.3.4:80 HTTP ，保存。
   4. 退出，重新启动PyProxySwitch，右键，就可以切换到你新添加的代理了。 

    若用的是3proxy，则要修改cfg/3proxy目录下的对应文件中的parent 1000 http 1.2.3.4 80为 parent 1000 http 地址 端口　的形式 

    默认的本地代理程序是 polipo（支持内容缓存，功能强大），另外还有3proxy（支持DNS缓存，不支持内容缓存，功能强大）和ip_relay（仅是端口转发，本身无代理功能） 

= 系统要求 =

    * 源代码版本:Python2.6+和PyQt4.7+
        (在以下环境中测试通过
        32位:
         Windows Vista + Python3.1 + PyQt4.7.4
         Windows Xp + Python2.7 + PyQt4.8.2
         Windows Xp + Python3.2 + PyQt4.8.3
         Slackware/Zenwalk Linux + Python2.6 + PyQt4.7.4
         Slackware/Zenwalk Linux + Python3.1 + PyQt4.7.4
        )
  * Windows可执行文件版本：32位 Windows XP/Vista （64位及其他操作系统未做测试） 

= 更新历史 =
    * 3.5.2   修复Windows版本启动时找不到模块的问题；修正一个Python3.2相关的input问题；修复一个路径相关的问题 2011-3-26
    * 3.5.1   Windows版本去掉3proxy支持（因3proxy被多个杀软报告为危险程序）；完善对中文路径的支持；清理目录结构，针对不同平台优化打包策略，使bin目录更加清晰；对于windows版本，为生成的exe文件添加版本信息；修复iprelay无法启动的bug
    * 3.5     增加新功能：图形界面批量添加/修改/删除代理；修改代理列表显示控件为tableView，替代treeView；重构与优化代码，改进异常处理，增加一个示例文件proxy.txt.example，更新docstring；界面微调：对话框设置为固定大小，控件间距调整 2011-03-02
    * 3.4.0   改进配置文件结构，【注意】PPS.conf与上一版本不再兼容，直接使用proxy.txt作为列表配置文件；为添加代理对话框设置输入验证；将添加/删除代理的操作设置为点击确定之后再执行；修正了一个bug:不断双击图标配置对话框会重复出现 2011-2-25
    * 3.3.2   解决系统托盘右键菜单无法消失的问题；更新README文档；从右击托盘图标就刷新菜单项目，更改为在设置界面点击确定后再刷新菜单，提高效率 2011-2-24
    * 3.3.1   更新配置文件结构；增加一个配置文件示例PPS.conf.example；完善中文支持
    * 3.3.0   重构代码，去除了大部分不必要的全局变量，使代码更加模块化 2011-2-21
    * 3.2.1   改用JSON作为配置格式；将gui_config.py合并到PyProxySwtich.pyw中；完善国际化支持,清理目录结构 2011-2-20
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
    * 0.9.9 修正了一些bug，提高了在Windows & Linux上的兼容性,在Arch Linux 2009.08, Slackware 13.0
          和Windows Xp sp3下测试通过 
    * 0.9.8 修正了在 Linux Python < 2.6下的几个bug
    * 0.9.7 使用py文件作为配置文件，可扩展性更强
    * 0.9.6 改进config文件结构，改进读写配置的相关函数
    * 0.9.5 更名为PyProxySwitch?，增强扩展性，同时支持3proxy和iprelay（sf.net）
    * 0.9.3 重构,添加平台相关代码
    * 0.9.2 增加读取配置文件的功能，支持添加代理，自动保存设置
    * 0.9.1 改进数据结构，精简优化代码
    * 0.9.0 解决CreatePopupMenu问题 2009-08-20 

