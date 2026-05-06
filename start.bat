@echo off
setlocal

rem Always run commands from the folder where this script is located.
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] Python venv not found: .venv\Scripts\activate.bat
  echo Create it first with: python -m venv .venv
  pause
  exit /b 1
)

if not exist "pdd-frontend\node_modules" (
  echo [INFO] Installing frontend dependencies...
  pushd pdd-frontend
  call npm install
  if errorlevel 1 (
    echo [ERROR] npm install failed.
    popd
    pause
    exit /b 1
  )
  popd
)

start cmd /k "cd /d backend\sqlite_query_service && call ..\..\.venv\Scripts\activate.bat && set PDD_API_PORT=8082 && python main.py"
start cmd /k "cd /d backend\ai_service && call ..\..\.venv\Scripts\activate.bat && python main.py"
start cmd /k "cd /d backend\backend_service && pocketbase.exe serve"
start cmd /k "cd /d pdd-frontend && npm run dev"

pause
