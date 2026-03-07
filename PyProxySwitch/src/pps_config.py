#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2011 Kder Lin
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

'''
pps_config is a configuration tool for PyProxySwitch, used to add/delete
proxies.

= Usage =:

== Add a Proxy ==:

    pps_config add proxy_name address:port username:password proxy_type

    "username" and "password" are only required when the proxy needs
    authorization.

    "proxy_type" is optional. Default value is HTTP and supported values
    are SOCKS4 and SOCKS5.

    Examples:
        pps_config add test1 test1.com:8080
        pps_config add test2 test2.com:8080 user:pass
        pps_config add socks_proxy socksproxy.com:3128 SOCKS5
        pps_config add test3 1.2.3.4:80

== Add multiple proxies ==:
    Edit the file "proxy.txt"(with UTF-8 encoding) in "cfg" folder,
    add one proxy per line with the following format:
        proxy_name address:port username:password proxy_type
    "username:password" and "proxy_type" are optional. Refer to the proxy.txt
    file in "cfg" folder or see "Add a Proxy" metioned above for details.

== Delete Proxy/Proxies ==:
    pps_config del proxy_name1 proxy_name2 proxy_name3 ...

    Examples:
        pps_config del test1
        pps_config del test1 test2 test3
'''

__author__ = 'Kder'
__copyright__ = 'Copyright 2009-2011 Kder'
__credits__ = ['Kder']

__version__ = '2.4.7'
__date__ = '2011-03-26'
__maintainer__ = "Kder"
__email__ = '<kderlin (#) gmail dot com>'
__url__ = 'http://www.kder.info'
__license__ = 'Apache License, Version 2.0'
__status__ = 'Beta'

import os
import sys
import codecs
import traceback
import json
import gettext
import shlex
from pathlib import Path
from typing import List, Tuple, Dict, Any

try:
    PATH0 = str(Path(__file__).parent)
except NameError:
    PATH0 = str(Path(sys.path[0]).parent)
if Path(PATH0).is_file():
    PROGRAM_PATH = str(Path(PATH0).parent.parent)
else:
    PROGRAM_PATH = str(Path(PATH0).parent)
CONF = str(Path(PROGRAM_PATH) / 'cfg' / 'PPS.conf')
PROXY_LIST = str(Path(PROGRAM_PATH) / 'cfg' / 'proxy.txt')


def pps_loadcfg(config_file):
    '''加载程序配置文件'''
    try:
        with codecs.open(config_file, 'r', encoding='utf-8') as json_file:
            config = json.load(json_file)
            return config
    #    config = imp.load_source('config', CONF)
    except (ValueError, IOError):
#        pps_output(PPS_MSG['ERR_OPEN_CFG'], 'stderr')
        # pps_exc_handle()
        traceback.print_exc()
        sys.exit(5)


CONFIG = pps_loadcfg(CONF)

_ = gettext.translation('pps_config',
    str(Path(PROGRAM_PATH) / 'i18n'), [CONFIG['LANG']]).gettext

PPS_MSG = {
    'SUCCESS_ADD': _('"%s" added.'),
    'INFO_DEL': _('Deleting "%s" ...'),
    'ERR_DEL_FILE': _('Error when deleting proxy: \
Config files of "%s" does not exist or permission denied.'),
    'USAGE_ADD': _('''
Usage:

Add a Proxy:

    pps_config add proxy_name address:port username:password proxy_type

    "username" and "password" are only required when the proxy needs
    authorization.
    "proxy_type" is optional. Default value is HTTP and supported values are
    SOCKS4 and SOCKS5.

    Examples:
        pps_config add test1 test1.com:8080
        pps_config add test2 test2.com:8080 user:pass
        pps_config add socks_proxy socksproxy.com:3128 SOCKS5
        pps_config add test3 1.2.3.4:80


Add multiple proxies:

    Edit the file "proxy.txt"(with UTF-8 encoding) in "cfg" folder,
    add one proxy per line with the following format:
        proxy_name address:port username:password proxy_type
    "username:password" and "proxy_type" are optional. Refer to the proxy.txt
    file in "cfg" folder
    or see "Add a Proxy" metioned above for details.
'''),
    'ERR_OPEN_CFG': _('Config file reading error: Please make sure that \
cfg/PPS.conf exists and is read-writable.'),
    'SUCCESS_DEL': _('Deleted successfully.'),
    'ERR_SPECIAL_CHAR': _('No special characters, please.'),
    'USAGE_DEL': _('''
Usage:

Delete Proxy/Proxies:
    pps_config del proxy_name1 proxy_name2 proxy_name3 ...

    Examples:
        pps_config del test1
        pps_config del test1 test2 test3
'''),
    'ERR_NAME_NOT_EXIST': _('The proxy "%s" does not exist.'),
    'ERR_CMD_FORMAT': _('Invalid command format.\n'),
    'ERR_SAVE_CFG': _('Config file saving error: Please make sure that each \
subdirectory of "cfg" directory exists and is read-writable.'),
    'ERR_LOAD_LIST': _('Error format of the proxy list file: %s.')
    }
