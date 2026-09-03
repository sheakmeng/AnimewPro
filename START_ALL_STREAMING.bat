@echo off
chcp 65001 > nul
title Telegram Cloud In-App Video Streamer - DramaFlixHD
color 0b

echo ==============================================================================
echo ⚡ DramaFlixHD - Telegram Cloud Video In-App Streamer (Live HTTPS)
echo ==============================================================================
echo.

cd /d "%~dp0"

echo [*] 1. កំពុងបើកដំណើរការ Telegram Stream Server (Port 8080)...
start "Telegram Stream Server" /min python tg_stream_server.py

timeout /t 3 /nobreak > nul

echo [*] 2. កំពុងបើកដំណើរការ Cloudflare Public HTTPS Tunnel...
echo [*] Video Streaming នឹងចាក់ផ្ទាល់ក្នុង Mini App ភ្លាមៗ!
echo.
echo [*] ទុកផ្ទាំងនេះចំហរដើម្បីឱ្យអ្នកទស្សនាចាក់វីដេអូបានគ្រប់ពេល។
echo.

cloudflared tunnel --url http://localhost:8080

pause
