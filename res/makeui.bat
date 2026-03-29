@echo off
call pyside6-uic -o pps_conf_ui.py pps_conf.ui
call pyside6-uic -o add_proxy_ui.py add_proxy.ui
pause