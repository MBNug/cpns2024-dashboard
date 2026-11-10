@echo off
title Stop CPNS 2024 Dashboard
cd /d "D:\CPNS\Dashboard"

echo =======================================================
echo   STOPPING CPNS 2024 DASHBOARD SERVER
echo =======================================================

set FOUND=0
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo [INFO] Terminating server process PID %%a on port 8000...
    taskkill /F /PID %%a >nul 2>&1
    set FOUND=1
)

if "%FOUND%"=="1" (
    echo [SUCCESS] CPNS 2024 Dashboard server stopped successfully.
) else (
    echo [INFO] No active server found listening on port 8000.
)

ping -n 3 127.0.0.1 >nul 2>&1
