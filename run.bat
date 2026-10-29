@echo off
title AutoShorts Studio - 100% Local AI Video Generator
cd /d "%~dp0"
echo ========================================================
echo   AutoShorts Studio (100% Free & Local AI Platform)
echo   GPU: NVIDIA GeForce RTX 3050 (NVENC Accelerated)
echo ========================================================
echo.
echo Launching Web Dashboard at http://127.0.0.1:8501 ...
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.enableCORS false --server.enableXsrfProtection false
pause
