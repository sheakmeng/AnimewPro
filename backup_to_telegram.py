"""
Animew Pro - Automated Video Backup to Telegram Channel
Runs via GitHub Actions or Local PC
Features:
- Time-Based Auto Stop (maximizes throughput within GitHub Actions timeout)
- Auto Retry with backoff for network resilience
- FFmpeg Video Metadata & Thumbnail Extraction (duration, width, height, poster)
- Telegram Manifest generation for App Fallback
"""

import os
import sys
import json
import time
import asyncio
import logging
import tempfile
import subprocess
import shutil
import httpx

# Ensure unbuffered UTF-8 output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Mute noisy internal Pyrogram MTProto ping warnings
logging.getLogger("pyrogram.session.session").setLevel(logging.ERROR)
logging.getLogger("pyrogram.connection.connection").setLevel(logging.ERROR)

import pyrogram.utils
pyrogram.utils.MIN_CHANNEL_ID = -100999999999999
pyrogram.utils.MAX_CHANNEL_ID = -1000000000000

from pyrogram import Client
from pyrogram.types import Message

# Configuration
SUPABASE_URL = "https://dowjxhkijtlsdvhyuddt.supabase.co"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRvd2p4aGtpanRsc2R2aHl1ZGR0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYyMjE3MTIsImV4cCI6MjEwMTc5NzcxMn0.ulxBnNG6fc6muqPrAxzEGw0VPyZpR5ug8bY713PyWGg"

# Telegram Secrets (From Environment Variables or Default)
API_ID = (os.getenv("TG_API_ID") or "20360418").strip().strip('"').strip("'")
API_HASH = (os.getenv("TG_API_HASH") or "3990d0d3cc6c5bd81c93a13cd5e3a311").strip().strip('"').strip("'")
BOT_TOKEN = (os.getenv("TG_BOT_TOKEN") or "8890281595:AAGEvtsLcj_bJI1AoNQE3-BUh9-AdqzVN5g").strip().strip('"').strip("'")
CHANNEL_ID = (os.getenv("TG_CHANNEL_ID") or "-1003943277744").strip().strip('"').strip("'")

# Performance & Time Guard Configuration
# On GitHub Actions, max execution time before safe exit (default 3000s = 50 mins)
# On Local / Pydroid 3, default to continuous run (86400s = 24 hours, batch 1000)
MAX_RUN_SECONDS = int(os.getenv("MAX_RUN_SECONDS", "86400"))
MAX_BATCH = int(os.getenv("MAX_BATCH", "1000"))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
MANIFEST_FILE = os.path.join(SCRIPT_DIR, "backup_manifest.json")
GITHUB_MANIFEST_URL = "https://raw.githubusercontent.com/sheakmeng/AnimewPro/main/backup_manifest.json"

def load_manifest():
    manifest = {}
    if os.path.exists(MANIFEST_FILE):
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            manifest = {}
            
    # If local manifest is empty or missing, auto-fetch the latest from GitHub
    if not manifest:
        try:
            print("🌐 កំពុងទាញយក Backup Manifest ចុងក្រោយពី GitHub...", flush=True)
            r = httpx.get(GITHUB_MANIFEST_URL, timeout=15)
            if r.status_code == 200:
                manifest = r.json()
                save_manifest(manifest)
                print(f"✅ បានទាញយកទិន្នន័យភាគដែល Backup រួច ({len(manifest)} ភាគ) ពី GitHub ជោគជ័យ!", flush=True)
        except Exception as e:
            print(f"⚠️ មិនអាចទាញយកពី GitHub បាន: {e}", flush=True)
            
    return manifest

def save_manifest(manifest):
    try:
        with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Error saving manifest: {e}", flush=True)

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

async def download_file_with_retry(url: str, output_path: str, max_retries: int = 3):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    for attempt in range(1, max_retries + 1):
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass
                
        try:
            if attempt > 1:
                print(f"  🔄 Retry attempt {attempt}/{max_retries}...", flush=True)
                await asyncio.sleep(attempt * 2)

            async with httpx.AsyncClient(timeout=httpx.Timeout(900.0, connect=60.0), follow_redirects=True) as client:
                async with client.stream("GET", url, headers=headers) as response:
                    if response.status_code != 200:
                        raise Exception(f"HTTP {response.status_code}")
                    
                    total_downloaded = 0
                    with open(output_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=2 * 1024 * 1024): # 2MB chunk
                            f.write(chunk)
                            total_downloaded += len(chunk)
                            if total_downloaded % (15 * 1024 * 1024) < (2 * 1024 * 1024): # Log every ~15MB
                                print(f"  📥 Downloading... {total_downloaded / (1024 * 1024):.1f} MB", flush=True)
            
            # If successfully downloaded and file is not empty
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                return True
            else:
                raise Exception("Downloaded file is empty or corrupted")

        except Exception as e:
            print(f"  ⚠️ Download warning (Attempt {attempt}/{max_retries}): {e}", flush=True)
            if attempt == max_retries:
                raise e

