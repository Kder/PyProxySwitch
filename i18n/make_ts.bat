@echo off
rem Qt Translation Source File Generator
rem This script generates or updates .ts translation source files from all Python source code

echo Generating Qt translation source files (.ts) from all Python files...

rem Update existing .ts files with new strings from all relevant Python source code
pylupdate6 -ts "%~dp0..\i18n\zh_CN.ts" -ts "%~dp0..\i18n\en.ts" ^
    "%~dp0..\res\add_proxy_ui.py" ^
    "%~dp0..\res\pps_conf_ui.py" ^
    "%~dp0..\src\gui\main_window.py" ^
    "%~dp0..\src\gui\config_dialog.py" ^
    "%~dp0..\src\gui\add_proxy_dialog.py" ^
    "%~dp0..\src\gui\batch_import_dialog.py" ^
    "%~dp0..\src\main.py" ^
    "%~dp0..\src\config.py" ^
    "%~dp0..\src\proxy_manager.py" ^
    "%~dp0..\src\pps_config.py" ^
    "%~dp0..\src\logger_config.py" ^
    "%~dp0..\src\errors.py" ^
    "%~dp0..\src\proxy_validation.py"

if %errorlevel% equ 0 (
    echo.
    echo Translation source files updated successfully!
    echo All Python source files have been processed for translation strings.
    echo You can now compile them to .qm files using make_qm.bat
) else (
    echo.
    echo Error occurred during translation file generation!
)

echo.
pause