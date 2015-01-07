@echo off
xgettext --from-code=utf8 -L Python -o pps_config.pot ..\src\pps_config.py
msgmerge -U .\zh_CN\LC_MESSAGES\pps_config.po pps_config.pot
msgmerge -U .\en\LC_MESSAGES\pps_config.po pps_config.pot
msgfmt -o .\zh_CN\LC_MESSAGES\pps_config.mo .\zh_CN\LC_MESSAGES\pps_config.po
msgfmt -o .\en\LC_MESSAGES\pps_config.mo .\en\LC_MESSAGES\pps_config.po
pause