def extract_video_metadata(video_path: str, thumb_out_path: str):
    """
    Extract video duration, width, height, and generate a thumbnail image using ffmpeg/ffprobe.
    Returns (duration_seconds, width, height, thumb_path_or_none)
    """
    duration = 0
    width = 1280
    height = 720
    thumb_created = False

    # Check if ffprobe and ffmpeg are available
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
                    duration = int(float(format_info["duration"]))
        except Exception as err:
            print(f"  ℹ️ ffprobe notice: {err}", flush=True)

    if has_ffmpeg and duration > 0:
        try:
            # Capture thumbnail at 10% of duration or at 5 seconds
            seek_pos = min(max(5, int(duration * 0.1)), 60)
            cmd = [
                "ffmpeg", "-y", "-ss", str(seek_pos),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "3",
                "-vf", "scale=640:-1",
                thumb_out_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)
            if res.returncode == 0 and os.path.exists(thumb_out_path) and os.path.getsize(thumb_out_path) > 0:
                thumb_created = True
        except Exception as err:
            print(f"  ℹ️ ffmpeg thumb notice: {err}", flush=True)

    return duration, width, height, (thumb_out_path if thumb_created else None)

def get_video_duration(video_path: str) -> float:
    """Helper to get video duration in seconds for progress tracking"""
    if not shutil.which("ffprobe"):
        return 0.0
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
        if res.returncode == 0 and res.stdout.strip():
            return float(res.stdout.strip())
    except Exception:
        pass
    return 0.0

def split_video_if_needed(video_path: str, max_mb: float = 1950.0):
    """
    If video size exceeds max_mb (default 1950MB to fit within Telegram 2GB limit),
    use FFmpeg lossless fast stream copy (-c copy) to split the video into Part 1, Part 2, etc.
    Takes only ~2-3 seconds with ZERO quality loss!
    Returns (list_of_part_paths, is_temporary_split)
    """
    import math
    if not os.path.exists(video_path):
        return [video_path], False

    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    if file_size_mb <= max_mb:
        return [video_path], False

    print(f"  ⚠️ Video size ({file_size_mb:.1f} MB) exceeds Telegram 2GB limit ({max_mb} MB)!", flush=True)

    if not shutil.which("ffmpeg"):
        print("  ❌ FFmpeg not found. Cannot split large file.", flush=True)
        return [video_path], False

    num_parts = math.ceil(file_size_mb / 1800.0)
    total_dur = get_video_duration(video_path)

    if total_dur <= 0:
        total_dur = (file_size_mb * 8 * 1024) / 4000.0

    part_dur = total_dur / num_parts
    print(f"  ⚡ Fast Lossless Split into {num_parts} parts (approx {part_dur/60:.1f} min each) in ~2s...", flush=True)

    parts = []
    for p_idx in range(num_parts):
        start_sec = p_idx * part_dur
        out_part = f"{video_path}.part{p_idx+1}.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_sec),
            "-i", video_path,
            "-t", str(part_dur),
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart",
            out_part
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            if res.returncode == 0 and os.path.exists(out_part) and os.path.getsize(out_part) > 1024:
                part_size_mb = os.path.getsize(out_part) / (1024 * 1024)
                print(f"  ✨ Part {p_idx+1}/{num_parts} created ({part_size_mb:.1f} MB)", flush=True)
                parts.append(out_part)
            else:
                print(f"  ❌ Failed creating part {p_idx+1}", flush=True)
        except Exception as e:
            print(f"  ❌ Split error on part {p_idx+1}: {e}", flush=True)

    if len(parts) == num_parts:
        return parts, True

    # If split failed for any reason, clean up and return original
    for p in parts:
        if os.path.exists(p):
            try: os.remove(p)
            except Exception: pass
    return [video_path], False

