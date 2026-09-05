@echo off
title FACTSHIELD React UI
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    set "FACTSHIELD_PY=.venv\Scripts\python.exe"
) else (
    set "FACTSHIELD_PY=python"
)
start "FACTSHIELD API" cmd /k "\"%FACTSHIELD_PY%\" -m uvicorn app.api:app --reload --port 8000"
cd frontend
if not exist node_modules npm install
npm run dev
