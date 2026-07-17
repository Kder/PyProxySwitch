@echo off
rem Qt Translation Source File Generator
rem This script generates or updates .ts translation source files from all Python source code

echo Generating Qt translation source files (.ts) from all Python files...

rem Update existing .ts files and discard messages no longer present in source.
pyside6-lupdate -no-obsolete -extensions py,ui ^
    "%~dp0..\pyproxyswitch\gui" ^
    "%~dp0..\pyproxyswitch\resources\add_proxy.ui" ^
    "%~dp0..\pyproxyswitch\resources\pps_conf.ui" ^
    -ts "%~dp0zh_CN.ts" "%~dp0en.ts"

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
