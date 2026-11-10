@echo off
title Portal CPNS 2024 Dashboard
cd /d "D:\CPNS\Dashboard"

echo =======================================================
echo   PORTAL DATA FORMASI CPNS 2024 - BKN ^& ANALYTICS
echo =======================================================
echo Workspace: D:\CPNS\Dashboard
echo.

:: 1. Check Python venv
if not exist "D:\CPNS\Dashboard\.venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment tidak ditemukan di D:\CPNS\Dashboard\.venv
    echo Silakan jalankan instalasi atau buat venv terlebih dahulu.
    echo.
    pause
    exit /b 1
)

:: 2. Free port 8000 if already occupied
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo [INFO] Menghentikan proses lama di port 8000 PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

:: 3. Open browser
echo [INFO] Membuka browser di http://localhost:8000 ...
start "" http://localhost:8000

:: 4. Start FastAPI server via Uvicorn
echo [INFO] Menjalankan server Uvicorn di http://127.0.0.1:8000 ...
echo [INFO] Tekan Ctrl+C untuk menghentikan server.
echo =======================================================
echo.
"D:\CPNS\Dashboard\.venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Server berhenti dengan kode error: %ERRORLEVEL%
    pause
)
