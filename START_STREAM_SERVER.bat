@echo off
chcp 65001 > nul
title Telegram Cloud Video Streaming Server - DramaFlixHD
color 0b

echo ==============================================================================
echo ⚡ DramaFlixHD - Telegram Cloud Video Streaming Server
echo ==============================================================================
echo.

cd /d "%~dp0"

echo [*] កំពុងពិនិត្យ Python និង Dependencies...
python -c "import pyrogram, aiohttp" 2>nul
if %errorlevel% neq 0 (
    echo [*] Installing required packages: aiohttp, pyrogram, tgcrypto...
    pip install aiohttp pyrogram tgcrypto httpx
)

echo.
echo [*] កំពុងដំណើរការ Stream Server នៅលើ Port 8080...
echo [*] អ្នកអាចបិទផ្ទាំងនេះបានគ្រប់ពេលដោយចុច Ctrl + C
echo.

python tg_stream_server.py

pause
