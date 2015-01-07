# -*- coding: utf-8 -*-

import sys

from cx_Freeze import setup, Executable

base = None
if sys.platform == "win32":
    base = "Win32GUI"

options =  dict(
    compressed = True,
    optimize = 1,
    append_script_to_exe=True,
    create_shared_zip=True,
    icon = 'PyProxySwitch/src/img/PyProxySwitch.ico',
)
    
    
setup(
        name = "PyProxySwitch",
        version = "3.5",
        description = "A proxy switcher based on Python.",
        options = dict(build_exe = options),
        executables = [Executable(r"PyProxySwitch\src\PyProxySwitch.pyw", 
            base = base)])

