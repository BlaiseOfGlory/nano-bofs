@echo off
setlocal
set "ROOT=%~dp0"
set "NANO_BOFS_DEFAULT_BACKEND=docker"
set "NANO_BOFS_STATE_DIR=%ROOT%.nano-bofs-state"
set "UV_PROJECT_ENVIRONMENT=.venv-win"
set "UV_PYTHON_PREFERENCE=only-system"
set "UV_CACHE_DIR=%ROOT%.uv-cache"
cd /d "%ROOT%"
uv sync --frozen >> "%ROOT%local-remote.log" 2>&1
if errorlevel 1 exit /b %errorlevel%
".venv-win\Scripts\python.exe" main.py >> "%ROOT%local-remote.log" 2>&1