USAGE = _('''
= Usage =:

== Add a Proxy ==:
    pps_config add proxy_name address:port username:password proxy_type

    "username" and "password" are only required when the proxy needs
    authorization.
    "proxy_type" is optional. Default value is HTTP and supported values are
    SOCKS4 and SOCKS5.

    Examples:
        pps_config add test1 test1.com:8080
        pps_config add test2 test2.com:8080 user:pass
        pps_config add socks_proxy socksproxy.com:3128 SOCKS5
        pps_config add test3 1.2.3.4:80

== Add multiple proxies ==:
    Edit the file "proxy.txt"(with UTF-8 encoding) in "cfg" folder,
    add one proxy per line with the following format:
        proxy_name address:port username:password proxy_type
    "username:password" and "proxy_type" are optional. Refer to the proxy.txt
    file in "cfg" folder
    or see "Add a Proxy" metioned above for details.

== Delete Proxy/Proxies ==:
    pps_config del proxy_name1 proxy_name2 proxy_name3 ...

    Examples:
        pps_config del test1
        pps_config del test1 test2 test3
''')

try:
    ACTION = sys.argv[1]
except IndexError:
    ACTION = None


def pps_output(msg: str, dest: str = 'stdout') -> None:
    '''PPS控制台字符串输出函数，支持Python 3+'''
    if not isinstance(msg, str):
        msg = str(msg)
    if dest == 'stderr':
        sys.stderr.buffer.write(msg.encode('utf-8') + b'\n')
    else:
        sys.stdout.buffer.write(msg.encode('utf-8') + b'\n')


def pps_load_proxylist(list_file):
    '''从文件加载代理列表，返回一个6元组(名称, 地址, 端口, 类型, 用户, 密码)
    组成的代理列表
    '''
    proxy_list = []
    try:
        with codecs.open(list_file, 'r', 'utf-8') as l_file:
            for line in l_file.readlines():
                # 使用 shlex 进行安全的分词，支持引号
                items = shlex.split(line.strip())
                if len(items) < 2:
                    continue  # 跳过格式错误的行

                addr_port = items[1].split(':')
                user_pass = ['', '']
                proxy_type = 'HTTP'

                # 检查最后一个元素是否是代理类型
                if items[-1] in ['SOCKS4', 'SOCKS5']:
                    proxy_type = items[-1]

                # 如果有第3个参数，尝试解析用户名:密码
                if len(items) > 2:
                    if ':' in items[2]:
                        user_pass = items[2].split(':', 1)
                        if len(user_pass) == 1:
                            user_pass = [user_pass[0], '']
                    # 如果第3个参数不是代理类型，但后面有参数，则第4个可能是代理类型
                    elif len(items) > 3 and items[3] in ['SOCKS4', 'SOCKS5']:
                        proxy_type = items[3]

                proxy = (items[0], addr_port[0], addr_port[1], proxy_type,
                    user_pass[0], user_pass[1])
                proxy_list.append(proxy)
        return proxy_list
    except IndexError:
        pps_output(PPS_MSG['ERR_LOAD_LIST'] % PROXY_LIST,
            'stderr')
        sys.exit(11)


PROXIES = pps_load_proxylist(PROXY_LIST)
PROXY_NAMES = [p_item[0] for p_item in PROXIES]


def pps_save_proxylist(proxies: List[Tuple[str, ...]] | List[str], list_file: str) -> None:
    '''保存代理列表到文件，列表可为元组的列表或字符串的列表'''
    try:
        with codecs.open(list_file, 'w', 'utf-8') as l_file:
            lines = []
            for i in proxies:
                if isinstance(i, tuple):
                    if i[5]:  # 密码不为空
                        proxy_i = f'{i[0]} {i[1]}:{i[2]} {i[4]}:{i[5]} {i[3]}\r\n'
                    else:
                        proxy_i = f'{i[0]} {i[1]}:{i[2]} {i[3]}\r\n'
                else:
                    proxy_i = f'{i}\r\n'
                lines.append(proxy_i)
            l_file.writelines(lines)
    except OSError:
        pps_output(PPS_MSG['ERR_SAVE_CFG'], 'stderr')


def pps_exc_handle():
    '''PPS异常处理函数'''
    if CONFIG['DEBUG'] == 1:
        traceback.print_exc()


