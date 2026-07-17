<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="zh_CN">
<context>
    <name>AddProxy_Dialog</name>
    <message>
        <location filename="../pyproxyswitch/gui/add_proxy_dialog.py" line="56"/>
        <location filename="../pyproxyswitch/gui/add_proxy_dialog.py" line="67"/>
        <source>Validation Error</source>
        <translation>验证错误</translation>
    </message>
</context>
<context>
    <name>BatchImportDialog</name>
    <message>
        <location filename="../pyproxyswitch/gui/batch_import_dialog.py" line="40"/>
        <source>Batch Add/Modify/Delete Proxy</source>
        <translation>批量添加/修改/删除代理</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/batch_import_dialog.py" line="44"/>
        <source>Please use the following syntax for one proxy per line:

proxy_name address:port username:password proxy_type

&quot;username&quot; and &quot;password&quot; are only required when the proxy needs authorization.
&quot;proxy_type&quot; can be HTTP, SOCKS4 or SOCKS5.

Example:
my_proxy 192.168.1.100:8080
auth_proxy 10.0.0.1:3120 user:pass HTTP
socks_proxy 203.0.113.5:1080 SOCKS5

</source>
        <translation>请按照下列格式添加/修改代理（冒号必须是英文半角的）：

  代理名称 地址:端口 用户名:密码 代理类型

用户名和密码仅当代理须验证时才需要；
代理类型可以是HTTP、SOCKS4或SOCKS5。

示例：
my_proxy 192.168.1.100:8080
auth_proxy 10.0.0.1:3120 user:pass HTTP
socks_proxy 203.0.113.5:1080 SOCKS5

</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/batch_import_dialog.py" line="69"/>
        <source>Preview</source>
        <translation>预览</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/batch_import_dialog.py" line="100"/>
        <source>Valid proxies found:</source>
        <translation>找到有效代理：</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/batch_import_dialog.py" line="106"/>
        <source>more</source>
        <translation>更多</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/batch_import_dialog.py" line="110"/>
        <source>Import Preview</source>
        <translation>导入预览</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/batch_import_dialog.py" line="132"/>
        <location filename="../pyproxyswitch/gui/batch_import_dialog.py" line="145"/>
        <location filename="../pyproxyswitch/gui/batch_import_dialog.py" line="152"/>
        <source>Import Failed</source>
        <translation>导入失败</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/batch_import_dialog.py" line="133"/>
        <source>No valid proxies found.</source>
        <translation>没有找到有效的代理。</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/batch_import_dialog.py" line="184"/>
        <source>Export Proxies</source>
        <translation>导出代理</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/batch_import_dialog.py" line="186"/>
        <source>Text Files (*.txt);;All Files (*)</source>
        <translation>文本文件 (*.txt);;所有文件 (*)</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/batch_import_dialog.py" line="214"/>
        <source>Success</source>
        <translation>成功</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/batch_import_dialog.py" line="215"/>
        <source>Proxies exported successfully</source>
        <translation>代理已成功导出</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/batch_import_dialog.py" line="223"/>
        <source>Error</source>
        <translation>错误</translation>
    </message>
</context>
<context>
    <name>Config_Dialog</name>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="110"/>
        <source>Add Proxy</source>
        <translation>添加代理</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="113"/>
        <source>Delete Proxy</source>
        <translation>删除代理</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="118"/>
        <source>Import Proxies</source>
        <translation>导入代理</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="121"/>
        <source>Export Proxies</source>
        <translation>导出代理</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="128"/>
        <source>Error</source>
        <translation>错误</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="150"/>
        <source>Name</source>
        <comment>Config_Dialog</comment>
        <translation>代理名称</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="152"/>
        <source>Address</source>
        <comment>Config_Dialog</comment>
        <translation>地址</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="154"/>
        <source>Port</source>
        <comment>Config_Dialog</comment>
        <translation>端口</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="155"/>
        <source>Type</source>
        <comment>Config_Dialog</comment>
        <translation>类型</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="157"/>
        <source>Username</source>
        <comment>Config_Dialog</comment>
        <translation>用户名</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="160"/>
        <source>Password</source>
        <comment>Config_Dialog</comment>
        <translation>密码</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="207"/>
        <source>Port must be between 1 and 65535</source>
        <translation>端口必须在1到65535之间</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="209"/>
        <source>Port must be a valid number</source>
        <translation>端口必须是有效的数字</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="241"/>
        <source>Name</source>
        <translation>代理名称</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="242"/>
        <source>Address</source>
        <translation>地址</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="243"/>
        <source>Port</source>
        <translation>端口</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="244"/>
        <source>Type</source>
        <translation>类型</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="245"/>
        <source>Username</source>
        <translation>用户名</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="246"/>
        <source>Password</source>
        <translation>密码</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="320"/>
        <source>Failed to read proxy list file</source>
        <translation>读取代理列表文件失败</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="381"/>
        <source>Please select a proxy to modify</source>
        <translation>请选择要修改的代理</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="440"/>
        <source>Confirm Delete</source>
        <translation>确认删除</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/config_dialog.py" line="441"/>
        <source>Are you sure you want to delete this proxy?</source>
        <translation>您确定要删除此代理吗？</translation>
    </message>