async def main():
    start_time = time.time()

    if not all([API_ID, API_HASH, BOT_TOKEN, CHANNEL_ID]):
        print("⚠️ Missing Telegram environment variables. Found:", flush=True)
        print(f"  TG_API_ID: {'SET' if API_ID else 'MISSING'}", flush=True)
        print(f"  TG_API_HASH: {'SET' if API_HASH else 'MISSING'}", flush=True)
        print(f"  TG_BOT_TOKEN: {'SET' if BOT_TOKEN else 'MISSING'}", flush=True)
        print(f"  TG_CHANNEL_ID: {'SET' if CHANNEL_ID else 'MISSING'}", flush=True)
        return

    try:
        api_id_int = int(API_ID)
        channel_id_int = int(CHANNEL_ID)
    except ValueError as e:
        print(f"❌ Error parsing numeric environment variables: {e}", flush=True)
        return

    manifest = load_manifest()

    print("🔍 Fetching shows & episodes from database...", flush=True)
    shows_map = await fetch_shows()
    episodes = await fetch_episodes()
    print(f"✅ Found {len(shows_map)} shows and {len(episodes)} available video episodes in database.", flush=True)

    # Filter out already backed-up episodes
    pending = []
    for ep in episodes:
        ep_id = str(ep["id"]).strip()
        if ep_id not in manifest:
            pending.append(ep)

    print(f"📊 ស្ថានភាពទិន្នន័យ Backup:", flush=True)
    print(f"  • បាន Backup រួចរាល់: {len(manifest)} ភាគ", flush=True)
    print(f"  • នៅសល់ត្រូវ Backup: {len(pending)} ភាគ", flush=True)
    print(f"  • ដែនកំណត់ម៉ោង (Time Limit): {MAX_RUN_SECONDS // 60} នាទី ({MAX_RUN_SECONDS}s)", flush=True)

    if not pending:
        print("🎉 គ្រប់ភាគទាំងអស់ត្រូវបាន Backup ចូល Telegram រួចរាល់អស់ហើយ! (All up to date)", flush=True)
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
    print("✅ Telegram Bot connected successfully!", flush=True)

    success_count = 0
    target_list = pending[:MAX_BATCH]

    for i, ep in enumerate(target_list, 1):
        elapsed = time.time() - start_time
        remaining_time = MAX_RUN_SECONDS - elapsed

        # Time-based stop guard: If less than 4 minutes remain, exit gracefully
        if remaining_time < 240 and i > 1:
            print(f"\n⏰ Time limit threshold reached ({elapsed/60:.1f}m elapsed). Gracefully pausing to save progress.", flush=True)
            print(f"   Next batch will seamlessly continue on the next scheduled run!", flush=True)
            break

        ep_id = ep["id"]
        show = shows_map.get(ep["show_id"], {})
        show_title = show.get("title", "Unknown Show")
        ep_num = ep.get("episode_number") or 1
        video_url = ep["video_url"]

        print(f"\n[{i}/{len(target_list)}] 🚀 Starting: {show_title} - Episode {ep_num} ({elapsed/60:.1f}m running)", flush=True)
        print(f"  🔗 URL: {video_url}", flush=True)

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video_file:
            temp_path = temp_video_file.name
        
        thumb_path = temp_path + ".thumb.jpg"
        video_parts = [temp_path]
        is_split = False

        try:
            print("  ⏳ Downloading from source with auto-retry...", flush=True)
            await download_file_with_retry(video_url, temp_path, max_retries=3)
            raw_file_size_mb = os.path.getsize(temp_path) / (1024 * 1024)
            print(f"  ✅ Download complete ({raw_file_size_mb:.1f} MB). Analyzing size & metadata...", flush=True)

            # Fast lossless split if file exceeds 1950MB
            video_parts, is_split = split_video_if_needed(temp_path, max_mb=1950.0)
            total_parts = len(video_parts)

            uploaded_msg_ids = []
            primary_file_id = None
            primary_msg_id = None
            total_uploaded_size_mb = 0

            for part_idx, part_file in enumerate(video_parts, 1):
                part_size_mb = os.path.getsize(part_file) / (1024 * 1024)
                total_uploaded_size_mb += part_size_mb

                if part_size_mb > 1999.0:
                    print(f"  ⛔ Skipping part {part_idx}: File size ({part_size_mb:.1f} MB) exceeds Telegram 2GB limit.", flush=True)
                    continue

                part_thumb = part_file + ".thumb.jpg"
                duration, width, height, thumb_file = extract_video_metadata(part_file, part_thumb)
                if duration > 0:
                    print(f"  🎬 Part {part_idx} Metadata: Duration {duration//60}m{duration%60}s | {width}x{height} | Thumb: {'Yes' if thumb_file else 'No'}", flush=True)

                part_suffix = f" (Part {part_idx}/{total_parts})" if total_parts > 1 else ""
                caption = (
                    f"🎬 **{show_title}**\n"
                    f"📌 **ភាគ / Episode:** {ep_num}{part_suffix}\n"
                    f"⚡ **Quality:** 1080p FHD\n"
                    f"📦 **Size:** {part_size_mb:.1f} MB\n"
                    f"🆔 `ep_id: {ep_id}`"
                )

                last_logged_pct = -1
                def progress(current, total):
                    nonlocal last_logged_pct
                    pct = int((current / total) * 100)
                    if pct % 20 == 0 and pct != last_logged_pct:
                        last_logged_pct = pct
                        part_tag = f"[Part {part_idx}/{total_parts}] " if total_parts > 1 else ""
                        print(f"  📤 {part_tag}Uploading: {pct}% ({current / (1024*1024):.1f} MB / {total / (1024*1024):.1f} MB)", flush=True)

                msg: Message = await app.send_video(
                    chat_id=channel_id_int,
                    video=part_file,
                    caption=caption,
                    duration=duration if duration > 0 else None,
                    width=width if duration > 0 else None,
                    height=height if duration > 0 else None,
                    thumb=thumb_file,
                    supports_streaming=True,
                    progress=progress
                )

                uploaded_msg_ids.append(msg.id)
                if not primary_msg_id:
                    primary_msg_id = msg.id
                    primary_file_id = msg.video.file_id if msg.video else None

                print(f"  🎉 Uploaded Part {part_idx}/{total_parts} successfully! (Telegram Message ID: {msg.id})", flush=True)

                if os.path.exists(part_thumb):
                    try: os.remove(part_thumb)
                    except Exception: pass

                # Brief pause between parts
                await asyncio.sleep(2)

            if primary_msg_id:
                # Store in manifest
                manifest[ep_id] = {
                    "show_id": ep["show_id"],
                    "show_title": show_title,
                    "episode_number": ep_num,
                    "telegram_message_id": primary_msg_id,
                    "telegram_file_id": primary_file_id,
                    "telegram_message_ids": uploaded_msg_ids,
                    "total_parts": total_parts,
                    "file_size_mb": round(total_uploaded_size_mb, 2),
                    "original_url": video_url,
                    "backed_up_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
                save_manifest(manifest)
                success_count += 1

        except Exception as err:
            print(f"  ❌ Error processing episode {ep_id}: {err}", flush=True)
        finally:
            if os.path.exists(temp_path):
                try: os.remove(temp_path)
                except Exception: pass
            if is_split:
                for p in video_parts:
                    if os.path.exists(p):
                        try: os.remove(p)
                        except Exception: pass
            if os.path.exists(thumb_path):
                try: os.remove(thumb_path)
                except Exception: pass

    # Optional final Telegram channel summary message
    if success_count > 0:
        try:
            total_backed = len(manifest)
            total_size_mb = sum(m.get("file_size_mb", 0) for m in manifest.values())
            summary_text = (
                f"📊 **Auto Backup Report**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"✅ **ទើប Backup ថ្មី:** +{success_count} ភាគ\n"
                f"📁 **សរុបទាំងអស់ក្នុង Archive:** {total_backed} ភាគ\n"
                f"💾 **ទំហំសរុប (Total Size):** {total_size_mb / 1024:.2f} GB\n"
                f"⏱️ **រយៈពេលរត់:** {(time.time() - start_time)/60:.1f} នាទី\n"
                f"🚀 **ស្ថានភាព:** ជោគជ័យ (Completed)"
            )
            await app.send_message(chat_id=channel_id_int, text=summary_text)
            print("📢 Sent summary report to Telegram channel.", flush=True)
        except Exception as e:
            print(f"ℹ️ Could not send summary notification: {e}", flush=True)

    await app.stop()
    print(f"\n🏁 Backup run finished! Successfully backed up {success_count} episodes in {(time.time() - start_time)/60:.1f} minutes.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())

