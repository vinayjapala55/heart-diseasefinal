@echo off
title BMD-HS Cardiovascular Diagnostic Suite - Live Server (Port 5500)
echo =========================================================================
echo    BMD-HS Clinical Cardiothoracic Diagnostic Workstation
echo    Starting Live Server on port 5500...
echo =========================================================================
echo.
echo Opening browser to: http://127.0.0.1:5500/web/index.html
start "" "http://127.0.0.1:5500/web/index.html"
echo.
echo Live Server is active. (Press Ctrl+C to stop)
python -m http.server 5500
pause