</context>
<context>
    <name>Dialog_AddProxy</name>
    <message>
        <location filename="../pyproxyswitch/resources/add_proxy.ui" line="14"/>
        <source>Add Proxy</source>
        <translation>添加代理</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/add_proxy.ui" line="26"/>
        <source>Username</source>
        <translation>用户名</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/add_proxy.ui" line="39"/>
        <source>&amp;Authorization</source>
        <translation>代理服务器需要认证(&amp;A)</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/add_proxy.ui" line="65"/>
        <source>Name</source>
        <comment>lable_name</comment>
        <extracomment>Proxy Name</extracomment>
        <translation>代理名称</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/add_proxy.ui" line="78"/>
        <source>Password</source>
        <translation>密码</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/add_proxy.ui" line="107"/>
        <source>Port</source>
        <translation>端口</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/add_proxy.ui" line="146"/>
        <source>Address</source>
        <translation>地址</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/add_proxy.ui" line="173"/>
        <source>HTTP</source>
        <translation>HTTP</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/add_proxy.ui" line="178"/>
        <source>SOCKS4</source>
        <translation>SOCKS4</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/add_proxy.ui" line="183"/>
        <source>SOCKS5</source>
        <translation>SOCKS5</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/add_proxy.ui" line="197"/>
        <source>Type</source>
        <translation>类型</translation>
    </message>
</context>
<context>
    <name>Dialog_Config</name>
    <message>
        <location filename="../pyproxyswitch/resources/pps_conf.ui" line="20"/>
        <source>PPS Settings</source>
        <translation>PyProxySwitch设置</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/pps_conf.ui" line="64"/>
        <source>&amp;Delete</source>
        <translation>删除(&amp;D)</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/pps_conf.ui" line="77"/>
        <source>&amp;Add</source>
        <translation>添加(&amp;A)</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/pps_conf.ui" line="100"/>
        <source>&amp;Modify</source>
        <translation>修改(&amp;M)</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/pps_conf.ui" line="113"/>
        <source>&amp;Batch Add/Mod/Del</source>
        <translation>批量加/改/删(&amp;B)</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/pps_conf.ui" line="52"/>
        <source>Proxy List</source>
        <translation>代理列表</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/pps_conf.ui" line="131"/>
        <source>Local Port</source>
        <translation>本地代理端口</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/pps_conf.ui" line="147"/>
        <source>8888</source>
        <translation>8888</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/pps_conf.ui" line="163"/>
        <source>Debug Mode</source>
        <translation>调试模式</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/pps_conf.ui" line="176"/>
        <source>Show &amp;debug info in console</source>
        <translation>在控制台显示调试信息(&amp;D)</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/pps_conf.ui" line="189"/>
        <source>Language</source>
        <translation>界面语言</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/pps_conf.ui" line="203"/>
        <source>简体中文</source>
        <translation>简体中文</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/pps_conf.ui" line="208"/>
        <source>English</source>
        <translation>English</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/pps_conf.ui" line="222"/>
        <source>Show Welcome</source>
        <translation>显示欢迎信息</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/pps_conf.ui" line="235"/>
        <source>Show &amp;welcome info when program start</source>
        <translation>在程序启动时显示欢迎信息(&amp;S)</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/resources/pps_conf.ui" line="119"/>
        <source>Advanced</source>
        <translation>高级</translation>
    </message>
</context>
<context>
    <name>Window</name>
    <message>
        <location filename="../pyproxyswitch/gui/main_window.py" line="77"/>
        <source>System Tray</source>
        <translation>系统托盘</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/main_window.py" line="79"/>
        <source>I&apos;ve not detected any system tray on this system.
PyProxySwitch cannot start.</source>
        <translation>错误：未找到系统托盘。
PyProxySwitch无法启动。</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/main_window.py" line="149"/>
        <source>Config</source>
        <translation>设置</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/main_window.py" line="152"/>
        <source>About</source>
        <translation>关于</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/main_window.py" line="157"/>
        <source>Quit</source>
        <translation>退出</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/main_window.py" line="197"/>
        <source>About PyProxySwitch</source>
        <translation>关于PyProxySwitch</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/main_window.py" line="200"/>
        <source>&lt;p&gt;Copyright 2009-2026 Kder&lt;/p&gt;&lt;p&gt;A cross-platform proxy switcher with a native Python HTTP/SOCKS server.&lt;/p&gt;&lt;p&gt;Licensed under Apache License 2.0&lt;/p&gt;&lt;p&gt;Visit &lt;a href=&apos;http://pyproxyswitch.kder.info&apos;&gt;http://pyproxyswitch.kder.info&lt;/a&gt; for more information.&lt;/p&gt;</source>
        <translation>&lt;p&gt;Copyright © 2009-2026 Kder&lt;/p&gt;&lt;p&gt;使用 Python 原生 HTTP/SOCKS 服务的跨平台代理切换程序。&lt;/p&gt;&lt;p&gt;采用 Apache License 2.0 授权。&lt;/p&gt;&lt;p&gt;更多信息请访问 &lt;a href=&apos;http://pyproxyswitch.kder.info&apos;&gt;http://pyproxyswitch.kder.info&lt;/a&gt;。&lt;/p&gt;</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/main_window.py" line="218"/>
        <source>Error</source>
        <translation>错误</translation>
    </message>
    <message>
        <location filename="../pyproxyswitch/gui/main_window.py" line="249"/>
        <source>I&apos;m here, welcome to PyProxySwitch!</source>
        <translation>我在这儿，欢迎使用PyProxySwitch！</translation>
    </message>
</context>
</TS>
