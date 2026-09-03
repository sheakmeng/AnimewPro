#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚡ Telegram Cloud Video Streaming Server (Animew Pro & DramaFlixHD)
High-performance HTTP 206 Partial Content Streamer for Telegram Cloud Videos.

Connects HTML5 <video> in Web Browser / Telegram Mini App directly to Telegram MTProto,
enabling fast 1080p FHD video playback with instant seeking directly from backed-up Telegram messages!
"""

import os
import sys
import math
import logging
import asyncio
from typing import Optional

# Ensure UTF-8 console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("tg_stream_server")

# Auto-load .env
def _load_env_file():
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.isfile(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

_load_env_file()

# Telegram Pyrogram Setup with 64-bit Channel ID support
import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -100999999999999
pyrogram.utils.MAX_CHANNEL_ID = -1000000000000

from pyrogram import Client
from pyrogram.types import Message
from aiohttp import web

# Environment variables
API_ID = int(os.getenv("TG_API_ID", "20360418"))
API_HASH = os.getenv("TG_API_HASH", "3990d0d3cc6c5bd81c93a13cd5e3a311").strip().strip('"').strip("'")
BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip().strip('"').strip("'")
DEFAULT_CHANNEL_ID = int(os.getenv("TG_CHANNEL_ID", "-1003943277744"))
SERVER_PORT = int(os.getenv("STREAM_PORT", os.getenv("PORT", "8080")))

# In-memory cache for Telegram message metadata
message_cache = {}

# Pyrogram Client
app = Client(
    "tg_stream_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# CORS middleware for seamless Web & Telegram Mini App embedding
@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        response = web.Response()
    else:
        try:
            response = await handler(request)
        except web.HTTPException as ex:
            response = ex

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Range, Origin, Content-Type, Accept"
    response.headers["Access-Control-Expose-Headers"] = "Content-Range, Content-Length, Accept-Ranges, Content-Type"
    return response


async def handle_home(request: web.Request) -> web.Response:
    """Server status & healthcheck endpoint."""
    bot_info = None
    try:
        me = await app.get_me()
        bot_info = {"id": me.id, "username": me.username, "first_name": me.first_name}
    except Exception as e:
        bot_info = {"error": str(e)}

    channel_status = "unknown"
    try:
        chat = await app.get_chat(DEFAULT_CHANNEL_ID)
        channel_status = f"Connected: {chat.title} ({chat.id})"
    except Exception as e:
        channel_status = f"Error: {e} (Please ensure bot is Admin in channel {DEFAULT_CHANNEL_ID})"

    return web.json_response({
        "service": "DramaFlixHD Telegram Video Stream Server",
        "status": "online",
        "bot": bot_info,
        "default_channel": DEFAULT_CHANNEL_ID,
        "channel_status": channel_status,
        "stream_endpoint": "/stream/{message_id}"
    })


async def get_cached_message(channel_id: int, message_id: int) -> Optional[Message]:
    """Retrieves a message from cache or fetches from Telegram with caching."""
    cache_key = f"{channel_id}_{message_id}"
    if cache_key in message_cache:
        return message_cache[cache_key]

    try:
        msg = await app.get_messages(channel_id, message_id)
        if msg and (msg.video or msg.document or msg.animation):
            message_cache[cache_key] = msg
            return msg
    except Exception as e:
        logger.error(f"Error fetching message {message_id} from {channel_id}: {e}")
    return None


async def handle_stream(request: web.Request) -> web.StreamResponse:
    """
    Streams a video from Telegram Cloud by message_id.
    Supports HTTP 206 Partial Content (Range requests) for fast seeking in HTML5 <video>.
    """
    try:
        message_id = int(request.match_info["message_id"])
    except (ValueError, KeyError):
        return web.HTTPBadRequest(text="Invalid message_id")

    channel_param = request.match_info.get("channel_id")
    channel_id = int(channel_param) if channel_param else DEFAULT_CHANNEL_ID

    msg = await get_cached_message(channel_id, message_id)
    if not msg:
        return web.HTTPNotFound(text=f"Video message {message_id} not found in channel {channel_id}")

    media = msg.video or msg.document or msg.animation
    if not media:
        return web.HTTPNotFound(text="Message does not contain a streamable video file")

    file_size = media.file_size
    mime_type = media.mime_type or "video/mp4"
    file_name = getattr(media, "file_name", f"video_{message_id}.mp4")

    range_header = request.headers.get("Range")

    if range_header:
        # Parse 'bytes=start-end'
        try:
            range_val = range_header.strip().lower().replace("bytes=", "")
            parts = range_val.split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
            if end >= file_size:
                end = file_size - 1
            if start > end or start >= file_size:
                return web.HTTPRequestedRangeNotSatisfiable(headers={"Content-Range": f"bytes */{file_size}"})
        except Exception:
            start = 0
            end = file_size - 1

        content_length = end - start + 1
        status_code = 206
        response_headers = {
            "Content-Type": mime_type,
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(content_length),
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'inline; filename="{file_name}"'
        }
    else:
        start = 0
        end = file_size - 1
        content_length = file_size
        status_code = 200
        response_headers = {
            "Content-Type": mime_type,
            "Content-Length": str(content_length),
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'inline; filename="{file_name}"'
        }

    # Head request only returns headers
    if request.method == "HEAD":
        return web.Response(status=status_code, headers=response_headers)

    response = web.StreamResponse(status=status_code, headers=response_headers)
    await response.prepare(request)

    # Calculate Pyrogram 1MB chunks (1024 * 1024)
    CHUNK_SIZE = 1024 * 1024
    offset_chunk = start // CHUNK_SIZE
    skip_initial_bytes = start % CHUNK_SIZE
    total_to_send = content_length
    bytes_sent = 0

    try:
        async for chunk in app.stream_media(msg, offset=offset_chunk):
            if skip_initial_bytes > 0:
                chunk = chunk[skip_initial_bytes:]
                skip_initial_bytes = 0

            if bytes_sent + len(chunk) > total_to_send:
                chunk = chunk[: total_to_send - bytes_sent]

            if chunk:
                await response.write(chunk)
                bytes_sent += len(chunk)

            if bytes_sent >= total_to_send:
                break
    except (asyncio.CancelledError, ConnectionResetError):
        # Client closed video tab or sought to another point
        pass
    except Exception as e:
        logger.warning(f"Stream error for msg {message_id}: {e}")

    await response.write_eof()
    return response


async def start_server():
    """Initializes Pyrogram and starts aiohttp web server."""
    logger.info("Connecting Telegram Client...")
    await app.start()
    me = await app.get_me()
    logger.info(f"✅ Bot connected: @{me.username} (ID: {me.id})")

    try:
        chat = await app.get_chat(DEFAULT_CHANNEL_ID)
        logger.info(f"✅ Channel connected: '{chat.title}' (ID: {chat.id})")
    except Exception as e:
        logger.warning(f"⚠️ Channel connection notice: {e}")
        logger.warning(f"👉 Please make sure @{me.username} is added as Administrator in channel {DEFAULT_CHANNEL_ID}")

    server_app = web.Application(middlewares=[cors_middleware])
    server_app.router.add_get("/", handle_home)
    server_app.router.add_get("/status", handle_home)
    server_app.router.add_get("/stream/{message_id}", handle_stream)
    server_app.router.add_get("/stream/{channel_id}/{message_id}", handle_stream)

    runner = web.AppRunner(server_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", SERVER_PORT)
    await site.start()
    logger.info(f"🚀 Telegram Stream Server running at: http://localhost:{SERVER_PORT}")
    logger.info(f"🎬 Test stream URL format: http://localhost:{SERVER_PORT}/stream/<telegram_message_id>")

    # Keep running
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stream server stopped.")
