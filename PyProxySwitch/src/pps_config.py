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

import sys
import os
import codecs
import traceback
import json
import gettext
#import locale
#locale.setlocale(locale.LC_ALL, '')
#enc = locale.getpreferredencoding()
#enc = 'utf-8'
#sys.stdout = codecs.getreader(enc)(sys.stdout)
#sys.stderr = codecs.getreader(enc)(sys.stderr)
#sys.stdin = codecs.getreader(enc)(sys.stdin)

ISPY2 = False
#if sys.version_info.major == 2:
if sys.version_info[0] == 2:
    ISPY2 = True

FENC = sys.getfilesystemencoding()
PATH0 = ''
try:
    PATH0 = os.path.dirname(os.path.abspath(__file__))
except NameError:
    PATH0 = os.path.dirname(sys.path[0])
if os.path.isfile(PATH0):
    PROGRAM_PATH = os.path.dirname(os.path.dirname(PATH0))
else:
    PROGRAM_PATH = os.path.dirname(PATH0)
try:
    PROGRAM_PATH = PROGRAM_PATH.decode(FENC)
except AttributeError:
    pass
CONF = os.path.join(PROGRAM_PATH, 'cfg', 'PPS.conf')
PROXY_LIST = os.path.join(PROGRAM_PATH, 'cfg', 'proxy.txt')


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
    os.path.join(PROGRAM_PATH, 'i18n'), [CONFIG['LANG']]).gettext

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


def pps_output(msg, dest='stdout'):
    '''PPS控制台字符串输出函数，可同时支持Python2和3，并避免乱码'''
    try:
        msg = msg.decode('utf8').encode(FENC)
    except (AttributeError, UnicodeError):
        pass
    if dest == 'stderr':
        sys.stderr.write(msg + '\n')
    else:
        sys.stdout.write(msg + '\n')


def pps_load_proxylist(list_file):
    '''从文件加载代理列表，返回一个6元组(名称, 地址, 端口, 类型, 用户, 密码)
    组成的代理列表
    '''
    proxy_list = []
    try:
        with codecs.open(list_file, 'r', 'utf-8') as l_file:
            for line in l_file.readlines():
                items = line.split()
                addr_port = items[1].split(':')
                user_pass = ['', '']
                proxy_type = 'HTTP'
                if items[-1] == 'SOCKS4' or items[-1] == 'SOCKS5':
                    proxy_type = items[-1]
                if len(items) > 2:
                    user_pass = items[2].split(':')
                    if len(user_pass) == 1:
                        user_pass = ['', '']
                # print items, addr_port, user_pass
                proxy = (items[0], addr_port[0], addr_port[1], proxy_type,
                    user_pass[0], user_pass[1])
                proxy_list.append(proxy)
        return proxy_list
    except IndexError:
        pps_output(PPS_MSG['ERR_LOAD_LIST'] % PROXY_LIST.encode('utf-8'),
            'stderr')
        sys.exit(11)


PROXIES = pps_load_proxylist(PROXY_LIST)
PROXY_NAMES = [p_item[0] for p_item in PROXIES]


def pps_save_proxylist(proxies, list_file):
    '''保存代理列表到文件，列表可为元组的列表或字符串的列表'''
    try:
        with codecs.open(list_file, 'w', 'utf-8') as l_file:
            lines = []
            proxy_i = ''
            for i in proxies:
                if type(i) == type(tuple()):
                    if i[5] != '':
                        proxy_i = '%s %s:%s %s:%s %s\r\n' % (i[0], i[1], i[2],
                            i[4], i[5], i[3])
                    else:
                        proxy_i = '%s %s:%s %s\r\n' % (i[0], i[1], i[2], i[3])
                else:
                    proxy_i = '%s\r\n' % i
                lines.append(proxy_i)
            # print proxies
            l_file.writelines(lines)
    except (IOError, WindowsError):
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


