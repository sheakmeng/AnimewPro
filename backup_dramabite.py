#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 DramaBite -> Telegram Auto Backup Tool
Automatically scans C:\\Users\\sheakmeng\\Desktop\\DramaBite\\downloads,
extracts video metadata & thumbnails, uploads to Telegram Channel,
updates backup_manifest.json, and syncs live to Google Sheets!
"""

import os
import sys
import json
import time
import math
import re
import asyncio
import logging
import subprocess
import shutil

# Ensure UTF-8 stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Mute noisy internal Pyrogram MTProto logs
logging.getLogger("pyrogram.session.session").setLevel(logging.ERROR)
logging.getLogger("pyrogram.connection.connection").setLevel(logging.ERROR)

import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -100999999999999
pyrogram.utils.MAX_CHANNEL_ID = -1000000000000

from pyrogram import Client
import httpx

# Paths & Directories
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
DRAMABITE_DIR = r"C:\Users\sheakmeng\Desktop\DramaBite"
DRAMABITE_DOWNLOADS = os.path.join(DRAMABITE_DIR, "downloads")
DRAMABITE_FFMPEG = os.path.join(DRAMABITE_DIR, "ffmpeg")

# Add bundled FFmpeg to PATH
if os.path.isdir(DRAMABITE_FFMPEG) and DRAMABITE_FFMPEG not in os.environ.get("PATH", ""):
    os.environ["PATH"] = DRAMABITE_FFMPEG + os.pathsep + os.environ.get("PATH", "")

# Auto-load .env
def _load_env_file():
    candidates = [
        os.path.join(SCRIPT_DIR, ".env"),
        os.path.join(DRAMABITE_DIR, ".env"),
        r"c:\Users\sheakmeng\Desktop\New folder\.env"
    ]
    for env_file in candidates:
        if os.path.isfile(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass
            break

_load_env_file()

API_ID = os.getenv("TG_API_ID", "").strip().strip('"').strip("'")
API_HASH = os.getenv("TG_API_HASH", "").strip().strip('"').strip("'")
BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip().strip('"').strip("'")
CHANNEL_ID = os.getenv("TG_CHANNEL_ID", "").strip().strip('"').strip("'")
GOOGLE_APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyeNw3vClMRYMWssYT-gTncSntQUvVvHb43QcDYR5k4RXLrFPDzS5vEh5PZyWM95XXmSg/exec"

MANIFEST_FILE = os.path.join(SCRIPT_DIR, "backup_manifest.json")

def load_manifest() -> dict:
    if os.path.isfile(MANIFEST_FILE):
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_manifest(manifest: dict):
    # 1. Save backup_manifest.json locally and in www
    for p in [MANIFEST_FILE, os.path.join(SCRIPT_DIR, "www", "backup_manifest.json")]:
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # 2. Update data.js and www/data.js
    for js_p in [os.path.join(SCRIPT_DIR, "data.js"), os.path.join(SCRIPT_DIR, "www", "data.js")]:
        try:
            os.makedirs(os.path.dirname(js_p), exist_ok=True)
            with open(js_p, "w", encoding="utf-8") as f:
                f.write("window.INITIAL_MANIFEST = " + json.dumps(manifest, ensure_ascii=False, indent=2) + ";\n")
        except Exception:
            pass

async def sync_to_google_sheet(ep_id: str, ep_data: dict):
    """Sync backed up episode to Google Sheets in real-time."""
    if not GOOGLE_APPS_SCRIPT_URL or not GOOGLE_APPS_SCRIPT_URL.startswith("http"):
        return
    try:
        payload = {"ep_id": ep_id, "data": ep_data}
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            r = await client.post(GOOGLE_APPS_SCRIPT_URL, json=payload)
            if r.status_code == 200:
                print(f"  📊 Live Synced to Google Sheet: {ep_data.get('show_title')} EP {ep_data.get('episode_number')}", flush=True)
    except Exception as e:
        print(f"  ⚠️ Google Sheet sync notice: {e}", flush=True)

def extract_video_metadata(video_path: str, thumb_out_path: str):
    duration = 0
    width = 1280
    height = 720
    thumb_created = False

    has_ffprobe = shutil.which("ffprobe") is not None
    has_ffmpeg = shutil.which("ffmpeg") is not None

    if has_ffprobe:
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,duration:format=duration",
                "-of", "json",
                video_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                streams = data.get("streams", [])
                format_info = data.get("format", {})
                if streams:
                    width = int(streams[0].get("width", 1280))
                    height = int(streams[0].get("height", 720))
                    dur_str = streams[0].get("duration") or format_info.get("duration")
                    if dur_str:
                        duration = int(float(dur_str))
                elif format_info.get("duration"):
                    duration = int(float(format_info.get("duration")))
        except Exception:
            pass

    if has_ffmpeg and duration > 0:
        try:
            target_sec = max(1, duration // 3)
            cmd = [
                "ffmpeg", "-y", "-ss", str(target_sec),
                "-i", video_path, "-vframes", "1",
                "-vf", "scale='min(640,iw)':-2",
                "-q:v", "2", thumb_out_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
            if res.returncode == 0 and os.path.exists(thumb_out_path) and os.path.getsize(thumb_out_path) > 0:
                thumb_created = True
        except Exception:
            pass

    return duration, width, height, (thumb_out_path if thumb_created else None)

def fetch_dramabite_posters_map():
    """Fetches all drama titles and their poster covers from DramaBite API."""
    posters_cache = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.dramabite.media",
        "Referer": "https://www.dramabite.media/"
    }
    for page in range(10):
        try:
            url = f"https://www.dramabite.media/short_video/video_svr/homepage?page={page}"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                break
            data = r.json()
            modules = data.get("module_list") or []
            if not modules:
                break
            for mod in modules:
                for v in mod.get("video_list") or []:
                    title = v.get("title")
                    cover = v.get("cover_url") or v.get("video_cover")
                    if title and cover:
                        clean_cover = cover.lstrip("/")
                        full_img = f"https://cdn-oss.miniepisode.media/{clean_cover}"
                        norm_title = re.sub(r'[^a-zA-Z0-9]', '', title).lower()
                        posters_cache[norm_title] = full_img
        except Exception:
            break
    return posters_cache

def scan_dramabite_downloads(target_dir=None):
    """Recursively scan DramaBite directory for video episodes."""
    downloads_dir = target_dir or DRAMABITE_DOWNLOADS
    if not os.path.isdir(downloads_dir):
        print(f"⚠️ ថត DramaBite មិនទាន់មាននៅ: {downloads_dir}")
        return []

    print("🖼️ កំពុងទាញយក Poster ផ្លូវការពីរឿងទាំងអស់លើ DramaBite API...", flush=True)
    posters_cache = fetch_dramabite_posters_map()

    video_exts = {".mp4", ".mkv", ".ts", ".mov", ".m4v"}
    image_exts = {".jpg", ".jpeg", ".png", ".webp"}
    found = []

    for root, dirs, files in os.walk(downloads_dir):
        # Look for cover image in current show folder
        folder_poster = ""
        for f in files:
            if os.path.splitext(f)[1].lower() in image_exts:
                folder_poster = os.path.join(root, f)
                break

        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in video_exts or f.lower().startswith("test_") or f.lower().endswith(".part"):
                continue

            full_path = os.path.join(root, f)
            folder_name = os.path.basename(root)

            # Show Title
            if folder_name.lower() != "downloads":
                show_title = folder_name
            else:
                base_name = os.path.splitext(f)[0]
                show_title = re.sub(r'_(?:EP|Episode|_)?\d+.*$', '', base_name, flags=re.IGNORECASE).strip() or base_name

            # Match Official Poster
            norm_show = re.sub(r'[^a-zA-Z0-9]', '', show_title).lower()
            resolved_poster = posters_cache.get(norm_show, "")
            if not resolved_poster:
                for k, v in posters_cache.items():
                    if norm_show in k or k in norm_show:
                        resolved_poster = v
                        break
            if not resolved_poster and folder_poster:
                resolved_poster = folder_poster

            # Episode Number
            m = re.search(r'(?:EP|Episode|[_-])\s*(\d+)', f, re.IGNORECASE)
            if not m:
                m = re.search(r'(\d+)', f)
            ep_num = int(m.group(1)) if m else 1

            # Safe Slugs
            clean_slug = re.sub(r'[^a-zA-Z0-9]+', '_', show_title).strip('_').lower()
            show_id = f"dramabite_{clean_slug}"
            ep_id = f"dramabite_{clean_slug}_{ep_num}"

            found.append({
                "id": ep_id,
                "show_id": show_id,
                "show_title": show_title,
                "episode_number": ep_num,
                "local_file_path": full_path,
                "file_size_mb": round(os.path.getsize(full_path) / (1024 * 1024), 2),
                "poster_url": resolved_poster,
                "synopsis": f"រឿងភាគ {show_title} កម្រិតច្បាស់ HD ទាញយកតាមរយៈ DramaBite",
                "source": "dramabite"
            })

    return found

async def backup_dramabite_episode(app: Client, ep: dict, manifest: dict, channel_id_int: int) -> bool:
    ep_id = ep["id"]
    show_title = ep["show_title"]
    ep_num = ep["episode_number"]
    file_path = ep["local_file_path"]
    part_size_mb = ep["file_size_mb"]
    poster_path = ep.get("poster_url")

    thumb_temp = file_path + ".thumb.jpg"
    duration, width, height, thumb_file = extract_video_metadata(file_path, thumb_temp)

    # Use folder poster image as thumbnail if ffmpeg frame was not generated
    if not thumb_file and poster_path and os.path.isfile(poster_path):
        thumb_file = poster_path

    caption = (
        f"🎬 **{show_title}**\n"
        f"📌 **ភាគ / Episode:** {ep_num}\n"
        f"⚡ **Source:** DramaBite HD (Local Upload)\n"
        f"📦 **Size:** {part_size_mb:.1f} MB\n"
        f"🆔 `ep_id: {ep_id}`"
    )

    last_logged_pct = -1
    start_t = time.time()

    def progress(current, total):
        nonlocal last_logged_pct
        pct = int((current / total) * 100) if total > 0 else 0
        if pct != last_logged_pct and pct % 20 == 0:
            last_logged_pct = pct
            speed_mb = (current / (1024 * 1024)) / max(0.1, time.time() - start_t)
            print(f"    ⏳ Uploading: {pct}% ({current / (1024*1024):.1f}/{total / (1024*1024):.1f} MB) • {speed_mb:.1f} MB/s", flush=True)

    try:
        msg = await app.send_video(
            chat_id=channel_id_int,
            video=file_path,
            caption=caption,
            duration=int(duration or 0),
            width=int(width or 0),
            height=int(height or 0),
            thumb=thumb_file if (thumb_file and os.path.isfile(thumb_file) and os.path.getsize(thumb_file) > 0) else None,
            supports_streaming=True,
            progress=progress
        )

        primary_msg_id = msg.id
        primary_file_id = msg.video.file_id if msg.video else None

        print(f"  🎉 Upload ជោគជ័យ! (Telegram Message ID: {primary_msg_id})", flush=True)

        manifest[ep_id] = {
            "show_id": ep["show_id"],
            "show_title": show_title,
            "episode_number": ep_num,
            "telegram_message_id": primary_msg_id,
            "telegram_file_id": primary_file_id,
            "telegram_message_ids": [primary_msg_id],
            "total_parts": 1,
            "file_size_mb": part_size_mb,
            "original_url": file_path,
            "poster_url": ep.get("poster_url") or "",
            "synopsis": ep.get("synopsis", ""),
            "source": "dramabite",
            "backed_up_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

        save_manifest(manifest)
        await sync_to_google_sheet(ep_id, manifest[ep_id])
        return True

    except Exception as err:
        print(f"  ❌ Error uploading {ep_id}: {err}", flush=True)
        return False
    finally:
        if os.path.exists(thumb_temp):
            try: os.remove(thumb_temp)
            except Exception: pass

async def main():
    print("=" * 65, flush=True)
    print("   🎬 DRAMABITE -> TELEGRAM AUTO BACKUP ENGINE", flush=True)
    print(f"   📁 Scanning: {DRAMABITE_DOWNLOADS}", flush=True)
    print("=" * 65, flush=True)

    if not all([API_ID, API_HASH, BOT_TOKEN, CHANNEL_ID]):
        print("❌ Missing Telegram credentials in .env file.", flush=True)
        return

    try:
        api_id_int = int(API_ID)
        channel_id_int = int(CHANNEL_ID)
    except ValueError as e:
        print(f"❌ Error parsing numeric IDs: {e}", flush=True)
        return

    manifest = load_manifest()
    custom_dir = sys.argv[1].strip() if (len(sys.argv) > 1 and not sys.argv[1].startswith("-")) else None
    
    all_dramabite_eps = scan_dramabite_downloads(custom_dir)
    if not all_dramabite_eps:
        print(f"⚠️ មិនទាន់មានវីដេអូទាញយកក្នុងថត DramaBite ឡើយ។", flush=True)
        return

    # Zero-duplicate check
    pending = [ep for ep in all_dramabite_eps if ep["id"] not in manifest]

    print(f"📊 ស្ថានភាពទិន្នន័យ:", flush=True)
    print(f"  • រកឃើញក្នុង DramaBite: {len(all_dramabite_eps)} ភាគ", flush=True)
    print(f"  • បាន Backup រួចរាល់: {len(all_dramabite_eps) - len(pending)} ភាគ", flush=True)
    print(f"  • នៅសល់ត្រូវ Backup ឡើង Telegram: {len(pending)} ភាគ", flush=True)
    print("-" * 65, flush=True)

    if not pending:
        print("🎉 គ្រប់វីដេអូទាំងអស់ពី DramaBite ត្រូវបាន Backup ចូល Telegram រួចរាល់អស់ហើយ! (All up to date)", flush=True)
        return

    print("\n🤖 កំពុងតភ្ជាប់ទៅកាន់ Telegram Bot (Backup Anime)...", flush=True)
    session_file = os.path.join(r"c:\Users\sheakmeng\Desktop\New folder", "backup_session")
    app = Client(
        session_file,
        api_id=api_id_int,
        api_hash=API_HASH
    )
    await app.start()
    print("✅ Telegram Bot connected successfully to channel!", flush=True)

    success_count = 0
    start_t = time.time()

    for idx, ep in enumerate(pending, 1):
        print(f"\n[{idx}/{len(pending)}] 🚀 Uploading: {ep['show_title']} (EP {ep['episode_number']}) - {ep['file_size_mb']} MB", flush=True)
        ok = await backup_dramabite_episode(app, ep, manifest, channel_id_int)
        if ok:
            success_count += 1
        await asyncio.sleep(1)

    # Summary notification
    if success_count > 0:
        try:
            summary = (
                f"🎬 **DramaBite Local Backup Complete**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"✅ **ទើប Backup ថ្មី:** +{success_count} ភាគ\n"
                f"📁 **សរុបទាំងអស់ក្នុង Archive:** {len(manifest)} ភាគ\n"
                f"⏱️ **រយៈពេល:** {(time.time() - start_t)/60:.1f} នាទី\n"
                f"🚀 **ស្ថានភាព:** ជោគជ័យ (Completed)"
            )
            await app.send_message(chat_id=channel_id_int, text=summary)
            print("📢 បានផ្ញើសេចក្តីជូនដំណឹងចូល Telegram Channel រួចរាល់!", flush=True)
        except Exception:
            pass

    await app.stop()
    print(f"\n🏁 បញ្ចប់ការ Backup! បាន Upload {success_count}/{len(pending)} ភាគជោគជ័យក្នុងរយៈពេល {(time.time() - start_t)/60:.1f} នាទី។", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
