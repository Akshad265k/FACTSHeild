@echo off
title FACTSHIELD - React Fact Integrity System
echo.
echo  ============================================
echo   FACTSHIELD - React Fact Integrity
echo  ============================================
echo.

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    set "FACTSHIELD_PY=.venv\Scripts\python.exe"
    echo  [OK] Virtual environment activated
) else (
    set "FACTSHIELD_PY=python"
    echo  [WARN] No .venv found — using system Python
)

REM Ensure dependencies are installed
echo  [..] Checking dependencies...
"%FACTSHIELD_PY%" -m pip install -r requirements.txt -q >nul 2>&1
echo  [OK] Dependencies verified

echo.
echo  Starting Python engine API on http://localhost:8000
echo  Starting React interface on http://localhost:5173
echo  Press Ctrl+C to stop.
echo.

start "FACTSHIELD API" cmd /k "\"%FACTSHIELD_PY%\" -m uvicorn app.api:app --reload --port 8000"
if not exist "frontend\node_modules" (
    echo  [..] Installing React dependencies...
    pushd frontend
    npm install
    popd
)
pushd frontend
npm run dev
