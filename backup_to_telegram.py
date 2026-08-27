"""
Animew Pro - Automated Video Backup to Telegram Channel
Runs via GitHub Actions or Local PC
"""

import os
import sys
import json
import asyncio
import tempfile
import httpx
from pyrogram import Client
from pyrogram.types import Message

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -100999999999999
pyrogram.utils.MAX_CHANNEL_ID = -1000000000000

# Configuration
SUPABASE_URL = "https://dowjxhkijtlsdvhyuddt.supabase.co"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRvd2p4aGtpanRsc2R2aHl1ZGR0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYyMjE3MTIsImV4cCI6MjEwMTc5NzcxMn0.ulxBnNG6fc6muqPrAxzEGw0VPyZpR5ug8bY713PyWGg"

# Telegram Secrets (From Environment Variables)
API_ID = (os.getenv("TG_API_ID") or "").strip().strip('"').strip("'")
API_HASH = (os.getenv("TG_API_HASH") or "").strip().strip('"').strip("'")
BOT_TOKEN = (os.getenv("TG_BOT_TOKEN") or "").strip().strip('"').strip("'")
CHANNEL_ID = (os.getenv("TG_CHANNEL_ID") or "").strip().strip('"').strip("'")

MANIFEST_FILE = "backup_manifest.json"

def load_manifest():
    if os.path.exists(MANIFEST_FILE):
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_manifest(manifest):
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

async def fetch_shows():
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {ANON_KEY}"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{SUPABASE_URL}/rest/v1/shows?select=id,title,type,release_year", headers=headers)
        r.raise_for_status()
        return {s["id"]: s for s in r.json()}

async def fetch_episodes():
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {ANON_KEY}"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{SUPABASE_URL}/rest/v1/episodes?select=id,show_id,title,episode_number,video_url,created_at&video_url=not.is.null&order=created_at.asc&limit=1000",
            headers=headers
        )
        r.raise_for_status()
        return r.json()

async def download_file(url: str, output_path: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=30.0), follow_redirects=True) as client:
        async with client.stream("GET", url, headers=headers) as response:
            if response.status_code != 200:
                raise Exception(f"Failed to download: HTTP {response.status_code}")
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=1024 * 1024): # 1MB chunk
                    f.write(chunk)

async def main():
    if not all([API_ID, API_HASH, BOT_TOKEN, CHANNEL_ID]):
        print("⚠️ Missing Telegram environment variables. Found:")
        print(f"  TG_API_ID: {'SET' if API_ID else 'MISSING'}")
        print(f"  TG_API_HASH: {'SET' if API_HASH else 'MISSING'}")
        print(f"  TG_BOT_TOKEN: {'SET' if BOT_TOKEN else 'MISSING'}")
        print(f"  TG_CHANNEL_ID: {'SET' if CHANNEL_ID else 'MISSING'}")
        return

    try:
        api_id_int = int(API_ID)
        channel_id_int = int(CHANNEL_ID)
    except ValueError as e:
        print(f"❌ Error parsing numeric environment variables: {e}")
        return

    manifest = load_manifest()

    print("🔍 Fetching shows & episodes from database...")
    shows_map = await fetch_shows()
    episodes = await fetch_episodes()
    print(f"✅ Found {len(shows_map)} shows and {len(episodes)} available video episodes.")

    # Filter out already backed-up episodes
    pending = []
    for ep in episodes:
        ep_id = ep["id"]
        if ep_id not in manifest:
            pending.append(ep)

    print(f"📦 Total pending for backup: {len(pending)} episodes.")
    if not pending:
        print("🎉 All episodes are up to date! Nothing to backup.")
        return

    print("🤖 Connecting to Telegram Bot...", flush=True)
    app = Client(
        "backup_session",
        api_id=api_id_int,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=True,
        ipv6=False
    )
    await app.start()
    print("✅ Telegram Bot connected successfully.", flush=True)

    success_count = 0
    max_batch = 25  # Limit per run to avoid GitHub Actions timeout (runs next batch next time)

    for i, ep in enumerate(pending[:max_batch], 1):
        ep_id = ep["id"]
        show = shows_map.get(ep["show_id"], {})
        show_title = show.get("title", "Unknown Show")
        ep_num = ep.get("episode_number") or 1
        video_url = ep["video_url"]

        print(f"\n[{i}/{min(len(pending), max_batch)}] Backing up: {show_title} - Episode {ep_num}")

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            print("  ⏳ Downloading from source...")
            await download_file(video_url, temp_path)
            file_size_mb = os.path.getsize(temp_path) / (1024 * 1024)
            print(f"  📥 Download complete ({file_size_mb:.1f} MB). Uploading to Telegram...")

            caption = (
                f"🎬 **{show_title}**\n"
                f"📌 **ភាគ / Episode:** {ep_num}\n"
                f"⚡ **Quality:** 1080p FHD\n"
                f"🆔 `ep_id: {ep_id}`"
            )

            msg: Message = await app.send_video(
                chat_id=channel_id_int,
                video=temp_path,
                caption=caption,
                supports_streaming=True
            )

            # Store in manifest
            manifest[ep_id] = {
                "show_id": ep["show_id"],
                "show_title": show_title,
                "episode_number": ep_num,
                "telegram_message_id": msg.id,
                "telegram_file_id": msg.video.file_id if msg.video else None,
                "file_size_mb": round(file_size_mb, 2),
                "original_url": video_url
            }
            save_manifest(manifest)
            print(f"  ✅ Uploaded successfully (Msg ID: {msg.id})")
            success_count += 1

            # Brief pause to respect Telegram rate limits
            await asyncio.sleep(3)

        except Exception as err:
            print(f"  ❌ Error processing episode {ep_id}: {err}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    await app.stop()
    print(f"\n🎉 Backup run finished! Successfully backed up {success_count} episodes.")

if __name__ == "__main__":
    asyncio.run(main())
