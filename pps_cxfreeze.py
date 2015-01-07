#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cx_Freeze
import sys
import os
import subprocess
import shutil
import glob
import sip
sip.setapi('QVariant', 2)

import PyQt4

sys.path = sys.path + ['PyProxySwitch/src/', 'PyProxySwitch/res/']

import pps_config
import PyProxySwitch
version = PyProxySwitch.__version__


msg = {'welcome': '''
 =================================================
 　　*　　　　　　　　*　　　　　　　　*
    PyProxySwitch自动编译/打包程序   by Kder

【注意：请先根据情况修改第65行path7z中7-zip的路径】
 　　*　　　　　　　　*　　　　　　　　*
 =================================================
''',
    'continue': '是否继续？（y/n）：',
    'freezing': '\n开始编译……\n',
    'package_prompt': ''''
   Windows/Linux二进制版和源码版将被分别打包为7z/lzma格式
   若不想自动打包，请输入n退出。
''',
    'packaging': '\n开始打包……\n',
    'success': '\n编译及打包结束，谢谢使用。\n',
    }


# version = pps_config.__version__
FENC = pps_config.FENC
ISPY2 = pps_config.ISPY2
if ISPY2:
    for i in msg:
        msg[i] = msg[i].decode('utf-8').encode(FENC)
pps_config.pps_output(msg['welcome'])
srcDir = 'PyProxySwitch'
src_archive = "PyProxySwitch-%s-src" % version
targetDir = "PyProxySwitch-%s/bin" % version
bin_archive = "PyProxySwitch-%s" % version
base = None
includeFiles = [
    ('PyProxySwitch/src', '../src'), ('PyProxySwitch/i18n', '../i18n'),
    ('PyProxySwitch/cfg', '../cfg'), ('PyProxySwitch/licenses', '../licenses'),
    ('PyProxySwitch/img', '../img'), ('PyProxySwitch/res', '../res'),
    ('PyProxySwitch/README_zh_CN.txt', '../README_zh_CN.txt'),
    ('PyProxySwitch/README_en.txt', '../README_en.txt')]

if os.name == 'nt':
    base = "Win32GUI"
    targetDir = "PyProxySwitch-%s-win/bin" % version
    bin_archive = "PyProxySwitch-%s-win" % version
    path7z = 'F:\\Program Files\\7-Zip'
    includeFiles.extend([
        (os.path.join(PyQt4.__path__[0], '__init__.pyc'),
            '../lib/PyQt4/__init__.pyc'),
        (os.path.join(PyQt4.__path__[0], 'QtCore.pyd'),
            '../lib/PyQt4/QtCore.pyd'),
        (os.path.join(PyQt4.__path__[0], 'QtGui.pyd'),
            '../lib/PyQt4/QtGui.pyd'),
        (os.path.join(PyQt4.__path__[0], 'bin', 'QtCore4.dll'),
            '../lib/QtCore4.dll'),
        (os.path.join(PyQt4.__path__[0], 'bin', 'QtGui4.dll'),
            '../lib/QtGui4.dll'),
        ('PyProxySwitch/bin/polipo/polipo.exe',
        '../bin/polipo/polipo.exe'),
        ('PyProxySwitch/bin/polipo/libgnurx-0.dll',
        '../bin/polipo/libgnurx-0.dll'),
        ('PyProxySwitch/bin/ip_relay/ip_relay.exe',
        '../bin/ip_relay/ip_relay.exe'),
        ('PyProxySwitch/bin/ip_relay/lib_ip_relay.lib',
        '../bin/ip_relay/lib_ip_relay.lib')])
elif os.name == 'posix':
    includeFiles.extend([
        ('PyProxySwitch/bin/polipo/polipo', '../bin/polipo/polipo'),
        ('PyProxySwitch/bin/3proxy/3proxy', '../bin/3proxy/3proxy'),
        ('PyProxySwitch/bin/ip_relay/ip_relay', '../bin/ip_relay/ip_relay'),
        ('PyProxySwitch/bin/ip_relay/lib_ip_relay_linux_i386_so.o',
         '../bin/ip_relay/lib_ip_relay_linux_i386_so.o'),
        ('PyProxySwitch/bin/ip_relay/lib_ip_relay_linux_i386_gcc.a',
         '../bin/ip_relay/lib_ip_relay_linux_i386_gcc.a'),
        ('PyProxySwitch/bin/ip_relay/lib_ip_relay_linux_i386.so.1.0.1',
         '../bin/ip_relay/lib_ip_relay_linux_i386.so.1.0.1'),
        ('libQtCore.so.4', '../bin/libQtCore.so.4'),
        ('libQtGui.so.4', '../bin/libQtGui.so.4'),
        ('libpng14.so.14', '../bin/libpng14.so.14'),
        ('libEGL.so.1', '../bin/libEGL.so.1')])


class metadata:
    name = 'PyProxySwitch'
    version = version
    author = '%s %s' % (PyProxySwitch.__author__, PyProxySwitch.__email__)
