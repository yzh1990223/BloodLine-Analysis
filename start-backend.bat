@echo off
setlocal
chcp 65001 >nul

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "PYTHON_EXE=%BACKEND_DIR%\.venv\Scripts\python.exe"

title BloodLine Analysis Backend

if not exist "%BACKEND_DIR%" (
  echo [错误] 未找到 backend 目录：%BACKEND_DIR%
  pause
  exit /b 1
)

if not exist "%PYTHON_EXE%" (
  echo [错误] 未找到后端虚拟环境：%PYTHON_EXE%
  echo.
  echo 请先在 Windows 终端中完成依赖安装，例如：
  echo   cd /d "%BACKEND_DIR%"
  echo   uv sync --project . --extra dev
  pause
  exit /b 1
)

pushd "%BACKEND_DIR%"

echo [信息] 正在执行数据库迁移...
"%PYTHON_EXE%" -m alembic upgrade head
if errorlevel 1 (
  echo [错误] Alembic 迁移失败，请先检查数据库状态。
  popd
  pause
  exit /b 1
)

echo [信息] 正在启动后端服务：http://127.0.0.1:8000
set "PYTHONPATH=src"
"%PYTHON_EXE%" -m uvicorn bloodline_api.main:app --host 127.0.0.1 --port 8000

if errorlevel 1 (
  echo.
  echo [错误] 后端服务启动失败，请查看上方日志。
  popd
  pause
  exit /b 1
)

popd
endlocal
