@echo off
chcp 65001 > nul
title Telegram Cloud Video Streaming Server - DramaFlixHD
color 0b

echo ==============================================================================
echo [DramaFlixHD] Telegram Cloud Video Streaming Server
echo ==============================================================================
echo.

cd /d "%~dp0"

echo [*] Launching Telegram Stream Server on Port 8080...
echo [*] Press Ctrl + C to stop at any time.
echo.

python tg_stream_server.py

pause
