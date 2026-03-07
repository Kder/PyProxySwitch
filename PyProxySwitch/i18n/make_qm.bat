@echo off
pylupdate6 -ts zh_CN.ts -ts en.ts ..\res\add_proxy_ui.py ..\res\pps_conf_ui.py
pyside6-lrelease zh_CN.ts
pyside6-lrelease en.ts
pause