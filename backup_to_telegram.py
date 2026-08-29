"""
Animew Pro & Dramaora - 1-Click Automated Video Backup to Telegram Channel
Optimized for: Pydroid 3 (Android Mobile), Local PC, & GitHub Actions

Behavior:
- Simply RUN the script -> Immediately scans, unlocks 100% VIP episodes, and backs up ALL dramas from Dramaora.tv to Telegram!
- Zero user intervention required (No blocking input prompts).
- Zero-crash fallback when FFmpeg is not installed (perfect for mobile Pydroid 3).
- Instant cleanup of temporary files after each upload (prevents filling Android storage).
- Deduplication via backup_manifest.json (skips already backed up episodes).
"""

import os
import sys
import json
import time
import math
import hashlib
import random
import asyncio
import logging
import tempfile
import subprocess
import shutil
from urllib.parse import urlparse, parse_qs

import httpx

# Ensure unbuffered UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Mute noisy internal Pyrogram MTProto ping warnings
logging.getLogger("pyrogram.session.session").setLevel(logging.ERROR)
logging.getLogger("pyrogram.connection.connection").setLevel(logging.ERROR)

import pyrogram.utils
# Fix Pyrogram 64-bit Channel ID support
pyrogram.utils.MIN_CHANNEL_ID = -100999999999999
pyrogram.utils.MAX_CHANNEL_ID = -1000000000000

from pyrogram import Client
from pyrogram.types import Message

# ==============================================================================
# CONFIGURATION & SECRETS
# ==============================================================================

# Telegram Secrets (From Environment Variables or Default)
API_ID = (os.getenv("TG_API_ID") or "20360418").strip().strip('"').strip("'")
API_HASH = (os.getenv("TG_API_HASH") or "3990d0d3cc6c5bd81c93a13cd5e3a311").strip().strip('"').strip("'")
BOT_TOKEN = (os.getenv("TG_BOT_TOKEN") or "8890281595:AAGEvtsLcj_bJI1AoNQE3-BUh9-AdqzVN5g").strip().strip('"').strip("'")
CHANNEL_ID = (os.getenv("TG_CHANNEL_ID") or "-1003943277744").strip().strip('"').strip("'")

# Performance & Unlimited Run Configuration (No Time Limit / មិនកំណត់នាទី)
MAX_RUN_SECONDS = int(os.getenv("MAX_RUN_SECONDS", "0"))  # 0 = Unlimited (រត់រហូតដល់ចប់គ្រប់ភាគទាំងអស់)
MAX_BATCH = int(os.getenv("MAX_BATCH", "999999"))         # Unlimited batch size

# Dramaora Protocol Constants
DRAMAORA_PID = 1329
DRAMAORA_KEY = "73a74wxa58179eef93"
DRAMAORA_VERSION = 20251120
DRAMAORA_DEFAULT_TICKET = "1787000521gAuJs0mo3c"

# Known Popular & High-Quality Dramaora Series to Crawl
KNOWN_DRAMA_IDS = [
    "52025667797",  # The Wrong Love
    "52023960492",  # Fallen Desire
    "52027768287",  # Cursed by Desire
    "52024881903",  # Revenge & Love
    "52025912841",  # Destined Bond
    "52026819204",  # CEO's Secret Bride
    "52028109238",  # Temptation of the Alpha
    "52029381720",  # Hidden Identity
    "52025571614",  # Milk Service
    "52024257303",  # Bound by Blood
]

# Paths & Manifest Locations (Auto-detected across PC & Android Pydroid 3)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
MANIFEST_FILE = os.path.join(SCRIPT_DIR, "backup_manifest.json")
GITHUB_MANIFEST_URL = "https://raw.githubusercontent.com/sheakmeng/AnimewPro/main/backup_manifest.json"

# 📊 Google Apps Script Web App URL (Realtime Google Sheet & APK Cloud Sync)
GOOGLE_APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyeNw3vClMRYMWssYT-gTncSntQUvVvHb43QcDYR5k4RXLrFPDzS5vEh5PZyWM95XXmSg/exec" 