def add_proxy(proxy, proxy_type='HTTP'):
    '''添加代理，proxy为一包含(名称, 地址, 端口, 类型, 用户, 密码)
    的列表或元组
    '''
    proxy_check = True
    proxy_name = ''
    try:
        proxy_name = proxy[0]  # .decode(FENC).encode('utf-8')
        proxy_address = proxy[1].rstrip()
        host_port = proxy_address.split(':')
        try:
            proxy_name = proxy_name.decode(FENC)
        except (AttributeError, UnicodeError):
            pass
        # check if address:port has correct format
        assert (':' in proxy_address) and ('' not in host_port)
        user_pass = ['', '']
        if len(proxy) > 2:
            user_pass = proxy[2].split(':')
            #保证用户名密码均不为空，且以冒号隔开
            assert (':' in proxy[2]) and ('' not in user_pass)

    except (AssertionError, IndexError):
        proxy_check = False
        pps_exc_handle()
        # print(sys.exc_info()[2].tb_lasti) #+sys.exc_info()[2].tb_lineno
        #~ sys.exit(1)

    #避免特殊字符 #, '$', '&', '(', ')',

    if set(['"', '\\', '/', ':', '*', '?',  # {'a', 'b'} syntax is for Py2.7+
        '<', '>', '|']) & set(proxy_name) != set():
        pps_output(PPS_MSG['ERR_SPECIAL_CHAR'])
        proxy_check = False
            #~ sys.exit(7)
    #检查有无重复
# if proxy_name in config['CFG_3proxy'] or \
#proxy_name in config['CFG_polipo']:
    # pps_output(PPS_MSG['ERR_NAME_EXISTS'] %
    # proxy_name, 'stderr')
    # proxy_check = False
    #~ sys.exit(2)

    if proxy_check:
        #开始添加代理项目
        # new_names = []
        if __name__ == '__main__':
            # new_names.append(proxy_name)
            proxy = (proxy_name, host_port[0], host_port[1],
                proxy_type, user_pass[0], user_pass[1])
            for proxy_ in PROXIES:
                if proxy_[0] == proxy_name:
                    PROXIES.remove(proxy_)
            PROXIES.append(proxy)

        #添加对应的配置文件
        isauth = user_pass[0] != ''
        ishttp = proxy_type == 'HTTP'
        type_map = {
                'HTTP': ['', ''],
                'SOCKS4': ['socks4a', 'socks4+'],
                'SOCKS5': ['socks5', 'socks5+']
                }

        conf_file_tpl = {
        True: {True: [(
                    'parentProxy = %s\r\n'
                    'parentAuthCredentials = %s:%s\r\n'
                    'proxyPort = %s\r\n'
                    ) % (proxy_address, user_pass[0], user_pass[1],
                        CONFIG['LOCAL_PORT']),
                    ('internal 127.0.0.1\r\n'
                    'auth iponly\r\n'
                    'allow * 127.0.0.1\r\n'
                    'parent 1000 http %s %s %s %s\r\n'
                    'proxy -n -a -p%s\r\n') % \
                        (host_port[0], host_port[1], user_pass[0],
                            user_pass[1], CONFIG['LOCAL_PORT'])
                 ],
                 False: [
                    'parentProxy = %s\r\nproxyPort = %s\r\n' % \
                      (proxy_address, CONFIG['LOCAL_PORT']),
                    ('internal 127.0.0.1\r\n'
                    'auth iponly\r\n'
                    'allow * 127.0.0.1\r\n'
                    'parent 1000 http %s %s\r\n'
                    'proxy -n -a -p%s\r\n') % (host_port[0], host_port[1],
                        CONFIG['LOCAL_PORT'])
                 ]
                },
        False: {True: [('socksProxyType = %s\r\n'
                        'parentAuthCredentials = %s:%s\r\n'
                        'socksParentProxy = %s\r\n'
                        'proxyPort = %s\r\n') % (type_map[proxy_type][0],
                        user_pass[0], user_pass[1],
                        proxy_address, CONFIG['LOCAL_PORT']),
                        ('internal 127.0.0.1\r\n'
                        'auth iponly\r\n'
                        'allow * 127.0.0.1\r\n'
                        'parent 1000 %s %s %s %s %s\r\n'
                        'proxy -n -a -p%s\r\n') % (type_map[proxy_type][1],
                            host_port[0], host_port[1],
                            user_pass[0], user_pass[1], CONFIG['LOCAL_PORT'])
                        ],
                False: [
                        ('socksProxyType = %s\r\n'
                        'socksParentProxy = %s\r\n'
                        'proxyPort = %s\r\n') % (type_map[proxy_type][0],
                        proxy_address, CONFIG['LOCAL_PORT']),
                        ('internal 127.0.0.1\r\n'
                        'auth iponly\r\n'
                        'allow * 127.0.0.1\r\n'
                        'parent 1000 %s %s %s\r\n'
                        'proxy -n -a -p%s\r\n') % (type_map[proxy_type][1],
                        host_port[0], host_port[1], CONFIG['LOCAL_PORT'])
                ]
                }
        }

        conf_polipo = conf_file_tpl[ishttp][isauth][0]

        try:
            with codecs.open(os.path.join(PROGRAM_PATH, 'cfg', 'polipo',
                    proxy_name + '.conf'), 'w', 'utf-8') as cfg_file:
                cfg_file.write(conf_polipo)
            if os.name != 'nt':
                conf_3proxy = conf_file_tpl[ishttp][isauth][1]
                with codecs.open(os.path.join(PROGRAM_PATH, 'cfg', '3proxy',
                        proxy_name + '.conf'), 'w', 'utf-8') as cfg_file:
                    cfg_file.write(conf_3proxy)

        except IOError:
            pps_output(PPS_MSG['ERR_SAVE_CFG'] % proxy_name.encode('utf-8'))
            pps_exc_handle()
            sys.exit(2)
        if __name__ == '__main__':
            # in 2.x, .encode is needed,but in 3.x this will result in b'\xxx'
            # output
            pps_output(PPS_MSG['SUCCESS_ADD'] % proxy_name.encode('utf-8'))
    elif proxy_check == False and ACTION != None:
        pps_output(PPS_MSG['ERR_CMD_FORMAT'] +
            PPS_MSG['USAGE_ADD'])


