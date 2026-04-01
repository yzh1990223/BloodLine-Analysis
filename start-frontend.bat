@echo off
setlocal
chcp 65001 >nul

set "ROOT_DIR=%~dp0"
set "FRONTEND_DIR=%ROOT_DIR%frontend"

title BloodLine Analysis Frontend

if not exist "%FRONTEND_DIR%" (
  echo [错误] 未找到 frontend 目录：%FRONTEND_DIR%
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [错误] 未检测到 npm，请先安装 Node.js，并确保 npm 已加入 PATH。
  pause
  exit /b 1
)

if not exist "%FRONTEND_DIR%\node_modules" (
  echo [错误] 未找到前端依赖目录：%FRONTEND_DIR%\node_modules
  echo.
  echo 请先在 Windows 终端中执行：
  echo   cd /d "%FRONTEND_DIR%"
  echo   npm install
  pause
  exit /b 1
)

pushd "%FRONTEND_DIR%"
echo [信息] 正在启动前端服务：http://127.0.0.1:5173
call npm run dev -- --host 127.0.0.1 --port 5173

if errorlevel 1 (
  echo.
  echo [错误] 前端服务启动失败，请查看上方日志。
  popd
  pause
  exit /b 1
)

popd
endlocal
