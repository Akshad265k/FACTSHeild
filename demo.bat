@echo off
title FACTSHIELD Demo
echo.
echo  ============================================
echo   FACTSHIELD Demo Runner
echo  ============================================
echo.

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

echo  [1/3] Running test suite...
python -m pytest tests/ -v --tb=short
echo.

echo  [2/3] Running benchmark on release_001...
python -m evaluation.benchmark --release release_001
echo.

echo  [3/3] Launching Streamlit app...
echo  Open http://localhost:8501 in your browser
python -m streamlit run run.py --server.headless true