MANIFEST_CANDIDATE_PATHS = [
    MANIFEST_FILE,
    os.path.join(os.getcwd(), "backup_manifest.json"),
    "/sdcard/Download/backup_manifest.json",
    "/storage/emulated/0/Download/backup_manifest.json",
    "/sdcard/backup_manifest.json"
]

async def sync_to_google_sheet(ep_id: str, ep_data: dict):
    """Sync backed up episode directly to Google Sheets Web App in real-time."""
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

# ==============================================================================
# MANIFEST MANAGEMENT & ZERO-DUPLICATION ENGINE
# ==============================================================================

def is_already_backed_up(ep: dict, manifest: dict) -> bool:
    """Check if an episode has already been uploaded to Telegram."""
    if not manifest:
        return False

    ep_id = str(ep.get("id") or "").strip()
    if ep_id and ep_id in manifest:
        return True

    show_id = str(ep.get("show_id") or "").strip()
    ep_num = ep.get("episode_number")
    show_title = str(ep.get("show_title") or "").strip().lower()
    video_url = str(ep.get("video_url") or "").strip()

    for item in manifest.values():
        if not isinstance(item, dict):
            continue

        # 1. Match by show_id + episode_number
        if show_id and item.get("show_id") == show_id and item.get("episode_number") == ep_num:
            return True

        # 2. Match by show_title + episode_number
        if show_title and str(item.get("show_title", "")).strip().lower() == show_title and item.get("episode_number") == ep_num:
            return True

        # 3. Match by exact stream URL
        if video_url and item.get("original_url") == video_url:
            return True

    return False

def load_manifest():
    """Load local manifest across all possible locations; merge with GitHub if needed."""
    manifest = {}

    # Check local candidate paths
    for path in MANIFEST_CANDIDATE_PATHS:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict) and loaded:
                        manifest.update(loaded)
            except Exception:
                pass

    if manifest:
        print(f"📦 បានផ្ទុកទិន្នន័យពី Local Manifest ({len(manifest)} ភាគ) ជោគជ័យ!", flush=True)

    # Sync / merge from GitHub if needed
    try:
        r = httpx.get(GITHUB_MANIFEST_URL, timeout=10)
        if r.status_code == 200:
            gh_manifest = r.json()
            if isinstance(gh_manifest, dict):
                prev_len = len(manifest)
                for k, v in gh_manifest.items():
                    if k not in manifest:
                        manifest[k] = v
                if len(manifest) > prev_len:
                    print(f"🌐 បាន Sync បន្ថែម ({len(manifest) - prev_len} ភាគ) ពី GitHub! (សរុប {len(manifest)} ភាគ)", flush=True)
                save_manifest(manifest)
    except Exception:
        pass

    return manifest

