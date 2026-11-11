@echo off
title Push CPNS 2024 Dashboard ke GitHub
cd /d "D:\CPNS\Dashboard"

echo =======================================================
echo   PUSH CPNS 2024 DASHBOARD KE GITHUB
echo =======================================================
echo Target Repository: https://github.com/MBNug/cpns2024-dashboard.git
echo.
echo [INFO] Menyiapkan branch main dan remote origin...
git branch -M main
git remote remove origin >nul 2>&1
git remote add origin https://github.com/MBNug/cpns2024-dashboard.git

echo.
echo [INFO] Mengirim file ke GitHub...
echo (Jika jendela browser login GitHub muncul, silakan klik 'Authorize')
echo.
git push -u origin main

if %ERRORLEVEL% equ 0 (
    echo.
    echo =======================================================
    echo   [BERHASIL] Seluruh file sukses ter-push ke GitHub!
    echo   Buka link: https://github.com/MBNug/cpns2024-dashboard
    echo =======================================================
) else (
    echo.
    echo [ERROR] Push belum berhasil. Kode error: %ERRORLEVEL%
)

echo.
pause
