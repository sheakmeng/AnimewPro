@echo off
chcp 65001 >nul
title DramaBite - Auto Backup to Telegram
color 0b

echo =================================================================
echo    🎬 DRAMABITE - 1-CLICK AUTO BACKUP TO TELEGRAM
echo =================================================================
echo.
echo [*] កំពុងស្កេនថត C:\Users\sheakmeng\Desktop\DramaBite\downloads ...
echo.

python "%~dp0backup_dramabite.py"

echo.
echo =================================================================
echo [OK] ដំណើរការ Backup បានបញ្ចប់រួចរាល់!
echo =================================================================
echo.
pause