def save_manifest(manifest):
    """Save manifest across all available storage locations (PC & Android)."""
    saved_any = False
    for path in MANIFEST_CANDIDATE_PATHS:
        try:
            parent = os.path.dirname(path)
            if parent and not os.path.exists(parent):
                continue
            with open(path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            saved_any = True
        except Exception:
            pass

    if not saved_any:
        try:
            with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

# ==============================================================================
# DRAMAORA API CLIENT (Auto-Token Refresh & 100% Episode Unlock)
# ==============================================================================

class DramaoraClient:
    """
    High-performance API client for Dramaora.tv
    Extracts drama catalogs and unlocks 100% full VIP episode stream URLs.
    """

    def __init__(self, ticket=DRAMAORA_DEFAULT_TICKET):
        self.ticket = ticket
        self.token = ""
        self.uid = 0
        self.cid = 929
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Referer": "https://vi.dramaora.tv/",
            "Origin": "https://vi.dramaora.tv",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _sign(ts: int) -> str:
        return hashlib.md5((DRAMAORA_KEY + str(ts)).encode()).hexdigest()

    @staticmethod
    def _random_hex(k=32):
        return "".join(random.choices("0123456789abcdef", k=k))

    @staticmethod
    def _random_digits(k=20):
        return "".join(random.choices("0123456789", k=k))

    async def login(self) -> bool:
        """Authenticate session with ticket and device payload."""
        ts = int(time.time())
        payload = {
            "device": self._random_hex(32),
            "deviceId": self._random_digits(20),
            "pageParamStorage": '{"cid":0,"data":""}',
            "ticket": self.ticket,
            "pid": DRAMAORA_PID,
            "version": DRAMAORA_VERSION,
            "ios": 3,
            "cid": "",
            "sign": self._sign(ts),
            "timestamp": ts,
            "lang": "en-us",
            "system_lang": "en-US",
            "gmt": "GMT+07:00"
        }
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=15) as client:
                res = await client.post("https://vi.dramaora.tv/api/User/login", json=payload)
                data = res.json()
                if data.get("code") == 0 and isinstance(data.get("data"), dict):
                    self.token = data["data"].get("token", "")
                    self.uid = data["data"].get("uid", 0)
                    self.cid = data["data"].get("cid", 929)
                    return True
        except Exception as e:
            print(f"  ⚠️ Dramaora login error: {e}", flush=True)
        return False

    async def ensure_session(self):
        if not self.token:
            await self.login()

    async def api_request(self, client: httpx.AsyncClient, endpoint: str, params: dict = None, method: str = "GET", json_payload: dict = None, max_retries: int = 3):
        """Perform API request with automatic token expiration (-6) recovery."""
        if not self.token:
            await self.login()

        for attempt in range(max_retries):
            ts = int(time.time())
            base_params = {
                "pid": DRAMAORA_PID,
                "version": DRAMAORA_VERSION,
                "ios": 3,
                "token": self.token,
                "uid": self.uid,
                "cid": self.cid,
                "lang": "en-us",
                "timestamp": ts,
                "sign": self._sign(ts)
            }
            if params:
                base_params.update(params)

            try:
                if method == "GET":
                    r = await client.get(f"https://vi.dramaora.tv/api/Videocenter/{endpoint}", params=base_params)
                else:
                    body = dict(base_params)
                    if json_payload:
                        body.update(json_payload)
                    r = await client.post(f"https://vi.dramaora.tv/api/Videocenter/{endpoint}", json=body)

                data = r.json()
                if data.get("code") == -6:
                    await self.login()
                    continue
                return data
            except Exception:
                await self.login()
                await asyncio.sleep(0.5)
        return {}

    def parse_url(self, url: str):
        """Extract vid and ticket from Dramaora URL or direct numeric ID."""
        url = str(url).strip()
        if url.isdigit():
            return int(url), self.ticket

        vid = 0
        ticket = self.ticket

        if "#" in url:
            frag = url.split("#", 1)[1]
            qs = frag.split("?", 1)[1] if "?" in frag else ""
            qp = parse_qs(qs)
            vid = int((qp.get("vid") or ["0"])[0])
            if qp.get("ticket"):
                ticket = qp.get("ticket")[0]

        if not vid:
            parsed = urlparse(url)
            qp = parse_qs(parsed.query)
            vid = int((qp.get("vid") or ["0"])[0])
            if qp.get("ticket"):
                ticket = qp.get("ticket")[0]

        return vid, ticket

    async def get_all_drama_catalogue(self):
        """Discover ALL dramas across all Dramaora categories, ranking, and search keywords."""
        await self.ensure_session()
        dramas = {}

        print("🔍 កំពុងស្កេនទាញយកបញ្ជីរឿងទាំងអស់ពី Dramaora.tv (Categories & Catalogs)...", flush=True)

        async with httpx.AsyncClient(headers=self.headers, timeout=20) as client:
            # 1. Crawl all categories
            for lang in ["en-us", "vi-vn", "th-th"]:
                res_json = await self.api_request(client, "getHomeCategoryConfigList", params={"lang": lang})
                categories = res_json.get("list") or res_json.get("data") or []
                if isinstance(categories, list):
                    for cat in categories:
                        cat_id = cat.get("id")
                        cat_name = cat.get("cha_title_name") or cat.get("name") or "Category"
                        for page in range(0, 5):
                            cat_params = {"id": cat_id, "category_id": cat_id, "page": page, "pagesize": 50, "lang": lang}
                            cat_json = await self.api_request(client, "getHomeCategoryById", params=cat_params)
                            raw_list = cat_json.get("list")
                            items = raw_list.get("data", []) if isinstance(raw_list, dict) else (raw_list if isinstance(raw_list, list) else [])
                            if not items:
                                break
                            for it in items:
                                vid = str(it.get("vid") or it.get("id") or "").strip()
                                title = str(it.get("vname") or it.get("title") or it.get("name") or it.get("video_name") or "").strip()
                                poster = it.get("verticpic") or it.get("cover") or it.get("poster") or ""
                                intro = it.get("intro") or it.get("desc") or ""
                                if vid and vid not in dramas:
                                    dramas[vid] = {
                                        "vid": vid,
                                        "title": title or f"Drama_{vid}",
                                        "poster": poster,
                                        "intro": intro,
                                        "category": cat_name,
                                        "ep_count": it.get("episode_count", "?")
                                    }
                            if len(items) < 50:
                                break

            # 2. Popular keyword search crawl to capture all catalog titles
            keywords = ["love", "alpha", "secret", "boss", "bride", "revenge", "king", "wife", "destiny", "desire", "wrong", "billionaire", "wolf", "vampire", "doctor", "princess", "bad"]
            for kw in keywords:
                for page in range(0, 3):
                    rj = await self.api_request(client, "search", params={"keyword": kw, "page": page, "pagesize": 50})
                    raw_list = rj.get("list")
                    items = raw_list.get("data", []) if isinstance(raw_list, dict) else (raw_list if isinstance(raw_list, list) else [])
                    if not items:
                        break
                    for it in items:
                        vid = str(it.get("vid") or it.get("id") or "").strip()
                        title = str(it.get("vname") or it.get("title") or it.get("name") or "").strip()
                        poster = it.get("verticpic") or it.get("cover") or it.get("poster") or ""
                        intro = it.get("intro") or it.get("desc") or ""
                        if vid and vid not in dramas:
                            dramas[vid] = {
                                "vid": vid,
                                "title": title or f"Drama_{vid}",
                                "poster": poster,
                                "intro": intro,
                                "category": "Search",
                                "ep_count": it.get("episode_count", "?")
                            }
                    if len(items) < 50:
                        break

            # 3. Add known IDs as fallback
            for k_vid in KNOWN_DRAMA_IDS:
                if k_vid not in dramas:
                    dramas[k_vid] = {"vid": k_vid, "title": f"Drama_{k_vid}", "ep_count": "?"}

        print(f"✅ រកឃើញរឿងសរុបចំនួន {len(dramas)} រឿង ពី Dramaora.tv!", flush=True)
        return list(dramas.values())

    async def get_drama_info(self, url_or_vid: str, lang="en-us"):
        """
        Fetch drama details and unlock 100% full episode stream URLs.
        Returns: { 'title': str, 'vid': int, 'episodes': [...] }
        """
        vid, ticket = self.parse_url(url_or_vid)
        if not vid:
            return None

        self.ticket = ticket or self.ticket
        await self.ensure_session()

        print(f"🔍 ស្កេនរឿង Dramaora: vid={vid}...", flush=True)

        drama_list = []
        video_info = {}
        langs_to_try = [lang, "en-us", "vi-vn", "th-th"]
        chosen_lang = lang

        async with httpx.AsyncClient(headers=self.headers, timeout=20) as client:
            for test_lang in langs_to_try:
                for page in range(0, 3):
                    d = await self.api_request(
                        client, "getVideoDrama",
                        params={"vid": vid, "eid": "", "pagesize": 100, "page": page, "lang": test_lang}
                    )
                    l = d.get("list", [])
                    if l:
                        drama_list.extend(l)
                        if not video_info:
                            video_info = d.get("videoInfo", {})
                        chosen_lang = test_lang
                        if len(l) < 100:
                            break
                    else:
                        break
                if drama_list:
                    break

            if not drama_list:
                print(f"⚠️ No episodes found for vid={vid}", flush=True)
                return None

            title = video_info.get("vname") or video_info.get("title") or f"Drama_{vid}"

            # Deduplicate raw episode list by unique eid
            seen_eids = set()
            unique_list = []
            for ep in drama_list:
                ep_eid = ep.get("eid")
                if ep_eid and ep_eid not in seen_eids:
                    seen_eids.add(ep_eid)
                    unique_list.append(ep)

            unique_list.sort(key=lambda x: x.get("episodeorder", 1))

            # Unlock all episode stream URLs via getFreeVideoDrama
            print(f"🔓 កំពុង Unlock គ្រប់ភាគ ({len(unique_list)} ភាគ) សម្រាប់រឿង '{title}'...", flush=True)
            streams = {}
            for ep in unique_list:
                ord_num = ep.get("episodeorder", 1)
                ep_eid = ep.get("eid")
                if ord_num in streams:
                    continue

                unlock_payload = {
                    "vid": str(vid),
                    "eid": str(ep_eid),
                    "lang": chosen_lang,
                }
                ud = await self.api_request(client, "getFreeVideoDrama", method="POST", json_payload=unlock_payload)
                items = ud.get("data", [])
                if isinstance(items, list):
                    for it in items:
                        item_ord = it.get("episodeorder")
                        stream_url = it.get("highUrl") or it.get("url") or it.get("sdUrl")
                        if item_ord and stream_url:
                            streams[item_ord] = stream_url

            poster_image = video_info.get("verticpic") or video_info.get("cover") or ""
            drama_intro = video_info.get("intro") or ""

            # Construct finalized episodes list
            episodes = []
            for ep in unique_list:
                ord_num = ep.get("episodeorder", 1)
                ep_id_unique = f"dramaora_{vid}_{ord_num}"
                episodes.append({
                    "id": ep_id_unique,
                    "show_id": f"dramaora_{vid}",
                    "show_title": title,
                    "episode_number": ord_num,
                    "video_url": streams.get(ord_num, ""),
                    "eid": ep.get("eid"),
                    "poster_url": poster_image,
                    "synopsis": drama_intro,
                    "source": "dramaora"
                })

            unlocked_count = sum(1 for e in episodes if e["video_url"])
            print(f"✅ បាន Unlock ជោគជ័យ {unlocked_count}/{len(episodes)} ភាគ សម្រាប់ '{title}'!", flush=True)

            return {
                "title": title,
                "vid": vid,
                "episodes": episodes
            }

            poster_image = video_info.get("verticpic") or video_info.get("cover") or ""
            drama_intro = video_info.get("intro") or ""

            # Construct finalized episodes list
            episodes = []
            for ep in unique_list:
                ord_num = ep.get("episodeorder", 1)
                ep_id_unique = f"dramaora_{vid}_{ord_num}"
                episodes.append({
                    "id": ep_id_unique,
                    "show_id": f"dramaora_{vid}",
                    "show_title": title,
                    "episode_number": ord_num,
                    "video_url": streams.get(ord_num, ""),
                    "eid": ep.get("eid"),
                    "poster_url": poster_image,
                    "synopsis": drama_intro,
                    "source": "dramaora"
                })

            unlocked_count = sum(1 for e in episodes if e["video_url"])
            print(f"✅ បាន Unlock ជោគជ័យ {unlocked_count}/{len(episodes)} ភាគ សម្រាប់ '{title}'!", flush=True)

            return {
                "title": title,
                "vid": vid,
                "episodes": episodes
            }

