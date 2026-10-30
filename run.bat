@echo off
title AutoShorts Studio - 100% Local AI Video Platform (React + FastAPI)
cd /d "%~dp0"
echo ========================================================
echo   AutoShorts Studio 2.0 (Option B: React + FastAPI)
echo   GPU: NVIDIA GeForce RTX 3050 (NVENC 60 FPS)
echo   AI: Faster-Whisper (CUDA) + Ollama (Llama 3.2)
echo ========================================================
echo.
echo Starting AutoShorts Server at http://127.0.0.1:8000 ...
start "" http://127.0.0.1:8000
python server.py
pause
