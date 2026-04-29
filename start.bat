@echo off

start cmd /k "cd backend\sqlite_query_service && call ..\..\.venv\Scripts\activate.bat && set PDD_API_PORT=8082 && python main.py"
start cmd /k "cd backend\\ai_service && call ..\\..\\.venv\\Scripts\\activate.bat && python main.py"
start cmd /k "cd backend\backend_service && pocketbase.exe serve"
start cmd /k "cd pdd-frontend && npm run dev"

pause