# ==============================================================================
# STREAM & FILE DOWNLOADER (Auto Retry & Chunk Streaming)
# ==============================================================================

async def download_video_stream(url: str, output_path: str, max_retries: int = 3):
    """Download video stream with auto-retry and chunking."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://vi.dramaora.tv/",
        "Origin": "https://vi.dramaora.tv"
    }

    for attempt in range(1, max_retries + 1):
        if os.path.exists(output_path):
            try: os.remove(output_path)
            except Exception: pass

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
                        async for chunk in response.aiter_bytes(chunk_size=2 * 1024 * 1024):  # 2MB chunk
                            f.write(chunk)
                            total_downloaded += len(chunk)
                            if total_downloaded % (15 * 1024 * 1024) < (2 * 1024 * 1024):
                                print(f"  📥 Downloading... {total_downloaded / (1024 * 1024):.1f} MB", flush=True)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                return True
            else:
                raise Exception("Downloaded file is empty or corrupted")

        except Exception as e:
            print(f"  ⚠️ Download warning (Attempt {attempt}/{max_retries}): {e}", flush=True)
            if attempt == max_retries:
                raise e

# ==============================================================================
# FFMPEG METADATA HELPERS (Graceful Fallback for Pydroid 3)
# ==============================================================================

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
                    duration = int(float(format_info["duration"]))
        except Exception:
            pass

    if has_ffmpeg and duration > 0:
        try:
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
        except Exception:
            pass

    return duration, width, height, (thumb_out_path if thumb_created else None)

async def download_thumbnail_image(poster_url: str, thumb_out_path: str):
    """Download official drama poster image to use as Telegram video thumbnail cover."""
    if not poster_url or not str(poster_url).startswith("http"):
        return None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://vi.dramaora.tv/"
        }
        async with httpx.AsyncClient(headers=headers, timeout=10.0, follow_redirects=True) as client:
            r = await client.get(poster_url)
            if r.status_code == 200 and len(r.content) > 500:
                with open(thumb_out_path, "wb") as f:
                    f.write(r.content)
                if os.path.exists(thumb_out_path) and os.path.getsize(thumb_out_path) > 500:
                    return thumb_out_path
    except Exception:
        pass
    return None

def split_video_if_needed(video_path: str, max_mb: float = 1950.0):
    if not os.path.exists(video_path):
        return [video_path], False

    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    if file_size_mb <= max_mb or not shutil.which("ffmpeg"):
        return [video_path], False

    num_parts = math.ceil(file_size_mb / 1800.0)
    total_dur = 0
    if shutil.which("ffprobe"):
        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
            if res.returncode == 0 and res.stdout.strip():
                total_dur = float(res.stdout.strip())
        except Exception:
            pass

    if total_dur <= 0:
        total_dur = (file_size_mb * 8 * 1024) / 4000.0

    part_dur = total_dur / num_parts
    print(f"  ⚡ Fast Lossless Split into {num_parts} parts...", flush=True)

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
                parts.append(out_part)
        except Exception:
            pass

    if len(parts) == num_parts:
        return parts, True

    for p in parts:
        if os.path.exists(p):
            try: os.remove(p)
            except Exception: pass
    return [video_path], False

# ==============================================================================
# MAIN BACKUP PROCESSOR
# ==============================================================================

async def process_episode_backup(app: Client, ep: dict, manifest: dict, channel_id_int: int):
    """Download, upload, and record a single episode to Telegram."""
    ep_id = str(ep["id"]).strip()
    show_title = ep.get("show_title") or "Unknown Show"
    ep_num = ep.get("episode_number") or 1
    video_url = ep.get("video_url") or ""
    poster_url = ep.get("poster_url") or ""

    if not video_url:
        print(f"  ⚠️ Skipping {show_title} EP {ep_num}: No stream URL.", flush=True)
        return False

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        temp_path = tf.name

    thumb_path = temp_path + ".thumb.jpg"
    video_parts = [temp_path]
    is_split = False

    try:
        print("  ⏳ កំពុង Download ភាគនេះពី Dramaora...", flush=True)
        await download_video_stream(video_url, temp_path, max_retries=3)

        raw_size_mb = os.path.getsize(temp_path) / (1024 * 1024)
        print(f"  ✅ Download រួចរាល់ ({raw_size_mb:.1f} MB). កំពុងរៀបចំ Upload...", flush=True)

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
            
            # 🖼️ Capture & Download Official Drama Poster Thumbnail if no ffmpeg thumb
            if not thumb_file and poster_url:
                thumb_file = await download_thumbnail_image(poster_url, part_thumb)
                if thumb_file:
                    print(f"  🖼️ បានទាញយក Drama Poster Cover សម្រាប់ Thumbnail លើ Telegram!", flush=True)

            if duration > 0:
                print(f"  🎬 Metadata: {duration//60}m{duration%60}s | {width}x{height} | Thumb: {'Yes' if thumb_file else 'No'}", flush=True)

            part_suffix = f" (Part {part_idx}/{total_parts})" if total_parts > 1 else ""
            caption = (
                f"🎬 **{show_title}**\n"
                f"📌 **ភាគ / Episode:** {ep_num}{part_suffix}\n"
                f"⚡ **Source:** Dramaora FHD (Unlocked)\n"
                f"📦 **Size:** {part_size_mb:.1f} MB\n"
                f"🆔 `ep_id: {ep_id}`"
            )
            if poster_url:
                caption += f"\n🖼️ **Poster:** [មើលរូបភាព Poster]({poster_url})"

            last_logged_pct = -1
            def progress(current, total):
                nonlocal last_logged_pct
                pct = int((current / total) * 100)
                if pct % 20 == 0 and pct != last_logged_pct:
                    last_logged_pct = pct
                    part_label = f"[Part {part_idx}/{total_parts}] " if total_parts > 1 else ""
                    print(f"  📤 {part_label}Uploading: {pct}% ({current / (1024*1024):.1f} MB / {total / (1024*1024):.1f} MB)", flush=True)

            # Upload video to Telegram (Pyrogram requires duration, width, height to be int, not None)
            msg: Message = await app.send_video(
                chat_id=channel_id_int,
                video=part_file,
                caption=caption,
                duration=int(duration or 0),
                width=int(width or 0),
                height=int(height or 0),
                thumb=thumb_file if (thumb_file and os.path.exists(thumb_file) and os.path.getsize(thumb_file) > 0) else None,
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

            await asyncio.sleep(2)

        if primary_msg_id:
            manifest[ep_id] = {
                "show_id": ep.get("show_id", ""),
                "show_title": show_title,
                "episode_number": ep_num,
                "telegram_message_id": primary_msg_id,
                "telegram_file_id": primary_file_id,
                "telegram_message_ids": uploaded_msg_ids,
                "total_parts": total_parts,
                "file_size_mb": round(total_uploaded_size_mb, 2),
                "original_url": video_url,
                "poster_url": ep.get("poster_url", ""),
                "synopsis": ep.get("synopsis", ""),
                "source": "dramaora",
                "backed_up_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            save_manifest(manifest)
            await sync_to_google_sheet(ep_id, manifest[ep_id])
            return True

    except Exception as err:
        print(f"  ❌ Error processing episode {ep_id}: {err}", flush=True)
        return False
    finally:
        # Crucial for Android / Pydroid 3: Clean up temporary files immediately!
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

    return False

# ==============================================================================
# MAIN RUNNER (100% Automatic Execution)
# ==============================================================================

async def main():
    start_time = time.time()

    print("=" * 65, flush=True)
    print("   🚀 DRAMAORA.TV -> TELEGRAM AUTO BACKUP (1-CLICK ENGINE)", flush=True)
    print("   📱 Optimized for Pydroid 3 (Android) / PC / GitHub Actions", flush=True)
    print("=" * 65, flush=True)

    if not all([API_ID, API_HASH, BOT_TOKEN, CHANNEL_ID]):
        print("❌ Missing Telegram credentials. Please check your config.", flush=True)
        return

    try:
        api_id_int = int(API_ID)
        channel_id_int = int(CHANNEL_ID)
    except ValueError as e:
        print(f"❌ Error parsing numeric IDs: {e}", flush=True)
        return

    manifest = load_manifest()

    d_client = DramaoraClient()
    print("🌐 កំពុងតភ្ជាប់ទៅកាន់ Dramaora.tv...", flush=True)
    await d_client.login()

    # If specific drama passed in command line arguments, use it; otherwise auto-crawl all
    target_episodes = []
    if len(sys.argv) > 1 and sys.argv[1].strip() and not sys.argv[1].startswith("-"):
        custom_target = sys.argv[1].strip()
        print(f"🎯 ដំណើរការ Backup រឿងជាក់លាក់: {custom_target}", flush=True)
        info = await d_client.get_drama_info(custom_target)
        if info and info.get("episodes"):
            target_episodes = info["episodes"]
    else:
        print("📋 កំពុងស្កេនទាញបញ្ជីរឿងទាំងអស់ពី Dramaora.tv...", flush=True)
        catalogue = await d_client.get_all_drama_catalogue()
        print(f"✅ រកឃើញ {len(catalogue)} រឿង។ កំពុងរៀបចំ Unlock គ្រប់ភាគ...", flush=True)
        for d in catalogue:
            d_info = await d_client.get_drama_info(str(d["vid"]))
            if d_info and d_info.get("episodes"):
                target_episodes.extend(d_info["episodes"])

    # Filter out already backed-up episodes (Zero-duplication check)
    pending = []
    for ep in target_episodes:
        if not is_already_backed_up(ep, manifest):
            pending.append(ep)

    print("\n" + "-" * 60, flush=True)
    print(f"📊 ស្ថានភាពទិន្នន័យ Backup:", flush=True)
    print(f"  • បាន Backup រួចរាល់: {len(manifest)} ភាគ", flush=True)
    print(f"  • នៅសល់ត្រូវ Backup: {len(pending)} ភាគ", flush=True)
    time_limit_str = "គ្មានដែនកំណត់ (Unlimited - រត់រហូតដល់ចប់)" if MAX_RUN_SECONDS <= 0 else f"{MAX_RUN_SECONDS // 60} នាទី ({MAX_RUN_SECONDS}s)"
    print(f"  • ដែនកំណត់ម៉ោង (Time Limit): {time_limit_str}", flush=True)
    print("-" * 60, flush=True)

    if not pending:
        print("🎉 គ្រប់ភាគទាំងអស់ត្រូវបាន Backup ចូល Telegram រួចរាល់អស់ហើយ! (All up to date)", flush=True)
        return

    print("\n🤖 Connecting to Telegram Bot...", flush=True)
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
    run_list = pending[:MAX_BATCH] if MAX_BATCH > 0 else pending

    for i, ep in enumerate(run_list, 1):
        elapsed = time.time() - start_time
        
        # Check time limit only if MAX_RUN_SECONDS is explicitly greater than 0
        if MAX_RUN_SECONDS > 0:
            remaining_time = MAX_RUN_SECONDS - elapsed
            if remaining_time < 180 and i > 1:
                print(f"\n⏰ Time limit reached ({elapsed/60:.1f}m). Gracefully pausing to save progress.", flush=True)
                break

        show_title = ep.get("show_title") or "Unknown"
        ep_num = ep.get("episode_number", 1)

        print(f"\n[{i}/{len(run_list)}] 🚀 Starting: {show_title} - Episode {ep_num} ({elapsed/60:.1f}m running)", flush=True)
        ok = await process_episode_backup(app, ep, manifest, channel_id_int)
        if ok:
            success_count += 1

    # Send summary notification to Telegram channel
    if success_count > 0:
        try:
            total_backed = len(manifest)
            total_size_mb = sum(m.get("file_size_mb", 0) for m in manifest.values())
            summary_text = (
                f"📊 **Dramaora Auto Backup Report**\n"
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
