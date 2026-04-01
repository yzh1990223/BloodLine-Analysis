@echo off
setlocal
chcp 65001 >nul

set "ROOT_DIR=%~dp0"

title BloodLine Analysis Launcher
echo [信息] 即将分别打开前后端启动窗口...

start "BloodLine Backend" cmd /k ""%ROOT_DIR%start-backend.bat""
start "BloodLine Frontend" cmd /k ""%ROOT_DIR%start-frontend.bat""

echo [信息] 已发起前后端启动，请查看新打开的两个窗口。
timeout /t 2 >nul
endlocal
