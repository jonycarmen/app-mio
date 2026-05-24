@echo off
cd /d "C:\Users\Jonathan Rosa\OneDrive\Desktop\APP MIO"
echo ==========================================
echo  INICIANDO APP MIO - MODO PUBLICO
echo ==========================================
echo.
echo 1. Iniciando servidor...
start /B cmd /c ".venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
timeout /t 5 /nobreak >nul
echo.
echo 2. Iniciando tunel publico...
echo    (Esto creara una URL para acceder desde cualquier movil)
echo.
echo 3. Espere unos segundos...
echo.
timeout /t 10 /nobreak >nul

REM Obtener la URL del tunel
echo ==========================================
echo  URL PUBLICA DE SU APP:
echo ==========================================

REM Iniciar cloudflared y capturar URL
start /B cmd /c "cloudflared tunnel --url http://localhost:8000 --no-autoupdate > %TEMP%\cf_live.log 2>&1"
timeout /t 15 /nobreak >nul

REM Extraer URL del log
powershell -Command "Get-Content $env:TEMP\cf_live.log | Select-String -Pattern 'https://.*\.trycloudflare\.com' | Select-Object -Last 1 | ForEach-Object { Write-Host ''; Write-Host '    SU URL PUBLICA ES:' -ForegroundColor Green; Write-Host ''; Write-Host '    ' $_.Line.Split('|')[-1].Trim() -ForegroundColor Yellow; Write-Host ''; Write-Host '    Login usuarios: ' $_.Line.Split('|')[-1].Trim() '/login' -ForegroundColor Cyan; Write-Host '    Panel admin:    ' $_.Line.Split('|')[-1].Trim() '/admin/login' -ForegroundColor Cyan; Write-Host '' }"

echo ==========================================
echo Presione cualquier tecla para cerrar...
echo (El servidor se detendra)
echo ==========================================
pause >nul

REM Detener proceso
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM cloudflared.exe >nul 2>&1
