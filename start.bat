@echo off
rem Starts backend + frontend in two windows and opens the app.
rem Keep both windows open while you use the app.

cd /d "%~dp0"

if not exist "backend\venv\Scripts\python.exe" (
    echo Setting up backend for the first time...
    python -m venv backend\venv
    backend\venv\Scripts\python -m pip install -r backend\requirements.txt
)

if not exist "frontend\node_modules" (
    echo Installing frontend packages for the first time...
    call npm --prefix frontend install
)

if not exist "backend\.env" (
    copy "backend\.env.example" "backend\.env" >nul
    echo Created backend\.env - add your TAVILY_API_KEY and GEMINI_API_KEY there.
)

start "Backend (port 8000)" cmd /k "cd /d "%~dp0backend" && venv\Scripts\python main.py"
start "Frontend (port 5173)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

rem Give the servers a few seconds to start
timeout /t 6 /nobreak >nul

start "" http://localhost:5173