def pps_savecfg(config_dict):
    '''保存程序配置字典到配置文件
       Use json to dump the config dict to file'''
    try:
        with codecs.open(CONF, 'w', encoding='utf-8') as c_file:
            json.dump(config_dict, c_file, indent=2, sort_keys=True)
    except (IOError, TypeError):
        pps_exc_handle()
    #~ return out_str


def add_proxy(proxy: List[str] | Tuple[str, ...], proxy_type: str = 'HTTP') -> None:
    '''添加代理，proxy为一包含(名称, 地址, 端口, 类型, 用户, 密码)
    的列表或元组
    '''
    proxy_check = True
    proxy_name = ''

    # 导入验证器
    from proxy_validation import ProxyValidator, ValidationError
    validator = ProxyValidator()

    try:

        # 解析代理参数
        proxy_name = proxy[0]
        proxy_address = proxy[1].rstrip()
        proxy_port = ''
        proxy_user = ''
        proxy_pass = ''

        # 解析地址和端口
        if ':' in proxy_address:
            addr_parts = proxy_address.rsplit(':', 1)
            proxy_address = addr_parts[0]
            proxy_port = addr_parts[1]
        else:
            proxy_port = proxy[2] if len(proxy) > 2 else ''

        # 解析用户名和密码（如果有）
        if len(proxy) > 2 and ':' in proxy[2]:
            user_pass = proxy[2].split(':', 1)
            proxy_user = user_pass[0]
            proxy_pass = user_pass[1] if len(user_pass) > 1 else ''
        else:
            user_pass = [proxy_user, proxy_pass]

        # 使用验证器验证所有参数
        validated_proxy = validator.validate_full_proxy(
            proxy_name, proxy_address, proxy_port, proxy_type, proxy_user, proxy_pass
        )

        # 使用验证后的参数
        proxy_name = validated_proxy[0]
        proxy_address = validated_proxy[1]
        proxy_port = validated_proxy[2]
        proxy_type = validated_proxy[3]
        proxy_user = validated_proxy[4]
        proxy_pass = validated_proxy[5]

        host_port = [proxy_address, proxy_port]

    except (ValueError, IndexError, ValidationError) as e:
        proxy_check = False
        pps_output(f"验证错误: {e}")
        pps_exc_handle()

    if proxy_check:
        # 开始添加代理项目
        if __name__ == '__main__':
            proxy_tuple = (proxy_name, host_port[0], host_port[1],
                          proxy_type, user_pass[0], user_pass[1])
            for proxy_ in PROXIES:
                if proxy_[0] == proxy_name:
                    PROXIES.remove(proxy_)
            PROXIES.append(proxy_tuple)

        # 添加对应的配置文件
        isauth = user_pass[0] != ''
        ishttp = proxy_type == 'HTTP'
        type_map = {
            'HTTP': ['', ''],
            'SOCKS4': ['socks4a', 'socks4+'],
            'SOCKS5': ['socks5', 'socks5+']
        }

        conf_file_tpl = {
            True: {True: [(
                f'parentProxy = {proxy_address}\r\n'
                f'parentAuthCredentials = {user_pass[0]}:{user_pass[1]}\r\n'
                f'proxyPort = {CONFIG["LOCAL_PORT"]}\r\n'
            ), (
                f'internal 127.0.0.1\r\n'
                f'auth iponly\r\n'
                f'allow * 127.0.0.1\r\n'
                f'parent 1000 http {host_port[0]} {host_port[1]} {user_pass[0]} {user_pass[1]} {CONFIG["LOCAL_PORT"]}\r\n'
                f'proxy -n -a -p{CONFIG["LOCAL_PORT"]}\r\n'
            )],
                False: [
                    f'parentProxy = {proxy_address}\r\nproxyPort = {CONFIG["LOCAL_PORT"]}\r\n',
                    f'internal 127.0.0.1\r\n'
                    f'auth iponly\r\n'
                    f'allow * 127.0.0.1\r\n'
                    f'parent 1000 http {host_port[0]} {host_port[1]} {CONFIG["LOCAL_PORT"]}\r\n'
                    f'proxy -n -a -p{CONFIG["LOCAL_PORT"]}\r\n'
                ]
            },
            False: {True: [(f'socksProxyType = {type_map[proxy_type][0]}\r\n'
                           f'parentAuthCredentials = {user_pass[0]}:{user_pass[1]}\r\n'
                           f'socksParentProxy = {proxy_address}\r\n'
                           f'proxyPort = {CONFIG["LOCAL_PORT"]}\r\n'),
                           (f'internal 127.0.0.1\r\n'
                            f'auth iponly\r\n'
                            f'allow * 127.0.0.1\r\n'
                            f'parent 1000 {type_map[proxy_type][1]} {host_port[0]} {host_port[1]} {user_pass[0]} {user_pass[1]} {CONFIG["LOCAL_PORT"]}\r\n'
                            f'proxy -n -a -p{CONFIG["LOCAL_PORT"]}\r\n'
                           )],
                    False: [
                        f'socksProxyType = {type_map[proxy_type][0]}\r\n'
                        f'socksParentProxy = {proxy_address}\r\n'
                        f'proxyPort = {CONFIG["LOCAL_PORT"]}\r\n',
                        f'internal 127.0.0.1\r\n'
                        f'auth iponly\r\n'
                        f'allow * 127.0.0.1\r\n'
                        f'parent 1000 {type_map[proxy_type][1]} {host_port[0]} {host_port[1]} {CONFIG["LOCAL_PORT"]}\r\n'
                        f'proxy -n -a -p{CONFIG["LOCAL_PORT"]}\r\n'
                    ]
            }
        }

        conf_polipo = conf_file_tpl[ishttp][isauth][0]

        try:
            polipo_path = Path(PROGRAM_PATH) / 'cfg' / 'polipo' / (proxy_name + '.conf')
            with codecs.open(polipo_path, 'w', 'utf-8') as cfg_file:
                cfg_file.write(conf_polipo)
            #if os.name != 'nt':
            conf_3proxy = conf_file_tpl[ishttp][isauth][1]
            proxy3_path = Path(PROGRAM_PATH) / 'cfg' / '3proxy' / (proxy_name + '.conf')
            with codecs.open(proxy3_path, 'w', 'utf-8') as cfg_file:
                cfg_file.write(conf_3proxy)

        except IOError as e:
            pps_output(PPS_MSG['ERR_SAVE_CFG'] % proxy_name)
            pps_exc_handle()
            sys.exit(2)
        if __name__ == '__main__':
            pps_output(PPS_MSG['SUCCESS_ADD'] % proxy_name)
    elif proxy_check is False and ACTION is not None:
        pps_output(PPS_MSG['ERR_CMD_FORMAT'] + PPS_MSG['USAGE_ADD'])


