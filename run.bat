@echo off
title Powder Studio AI - 100% Local AI Video Generator
cd /d "%~dp0"
echo ========================================================
echo   Powder Studio AI (Option B: React + FastAPI)
echo   GPU: NVIDIA GeForce RTX 3050 (NVENC Accelerated)
echo ========================================================
echo.
echo Launching Server and UI at http://127.0.0.1:8000 ...
start "" "http://127.0.0.1:8000"
python -m uvicorn server:app --host 127.0.0.1 --port 8000
pause