#    author = PyProxySwitch.__author__
    author_email = PyProxySwitch.__email__
    maintainer = PyProxySwitch.__maintainer__
    maintainer_email = PyProxySwitch.__email__
    url = PyProxySwitch.__projecturl__
    description = 'A proxy switcher based on Python.'
    long_description = PyProxySwitch.__doc__
    download_url = PyProxySwitch.__projecturl__ + '/download'
    classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: End Users/Desktop',
    'Intended Audience :: Advanced End Users',
    'Intended Audience :: Developers',
    'Intended Audience :: System Administrators',
    'License :: Apache License V2.0',
    'Operating System :: OS Independent (Written in an interpreted language)',
    'Programming Language :: Python',
    'Topic :: Networking',
    'Translations :: Chinese (Simplified)',
    'User Interface :: Qt',
    ]
    platforms = ['Windows', 'Linux', ]
    license = PyProxySwitch.__license__
    copyright = PyProxySwitch.__copyright__


metadata1 = metadata()
metadata2 = metadata()
try:
    metadata1.description = '快速代理切换程序'.decode('utf-8')
    metadata2.description = 'PyProxySwitch命令行配置工具'.decode('utf-8')
except:
    metadata1.description = '快速代理切换程序'
    metadata2.description = 'PyProxySwitch命令行配置工具'


freezer1 = cx_Freeze.Freezer(
            [cx_Freeze.Executable('PyProxySwitch/src/PyProxySwitch.pyw',
                base=base)],
#                base='Console')],
        includes=['pps_qrc', 'pps_config', 'add_proxy_ui', 'pps_conf_ui'],
        excludes=['PyQt4', 'unicodedata', 'bz2'],
        # replacePaths = options.replacePaths,
        compress=True,
        optimizeFlag=1,
        # initScript = options.initScript,
        #~ path = ,
        createLibraryZip=False,
        appendScriptToExe=True,
        targetDir=targetDir,
#        copyDependentFiles=False,
        # zipIncludes = options['zipIncludes'],
        includeFiles=includeFiles,
        icon='./PyProxySwitch/img/PyProxySwitch.ico',
        # silent = options.silent
        metadata=metadata1
        )


freezer2 = cx_Freeze.Freezer(
            [cx_Freeze.Executable("PyProxySwitch/src/pps_config.py",
                base='Console')],
        excludes=['PyQt4', 'unicodedata', 'bz2'],
        compress=True,
        optimizeFlag=1,
        createLibraryZip=False,
        appendScriptToExe=True,
        targetDir=targetDir,
        copyDependentFiles=True,
#        includeFiles=includeFiles,
        icon='./PyProxySwitch/img/PyProxySwitch.ico',
        metadata=metadata2
        )


if ISPY2:
    ans = raw_input(msg['continue'])
else:
    ans = input(msg['continue'])
if ans == 'n' or ans == 'n\r':
    sys.exit(0)

pps_config.pps_output(msg['freezing'])
freezer1.Freeze()
freezer2.Freeze()

if os.name == 'nt':
    try:
        shutil.rmtree(os.path.join(bin_archive, 'cfg', '3proxy'))
    except WindowsError:
        pass
libdir = os.path.join(bin_archive, 'lib')
#if not os.path.exists(libdir):
#    os.mkdir(libdir)
#else:
#    shutil.rmtree(libdir)
#    os.mkdir(libdir)
for item in glob.glob(os.path.join(targetDir, '*.pyd')):  # + \
        # glob.glob(os.path.join(targetDir, '*.dll')):
    try:
        shutil.move(item, libdir)
    except shutil.Error:
        pass

for pattern in [item % os.sep for item in ['*%s*.pyc', '*%s*.bat',
 'i18n%s*.pot', 'i18n%s*.ts', 'i18n%s*.pro', 'res%s*.ui', 'res%s*.qrc',
 'img%sThumbs.db']] + ['i18n%s*%s*%s*.po' % (os.sep, os.sep, os.sep)]:
    for file_ in glob.glob(os.path.join(bin_archive, pattern)):
        os.remove(file_)

pps_config.pps_output(msg['package_prompt'])
if ISPY2:
    ans = raw_input(msg['continue'])
else:
    ans = input(msg['continue'])
if ans == 'n' or ans == 'n\r':
    sys.exit(0)

pps_config.pps_output(msg['packaging'])

if os.name == 'nt' and not ('7-zip' in os.path.expandvars('$PATH')):
#    os.path.defpath = os.path.defpath+os.path.pathsep+path7z
#    os.environ['PATH'] = os.environ['PATH']+
    os.environ['PATH'] += os.path.pathsep + path7z

    subprocess.call(['7z', 'a', '-xr!*.db', '-xr!*.pyc', '-xr!*__pycache__*',
        src_archive + '.7z', srcDir])
    subprocess.call(['7z', 'a', '-xr!*.db', '-xr!*__pycache__*',
        bin_archive + '.7z', bin_archive])
else:
    subprocess.call(['tar', 'cavf', src_archive + '.tar.lzma', srcDir])
    subprocess.call(['tar', 'cavf', bin_archive + '.tar.lzma', bin_archive])

pps_config.pps_output(msg['success'])