def del_proxy(proxy):
    '''删除代理项，proxy为一由代理名称组成的序列（元组、列表或集合）'''
    deleted = True

    for proxy_name in proxy:
        try:
            proxy_name = proxy_name.decode(FENC)
        except (UnicodeError, AttributeError):
            pass

        if __name__ == '__main__':
            for i in PROXIES:
                if i[0] == proxy_name:
                    PROXIES.remove(i)
        if __name__ == '__main__':
            pps_output(PPS_MSG['INFO_DEL'] % proxy_name.encode('utf-8'))

        #移除对应的配置文件
        try:
            os.remove(os.path.join(PROGRAM_PATH, 'cfg', 'polipo',
                      proxy_name + '.conf'))
            if os.name != 'nt':
                os.remove(os.path.join(PROGRAM_PATH, 'cfg', '3proxy',
                      proxy_name + '.conf'))
        except (OSError, WindowsError):
            pps_output(PPS_MSG['ERR_DEL_FILE'] % proxy_name.encode('utf-8'),
                'stderr')
            deleted = False
            pps_exc_handle()
    if __name__ == '__main__' and deleted is True:
        pps_output(PPS_MSG['SUCCESS_DEL'])


if __name__ == '__main__':
    #简单的命令行参数处理

    #添加单个代理
    if ACTION == 'add':
        if len(sys.argv) < 4:
            pps_output(PPS_MSG['ERR_CMD_FORMAT'] +
                PPS_MSG['USAGE_ADD'])
            sys.exit(10)
#        print(sys.argv)
        if sys.argv[-1] in ['HTTP', 'SOCKS4', 'SOCKS5']:
            add_proxy(sys.argv[2:-1], sys.argv[-1])
        else:
            add_proxy(sys.argv[2:])

    #批量添加代理
    elif ACTION == None:
        with codecs.open(PROXY_LIST, 'r', 'utf-8') as file1:
            for proxy_line in file1.readlines():
                proxy_item = proxy_line.split()
                #~ print(proxy)
                if proxy_item[-1] in ['HTTP', 'SOCKS4', 'SOCKS5']:
                    add_proxy(proxy_item[0:-1], proxy_item[-1])
                else:
                    add_proxy(proxy_item)

    #删除单个/多个代理
    elif ACTION == 'del':
        if len(sys.argv) == 2:
            pps_output(PPS_MSG['ERR_CMD_FORMAT'] +
                PPS_MSG['USAGE_DEL'])
            sys.exit(8)
        del_proxy(sys.argv[2:])

    #显示帮助信息
    else:
        pps_output(PPS_MSG['ERR_CMD_FORMAT'] + USAGE)
        sys.exit(6)
#    print(pps_savecfg(config))
    # pps_savecfg(config)
    pps_save_proxylist(PROXIES, PROXY_LIST)
    sys.exit(0)

#vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
