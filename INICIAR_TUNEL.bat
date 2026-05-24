@echo off
chcp 65001 >nul
color 0A
title APP MIO - Acceso Publico

echo ================================================
echo    APP MIO - INICIAR ACCESO PUBLICO
echo ================================================
echo.
echo [1] Iniciando servidor local...

cd /d "C:\Users\Jonathan Rosa\OneDrive\Desktop\APP MIO"
start /B cmd /c ".venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1"

timeout /t 4 /nobreak >nul

echo [2] Servidor listo
echo.
echo [3] Creando tunel publico...
echo     Espera 15-20 segundos...
echo.

cloudflared tunnel --url http://localhost:8000 --no-autoupdate 2> tunnel.log

REM El comando anterior bloquea la terminal y muestra la URL
REM cuando veas la URL en pantalla, copiala y compartela

echo.
echo ================================================
echo    Servidor detenido
echo ================================================
pause
