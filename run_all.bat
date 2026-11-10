@echo off
title BMD-HS Full Diagnostic System Launcher
echo =========================================================================
echo    BMD-HS Clinical Diagnostic Suite - All Systems Launcher
echo =========================================================================
echo.
echo 1. Starting FastAPI AI Backend (port 8000)...
start "BMD-HS AI Backend (:8000)" cmd /k "python app.py"

echo 2. Waiting for backend initialization...
timeout /t 3 /nobreak >nul

echo 3. Opening Live Server in browser (http://127.0.0.1:5500/web/index.html)...
start "" "http://127.0.0.1:5500/web/index.html"

echo 4. Starting Live HTTP Server on port 5500...
python -m http.server 5500
pause