def del_proxy(proxy: List[str] | Tuple[str, ...] | Set[str]) -> None:
    '''删除代理项，proxy为一由代理名称组成的序列（元组、列表或集合）'''
    deleted = True

    for proxy_name in proxy:
        if not isinstance(proxy_name, str):
            proxy_name = proxy_name

        if __name__ == '__main__':
            for i in PROXIES[:]:  # 使用副本避免迭代时修改
                if i[0] == proxy_name:
                    PROXIES.remove(i)
            pps_output(PPS_MSG['INFO_DEL'] % proxy_name)

        # 移除对应的配置文件
        try:
            polipo_path = Path(PROGRAM_PATH) / 'cfg' / 'polipo' / (proxy_name + '.conf')
            os.remove(polipo_path)
            #if os.name != 'nt':
            proxy3_path = Path(PROGRAM_PATH) / 'cfg' / '3proxy' / (proxy_name + '.conf')
            os.remove(proxy3_path)
        except OSError:
            pps_output(PPS_MSG['ERR_DEL_FILE'] % proxy_name, 'stderr')
            deleted = False
            pps_exc_handle()
    if __name__ == '__main__' and deleted:
        pps_output(PPS_MSG['SUCCESS_DEL'])


if __name__ == '__main__':
    #简单的命令行参数处理

    # 添加单个代理
    if ACTION == 'add':
        if len(sys.argv) < 4:
            pps_output(PPS_MSG['ERR_CMD_FORMAT'] + PPS_MSG['USAGE_ADD'])
            sys.exit(10)
        if sys.argv[-1] in ['HTTP', 'SOCKS4', 'SOCKS5']:
            add_proxy(sys.argv[2:-1], sys.argv[-1])
        else:
            add_proxy(sys.argv[2:])

    # 批量添加代理
    elif ACTION is None:
        with codecs.open(PROXY_LIST, 'r', 'utf-8') as file1:
            for proxy_line in file1.readlines():
                proxy_item = proxy_line.split()
                if proxy_item[-1] in ['HTTP', 'SOCKS4', 'SOCKS5']:
                    add_proxy(proxy_item[0:-1], proxy_item[-1])
                else:
                    add_proxy(proxy_item)

    # 删除单个/多个代理
    elif ACTION == 'del':
        if len(sys.argv) == 2:
            pps_output(PPS_MSG['ERR_CMD_FORMAT'] + PPS_MSG['USAGE_DEL'])
            sys.exit(8)
        del_proxy(sys.argv[2:])

    # 显示帮助信息
    else:
        pps_output(PPS_MSG['ERR_CMD_FORMAT'] + USAGE)
        sys.exit(6)

    pps_save_proxylist(PROXIES, PROXY_LIST)
    sys.exit(0)

#vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
