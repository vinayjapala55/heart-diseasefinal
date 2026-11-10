@echo off
title BMD-HS Heart Disease Diagnostic Suite - Live Server
echo =====================================================================
echo    BMD-HS Clinical Cardiothoracic Diagnostic Workstation
echo    RosaNet 8-Branch Multi-Agent Cardiovascular AI
echo =====================================================================
echo.
echo Starting FastAPI AI Backend and opening Live UI...
echo Server URL: http://127.0.0.1:8000
echo.
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8000"
python app.py
pause

