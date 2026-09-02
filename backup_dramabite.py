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
import tempfile

# Auto-install missing packages (needed for Pydroid 3 Android)
def _ensure_package(pkg_name, import_name=None):
    import_name = import_name or pkg_name
    try:
        __import__(import_name)
    except ImportError:
        print(f"Installing {pkg_name}...", flush=True)
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", pkg_name, "--quiet"], check=False)

_ensure_package("requests")
_ensure_package("httpx")

try:
    import requests
except ImportError:
    requests = None

# Paths & Directories (Smart Auto-Detection for PC & Android Pydroid 3)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()

# DramaBite platform folder - auto-detect PC or Android
def _find_dramabite_base():
    candidates = [
        r"C:\Users\sheakmeng\Desktop\DramaBite",
        "/sdcard/Download/DramaBite",
        "/storage/emulated/0/Download/DramaBite",
        "/sdcard/DramaBite",
        os.path.join(SCRIPT_DIR, "DramaBite"),
        os.path.join(os.path.dirname(SCRIPT_DIR), "DramaBite"),
    ]
    for c in candidates:
        if os.path.isdir(os.path.join(c, "platforms")):
            return c
    return r"C:\Users\sheakmeng\Desktop\DramaBite"

DRAMABITE_BASE_DIR = _find_dramabite_base()
if os.path.isdir(os.path.join(DRAMABITE_BASE_DIR, "platforms")):
    if DRAMABITE_BASE_DIR not in sys.path:
        sys.path.insert(0, DRAMABITE_BASE_DIR)

# ==============================================================================
# DRAMABITE STANDALONE BYPASS ENGINE (Self-Contained for PC & Android Pydroid 3)
# ==============================================================================
from urllib.parse import parse_qs, unquote, urlsplit

class DramabiteMixin:
    """Dramabite public API parser and preload bypass engine."""
    _DRAMABITE_BASE = "https://www.dramabite.media"
    _DRAMABITE_API = _DRAMABITE_BASE + "/short_video/video_svr"
    _DRAMABITE_CDN_VIDEO = "https://cdn-video.miniepisode.media"
    _DRAMABITE_CDN_IMAGE = "https://cdn-oss.miniepisode.media"
    _DRAMABITE_DETAIL_CACHE_SECONDS = 120

    def _report_status(self, msg):
        print(f"  [Bypass] {msg}", flush=True)

    @property
    def _safe_session(self):
        if not hasattr(self, "session") or self.session is None:
            import requests
            self.session = requests.Session()
        return self.session

    def _dramabite_api(self, endpoint, params=None):
        params = params or {}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Origin": self._DRAMABITE_BASE,
            "Referer": self._DRAMABITE_BASE + "/",
        }
        try:
            resp = self._safe_session.get(
                f"{self._DRAMABITE_API}{endpoint}",
                params=params,
                headers=headers,
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                for key in ("data", "result", "rsp_body"):
                    nested = data.get(key)
                    if isinstance(nested, dict) and nested:
                        return nested
                return data
        except Exception:
            pass
        return {}

    @staticmethod
    def _dramabite_parse_url(url):
        raw = str(url or "").strip()
        for _ in range(2):
            decoded = unquote(raw)
            if decoded == raw:
                break
            raw = decoded
        cid = None
        vid = None
        try:
            parts = urlsplit(raw)
            queries = [parts.query]
            frag = parts.fragment or ""
            if "?" in frag:
                queries.append(frag.split("?", 1)[1])
            for query in queries:
                if not query:
                    continue
                parsed = parse_qs(query)
                if not cid:
                    vals = (
                        parsed.get("cid")
                        or parsed.get("content_id")
                        or parsed.get("collection_id")
                        or parsed.get("book_id")
                        or []
                    )
                    if vals:
                        cid = str(vals[0]).strip()
                if vid is None:
                    vals = parsed.get("vid") or parsed.get("episode") or parsed.get("ep") or []
                    if vals:
                        try:
                            vid = int(vals[0])
                        except (TypeError, ValueError):
                            pass
        except Exception:
            pass

        if not cid:
            m = re.search(r"[?&#](?:cid|content_id|collection_id|book_id)=([a-zA-Z0-9_-]+)", raw, re.IGNORECASE)
            if m:
                cid = m.group(1)
        if vid is None:
            m = re.search(r"[?&#](?:vid|episode|ep)=(\d+)", raw, re.IGNORECASE)
            if m:
                try:
                    vid = int(m.group(1))
                except (TypeError, ValueError):
                    pass

        if not cid:
            m = re.search(r"/(?:play|drama|series)/([a-zA-Z0-9_-]+)(?:/(\d+))?", raw, re.IGNORECASE)
            if m:
                cid = m.group(1)
                if vid is None and m.group(2):
                    vid = int(m.group(2))

        if vid is None or vid < 1:
            vid = 1
        return cid, vid

    def _dramabite_play_url(self, cid, vid=1):
        return f"{self._DRAMABITE_BASE}/#/play?cid={cid}&vid={int(vid)}"

    def _dramabite_abs_video(self, path):
        if not path:
            return ""
        if str(path).startswith("http://") or str(path).startswith("https://"):
            return str(path)
        return f"{self._DRAMABITE_CDN_VIDEO}/{str(path).lstrip('/')}"

    def _dramabite_abs_image(self, path):
        if not path:
            return ""
        path = str(path)
        if path.startswith("http://") or path.startswith("https://"):
            return path
        base = self._DRAMABITE_CDN_VIDEO if path.startswith("video/") else self._DRAMABITE_CDN_IMAGE
        return f"{base}/{path.lstrip('/')}"

    def _dramabite_get_dramas(self, max_pages=12):
        dramas = []
        seen = set()
        for page in range(max_pages):
            if getattr(self, "_cancelled", False):
                break
            self._report_status(f"🔄 Fetching Dramabite homepage page {page + 1}…")
            data = self._dramabite_api("/homepage", {"page": page})
            modules = data.get("module_list") or []
            if not modules:
                break
            before = len(dramas)
            for module in modules:
                for item in module.get("video_list") or []:
                    cid = str(item.get("cid") or (item.get("linkInfo") or {}).get("cid") or "").strip()
                    title = str(item.get("title") or "").strip()
                    if not cid or not title or cid in seen:
                        continue
                    seen.add(cid)
                    thumb = self._dramabite_abs_image(
                        item.get("cover_url") or item.get("video_cover") or ((item.get("linkInfo") or {}).get("cover"))
                    )
                    dramas.append({
                        "title": title,
                        "url": self._dramabite_play_url(cid, item.get("vid") or 1),
                        "thumb": thumb,
                        "ep_count": item.get("total_episode") or "",
                    })
            if len(dramas) == before:
                break
        return dramas

    def _dramabite_episode_list(self, cid):
        for params in ({"cid": cid, "page": 1}, {"cid": cid, "page": 0}, {"cid": cid}):
            data = self._dramabite_api("/episode_list", params)
            eps = data.get("episode_list") or data.get("episodes") or data.get("video_list") or []
            if isinstance(eps, list) and eps:
                return eps
        return []

    def _dramabite_episode_detail(self, cid, vid, force_refresh=False):
        cache = getattr(self, "_dramabite_detail_cache", None)
        if cache is None:
            cache = {}
            self._dramabite_detail_cache = cache
        key = (str(cid), int(vid))
        cached = cache.get(key)
        if cached and not force_refresh:
            if isinstance(cached, dict) and "data" in cached and "fetched_at" in cached:
                age = time.monotonic() - float(cached.get("fetched_at") or 0)
                if age < self._DRAMABITE_DETAIL_CACHE_SECONDS:
                    return cached.get("data") or {}
            elif isinstance(cached, dict):
                cache.pop(key, None)
        data = self._dramabite_api("/episode_detail", {"cid": cid, "vid": int(vid)})
        if isinstance(data, dict) and data:
            cache[key] = {"fetched_at": time.monotonic(), "data": data}
        return data

    def _dramabite_pick_stream(self, entry, target_vid):
        if not isinstance(entry, dict):
            return None
        try:
            entry_vid = int(entry.get("vid") or 0)
        except (TypeError, ValueError):
            entry_vid = 0
        if target_vid and entry_vid and entry_vid != int(target_vid):
            return None
        path = (
            entry.get("multi_rate_m3u8")
            or entry.get("video_link_m3u8")
            or entry.get("m3u8_url")
            or entry.get("play_url")
            or entry.get("video_link")
            or entry.get("url")
        )
        if not path:
            return None
        return self._dramabite_abs_video(path)

    def _dramabite_find_stream_in_detail(self, data, target_vid):
        if not isinstance(data, dict):
            return None, None
        current = self._dramabite_pick_stream(data.get("link_info") or data.get("linkInfo"), target_vid)
        if current:
            return current, "link_info"
        for key in ("next_video", "last_video", "nextVideo", "lastVideo"):
            picked = self._dramabite_pick_stream(data.get(key), target_vid)
            if picked:
                return picked, key
        for item in data.get("preload_episode_links") or data.get("preloadEpisodeLinks") or []:
            picked = self._dramabite_pick_stream(item, target_vid)
            if picked:
                return picked, "preload_episode_links"
        return None, None

    def _dramabite_drama_info(self, url):
        cid, vid = self._dramabite_parse_url(url)
        if not cid:
            self._report_status("⚠ Cannot find Dramabite cid in URL")
            return "", [], ""
        self._report_status(f"🔄 Fetching Dramabite drama info (cid={cid})…")
        detail = self._dramabite_episode_detail(cid, vid)
        episodes_raw = self._dramabite_episode_list(cid)
        title = str(detail.get("video_title") or detail.get("title") or "").strip() or f"Dramabite {cid}"
        thumbnail = self._dramabite_abs_image(
            detail.get("video_cover") or detail.get("cover_url") or detail.get("video_poster_url")
            or detail.get("poster") or ((detail.get("link_info") or detail.get("linkInfo") or {}).get("cover"))
            or ((episodes_raw[0] if episodes_raw else {}).get("cover_url"))
        )
        episodes = []
        for ep in episodes_raw:
            try:
                ep_vid = int(ep.get("vid") or ep.get("episode") or ep.get("episode_number") or 0)
            except (TypeError, ValueError):
                continue
            if ep_vid < 1:
                continue
            episodes.append({
                "num": ep_vid,
                "url": self._dramabite_play_url(cid, ep_vid),
                "title": f"{title}_EP{ep_vid:03d}",
                "locked": bool(ep.get("status")),
            })
        if not episodes:
            total = detail.get("total_episode") or detail.get("update_episode") or 0
            try:
                total = int(total)
            except (TypeError, ValueError):
                total = 0
            for ep_vid in range(1, total + 1):
                episodes.append({
                    "num": ep_vid,
                    "url": self._dramabite_play_url(cid, ep_vid),
                    "title": f"{title}_EP{ep_vid:03d}",
                    "locked": ep_vid > 1,
                })
        episodes.sort(key=lambda x: x["num"])
        free = sum(1 for ep in episodes if not ep.get("locked"))
        locked = len(episodes) - free
        if locked:
            self._report_status(f"✅ Found {len(episodes)} Dramabite episodes ({free} free, {locked} locked)")
        else:
            self._report_status(f"✅ Found {len(episodes)} Dramabite episodes")
        return title, episodes, thumbnail

    def _dramabite_video_url(self, episode_url, force_bypass=False):
        cid, vid = self._dramabite_parse_url(episode_url)
        if not cid:
            self._report_status("⚠ Invalid Dramabite episode URL")
            return None
        self._report_status(f"🔄 Dramabite EP{vid:03d}: querying API…")
        detail = self._dramabite_episode_detail(cid, vid, force_refresh=bool(force_bypass))
        stream_url, source = self._dramabite_find_stream_in_detail(detail, vid)
        if stream_url:
            self._report_status(f"✅ Dramabite EP{vid:03d}: stream ready")
            return stream_url
        start_prev = max(1, vid - 1)
        end_prev = max(1, vid - 8)
        for prev_vid in range(start_prev, end_prev - 1, -1):
            prev_detail = self._dramabite_episode_detail(cid, prev_vid, force_refresh=bool(force_bypass))
            stream_url, source = self._dramabite_find_stream_in_detail(prev_detail, vid)
            if stream_url:
                self._report_status(f"🔓 Dramabite bypass: EP{vid:03d} via EP{prev_vid:03d} {source}")
                return stream_url
        if detail.get("need_download_app") or detail.get("status"):
            self._report_status("⚠ Dramabite locked episode: bypass failed")
        else:
            self._report_status("⚠ Could not resolve Dramabite stream URL")
        return None


class DramaBiteBypassClient(DramabiteMixin):
    def __init__(self):
        import requests as rq
        self.session = rq.Session()
        self._cancelled = False
        self._dramabite_detail_cache = {}

    def _report_status(self, msg):
        print(f"  [Bypass] {msg}", flush=True)

BYPASS_AVAILABLE = True
print("[OK] DramaBite Standalone Bypass Engine loaded! (Android & PC Ready)", flush=True)


def find_dramabite_downloads_dir():
    candidates = [
        r"C:\Users\sheakmeng\Desktop\DramaBite\downloads",
        r"C:\Users\sheakmeng\Desktop\DramaBite",
        "/sdcard/Download/DramaBite/downloads",
        "/sdcard/Download/DramaBite",
        "/storage/emulated/0/Download/DramaBite/downloads",
        "/storage/emulated/0/Download/DramaBite",
        "/sdcard/DramaBite",
        "/storage/emulated/0/DramaBite",
        "/sdcard/Download",
        "/storage/emulated/0/Download",
        os.path.join(SCRIPT_DIR, "downloads"),
        SCRIPT_DIR
    ]
    for c in candidates:
        if os.path.isdir(c):
            for root, dirs, files in os.walk(c):
                if any(f.lower().endswith(('.mp4', '.mkv', '.ts', '.mov')) and not f.lower().startswith('test_') for f in files):
                    return c
    if sys.platform == "win32":
        return r"C:\Users\sheakmeng\Desktop\DramaBite\downloads"
    return "/sdcard/Download"

DRAMABITE_DOWNLOADS = find_dramabite_downloads_dir()
DRAMABITE_FFMPEG = r"C:\Users\sheakmeng\Desktop\DramaBite\ffmpeg"

# Add bundled FFmpeg to PATH if present
if os.path.isdir(DRAMABITE_FFMPEG) and DRAMABITE_FFMPEG not in os.environ.get("PATH", ""):
    os.environ["PATH"] = DRAMABITE_FFMPEG + os.pathsep + os.environ.get("PATH", "")

# Auto-load .env
def _load_env_file():
    candidates = [
        os.path.join(SCRIPT_DIR, ".env"),
        "/sdcard/Download/.env",
        "/storage/emulated/0/Download/.env",
        r"C:\Users\sheakmeng\Desktop\DramaBite\.env",
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

API_ID = os.getenv("TG_API_ID", "20360418").strip().strip('"').strip("'")
API_HASH = os.getenv("TG_API_HASH", "3990d0d3cc6c5bd81c93a13cd5e3a311").strip().strip('"').strip("'")
BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "8664822430:AAFW9z9BL1KLt-_tYypVM4zqnWWBmoXkzuw").strip().strip('"').strip("'")
CHANNEL_ID = os.getenv("TG_CHANNEL_ID", "-1003943277744").strip().strip('"').strip("'")
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


def scan_dramabite_online(manifest: dict):
    """
    Online Mode: Use the DramaBite Bypass Engine to crawl all dramas from the API,
    unlock stream URLs, and return a list of episodes to backup (same format as scan_dramabite_downloads).
    Only returns episodes NOT already in the manifest.
    """
    if not BYPASS_AVAILABLE:
        print("⚠️ DramaBite Bypass Engine not available. Online Mode disabled.", flush=True)
        return []

    client = DramaBiteBypassClient()
    print("🌐 [Online Mode] កំពុងស្កេន DramaBite API ដើម្បី Crawl រឿងទាំងអស់...", flush=True)

    dramas = client._dramabite_get_dramas(max_pages=15)
    print(f"✅ រកឃើញ {len(dramas)} រឿងលើ DramaBite។", flush=True)

    pending_eps = []
    for drama in dramas:
        title = drama.get("title", "Unknown")
        url = drama.get("url", "")
        thumb = drama.get("thumb", "")
        if not url:
            continue

        clean_slug = re.sub(r'[^a-zA-Z0-9]+', '_', title).strip('_').lower()
        show_id = f"dramabite_online_{clean_slug}"

        drama_title, episodes, drama_thumb = client._dramabite_drama_info(url)
        if not episodes:
            continue

        poster_url = thumb or drama_thumb

        for ep in episodes:
            ep_num = ep.get("num", 1)
            ep_id = f"dramabite_online_{clean_slug}_{ep_num}"
            if ep_id in manifest:
                continue  # Already backed up

            ep_url = ep.get("url", "")
            if not ep_url:
                continue

            # Resolve stream URL via bypass
            stream_url = client._dramabite_video_url(ep_url)
            if not stream_url:
                print(f"  ⛔ Bypass failed: {drama_title} EP{ep_num}", flush=True)
                continue

            pending_eps.append({
                "id": ep_id,
                "show_id": show_id,
                "show_title": drama_title or title,
                "episode_number": ep_num,
                "stream_url": stream_url,
                "poster_url": poster_url,
                "synopsis": f"DramaBite Online HD - {drama_title}",
                "source": "dramabite_online",
                "cid_url": ep_url
            })

    return pending_eps



async def get_telegram_cdn_url(app: Client, file_id: str) -> str:
    """Get direct Telegram CDN download URL from file_id (MP4 direct link for player)."""
    try:
        file = await app.get_file(file_id)
        if file and file.file_path:
            return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    except Exception:
        pass
    return ""


def convert_to_mp4(input_path: str) -> str:
    """Fast stream copy remux for non-MP4 files (.ts, .mkv) to .mp4 without re-encoding."""
    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".mp4":
        return input_path

    ffmpeg_bin = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if not ffmpeg_bin:
        bundled = os.path.join(DRAMABITE_BASE_DIR, "ffmpeg", "ffmpeg.exe")
        if os.path.isfile(bundled):
            ffmpeg_bin = bundled
    if not ffmpeg_bin:
        return input_path

    mp4_path = os.path.splitext(input_path)[0] + "_fast.mp4"
    cmd = [
        ffmpeg_bin, "-y",
        "-i", input_path,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        "-movflags", "+faststart",
        mp4_path
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        if res.returncode == 0 and os.path.isfile(mp4_path) and os.path.getsize(mp4_path) > 1024 * 50:
            return mp4_path
    except Exception:
        pass
    return input_path


async def download_hls_stream(stream_url: str, output_path: str) -> bool:
    """Download HLS stream via FFmpeg or robust multi-threaded TS chunk downloader for Android."""
    ffmpeg_bin = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if not ffmpeg_bin:
        bundled = os.path.join(DRAMABITE_BASE_DIR, "ffmpeg", "ffmpeg.exe")
        if os.path.isfile(bundled):
            ffmpeg_bin = bundled

    headers_str = (
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36\r\n"
        "Referer: https://www.dramabite.media/\r\n"
        "Origin: https://www.dramabite.media\r\n"
    )

    if ffmpeg_bin:
        cmd = [
            ffmpeg_bin, "-y",
            "-reconnect", "1", "-reconnect_at_eof", "1",
            "-reconnect_streamed", "1", "-reconnect_delay_max", "5",
            "-headers", headers_str,
            "-i", stream_url,
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            "-movflags", "+faststart",
            output_path
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
            if result.returncode == 0 and os.path.isfile(output_path) and os.path.getsize(output_path) > 1024 * 50:
                return True
        except Exception:
            pass

    # Native Python Fast Multi-threaded Downloader (for Android & devices without FFmpeg)
    print("  ⚡ [Python Turbo] Multi-threaded direct chunk download...", flush=True)
    try:
        hdrs = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36",
            "Referer": "https://www.dramabite.media/",
            "Origin": "https://www.dramabite.media"
        }
        from urllib.parse import urljoin
        from concurrent.futures import ThreadPoolExecutor

        # Fetch playlist (handle Master Playlist recursion)
        current_url = stream_url
        ts_urls = []
        for _ in range(3):
            r = requests.get(current_url, headers=hdrs, timeout=15)
            if r.status_code != 200:
                return False
            lines = [l.strip() for l in r.text.splitlines() if l.strip() and not l.strip().startswith("#")]
            if not lines:
                return False
            
            # Check if lines point to sub-m3u8 or TS segments
            if any(".m3u8" in l.lower() or "m3u8" in l.lower() for l in lines):
                # Pick highest quality / last sub-playlist
                sub_candidates = [l for l in lines if ".m3u8" in l.lower() or "m3u8" in l.lower()]
                current_url = urljoin(current_url, sub_candidates[-1])
                continue
            else:
                ts_urls = [urljoin(current_url, l) for l in lines]
                break

        if not ts_urls:
            return False

        # Multi-threaded download
        chunks_data = [None] * len(ts_urls)

        def _fetch_chunk(idx_url):
            idx, u = idx_url
            for _ in range(3):
                try:
                    res = requests.get(u, headers=hdrs, timeout=12)
                    if res.status_code == 200 and len(res.content) > 0:
                        return idx, res.content
                except Exception:
                    time.sleep(0.5)
            return idx, b""

        with ThreadPoolExecutor(max_workers=8) as ex:
            for idx, content in ex.map(_fetch_chunk, enumerate(ts_urls)):
                chunks_data[idx] = content

        # Write sequentially to output file
        with open(output_path, "wb") as fout:
            for c in chunks_data:
                if c:
                    fout.write(c)

        if os.path.isfile(output_path) and os.path.getsize(output_path) > 1024 * 50:
            return True
    except Exception as e:
        print(f"  ❌ Direct chunk download error: {e}", flush=True)
    return False


async def backup_online_episode(app: Client, ep: dict, manifest: dict, channel_id_int: int) -> bool:
    """Download online DramaBite episode via fast stream copy and upload to Telegram."""
    ep_id = ep["id"]
    show_title = ep["show_title"]
    ep_num = ep["episode_number"]
    stream_url = ep["stream_url"]
    poster_url = ep.get("poster_url", "")

    print(f"  ⚡ [Online Fast] Download + Upload: {show_title} EP{ep_num}...", flush=True)

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        temp_path = tf.name

    thumb_path = temp_path + ".thumb.jpg"

    try:
        ok = await download_hls_stream(stream_url, temp_path)
        if not ok or not os.path.isfile(temp_path) or os.path.getsize(temp_path) < 1024 * 50:
            print(f"  ❌ Download failed: {show_title} EP{ep_num}", flush=True)
            return False

        final_path = temp_path
        part_size_mb = round(os.path.getsize(final_path) / (1024 * 1024), 2)
        print(f"  ✅ Fast Downloaded {part_size_mb:.1f} MB in seconds! Uploading to Telegram...", flush=True)

        duration, width, height, ffmpeg_thumb = extract_video_metadata(final_path, thumb_path)
        thumb_file = ffmpeg_thumb

        if poster_url and str(poster_url).startswith("http"):
            dl_thumb = await download_thumbnail_image(poster_url, thumb_path)
            if dl_thumb:
                thumb_file = dl_thumb

        caption = (
            f"🎬 **{show_title}**\n"
            f"📌 **ភាគ / Episode:** {ep_num}\n"
            f"⚡ **Source:** DramaBite Online HD (Bypass Unlock)\n"
            f"📦 **Size:** {part_size_mb:.1f} MB\n"
            f"🆔 `ep_id: {ep_id}`"
        )
        if poster_url and str(poster_url).startswith("http"):
            caption += f"\n🖼️ **Poster:** [មើលរូបភាព Poster]({poster_url})"

        last_logged_pct = -1
        start_up = time.time()
        def progress(current, total):
            nonlocal last_logged_pct
            pct = int((current / total) * 100) if total > 0 else 0
            if pct != last_logged_pct and pct % 20 == 0:
                last_logged_pct = pct
                speed_mb = (current / (1024 * 1024)) / max(0.1, time.time() - start_up)
                print(f"    Uploading: {pct}% ({current/(1024*1024):.1f}/{total/(1024*1024):.1f} MB) {speed_mb:.1f} MB/s", flush=True)

        msg = await app.send_video(
            chat_id=channel_id_int,
            video=final_path,
            caption=caption,
            duration=int(duration or 0),
            width=int(width or 1280),
            height=int(height or 720),
            thumb=thumb_file if (thumb_file and os.path.isfile(thumb_file)) else None,
            supports_streaming=True,
            progress=progress
        )

        # Get Telegram CDN URL for the uploaded MP4
        tg_file_id = msg.video.file_id if msg.video else None
        tg_cdn_url = ""
        if tg_file_id:
            tg_cdn_url = await get_telegram_cdn_url(app, tg_file_id)

        manifest[ep_id] = {
            "show_id": ep["show_id"],
            "show_title": show_title,
            "episode_number": ep_num,
            "telegram_message_id": msg.id,
            "telegram_file_id": tg_file_id,
            "file_size_mb": part_size_mb,
            "original_url": tg_cdn_url or stream_url,  # Prefer Telegram MP4 CDN URL
            "hls_source_url": stream_url,               # Keep original HLS for reference
            "poster_url": poster_url,
            "synopsis": ep.get("synopsis", ""),
            "source": "dramabite_online",
            "backed_up_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        save_manifest(manifest)
        await sync_to_google_sheet(ep_id, manifest[ep_id])
        print(f"  🎉 Upload ជោគជ័យ! (Message ID: {msg.id})", flush=True)
        return True
    except Exception as err:
        print(f"  ❌ Error: {err}", flush=True)
        return False
    finally:
        for f in [temp_path, thumb_path]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass


async def download_thumbnail_image(poster_url: str, thumb_out_path: str):
    """Download official drama poster image to use as Telegram video thumbnail cover."""
    if not poster_url or not str(poster_url).startswith("http"):
        return None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Safari/537.36",
            "Referer": "https://www.dramabite.media/"
        }
        async with httpx.AsyncClient(headers=headers, timeout=12.0, follow_redirects=True) as client:
            r = await client.get(poster_url)
            if r.status_code == 200 and len(r.content) > 500:
                with open(thumb_out_path, "wb") as f:
                    f.write(r.content)
                if os.path.exists(thumb_out_path) and os.path.getsize(thumb_out_path) > 500:
                    return thumb_out_path
    except Exception:
        pass
    return None

async def backup_dramabite_episode(app: Client, ep: dict, manifest: dict, channel_id_int: int) -> bool:
    ep_id = ep["id"]
    show_title = ep["show_title"]
    ep_num = ep["episode_number"]
    file_path = ep["local_file_path"]
    part_size_mb = ep["file_size_mb"]
    poster_path = ep.get("poster_url")

    thumb_temp = file_path + ".thumb.jpg"
    thumb_file = None
    duration, width, height, ffmpeg_thumb = extract_video_metadata(file_path, thumb_temp)

    # 🖼️ Priority 1: Download and use Official Drama Poster as video cover thumbnail on Telegram
    if poster_path and str(poster_path).startswith("http"):
        downloaded_thumb = await download_thumbnail_image(poster_path, thumb_temp)
        if downloaded_thumb:
            thumb_file = downloaded_thumb
            print(f"  🖼️ បានទាញយក Drama Poster Cover សម្រាប់ Thumbnail លើ Telegram!", flush=True)

    # Priority 2: Local folder poster
    if not thumb_file and poster_path and os.path.isfile(poster_path):
        thumb_file = poster_path

    # Priority 3: Fallback to FFmpeg extracted video frame
    if not thumb_file and ffmpeg_thumb:
        thumb_file = ffmpeg_thumb

    caption = (
        f"🎬 **{show_title}**\n"
        f"📌 **ភាគ / Episode:** {ep_num}\n"
        f"⚡ **Source:** DramaBite HD (Local Upload)\n"
        f"📦 **Size:** {part_size_mb:.1f} MB\n"
        f"🆔 `ep_id: {ep_id}`"
    )
    if poster_path and str(poster_path).startswith("http"):
        caption += f"\n🖼️ **Poster:** [មើលរូបភាព Poster]({poster_path})"

    last_logged_pct = -1
    start_t = time.time()

    def progress(current, total):
        nonlocal last_logged_pct
        pct = int((current / total) * 100) if total > 0 else 0
        if pct != last_logged_pct and pct % 20 == 0:
            last_logged_pct = pct
            speed_mb = (current / (1024 * 1024)) / max(0.1, time.time() - start_t)
            print(f"    Uploading: {pct}% ({current/(1024*1024):.1f}/{total/(1024*1024):.1f} MB) {speed_mb:.1f} MB/s", flush=True)

    try:
        # Auto-convert non-MP4 files (ts, mkv, mov) to MP4 before upload
        upload_path = file_path
        converted_mp4 = None
        ext = os.path.splitext(file_path)[1].lower()
        if ext != ".mp4":
            print(f"  [Convert] {ext} detected - converting to MP4...", flush=True)
            converted_mp4 = convert_to_mp4(file_path)
            if converted_mp4 != file_path:
                upload_path = converted_mp4
                part_size_mb = round(os.path.getsize(upload_path) / (1024 * 1024), 2)
                duration, width, height, ffmpeg_thumb2 = extract_video_metadata(upload_path, thumb_temp)
                if not thumb_file and ffmpeg_thumb2:
                    thumb_file = ffmpeg_thumb2
                print(f"  [Convert] Ready to upload MP4: {part_size_mb:.1f} MB", flush=True)

        msg = await app.send_video(
            chat_id=channel_id_int,
            video=upload_path,
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

        # Get Telegram CDN URL (MP4 direct link) for the player
        tg_cdn_url = ""
        if primary_file_id:
            tg_cdn_url = await get_telegram_cdn_url(app, primary_file_id)

        print(f"  Upload OK! (Message ID: {primary_msg_id}, MP4 CDN: {'Yes' if tg_cdn_url else 'No'})", flush=True)

        manifest[ep_id] = {
            "show_id": ep["show_id"],
            "show_title": show_title,
            "episode_number": ep_num,
            "telegram_message_id": primary_msg_id,
            "telegram_file_id": primary_file_id,
            "telegram_message_ids": [primary_msg_id],
            "total_parts": 1,
            "file_size_mb": part_size_mb,
            "original_url": tg_cdn_url or file_path,
            "local_file": file_path,
            "poster_url": ep.get("poster_url") or "",
            "synopsis": ep.get("synopsis", ""),
            "source": "dramabite",
            "backed_up_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

        save_manifest(manifest)
        await sync_to_google_sheet(ep_id, manifest[ep_id])
        return True

    except Exception as err:
        print(f"  Error uploading {ep_id}: {err}", flush=True)
        return False
    finally:
        if os.path.exists(thumb_temp):
            try: os.remove(thumb_temp)
            except Exception: pass
        if converted_mp4 and converted_mp4 != file_path and os.path.exists(converted_mp4):
            try: os.remove(converted_mp4)
            except Exception: pass


def get_safe_session_path(session_name="backup_session"):
    """Safely prepare session in internal app storage to prevent Android Scoped Storage SQLite errors."""
    import tempfile
    internal_dir = tempfile.gettempdir()
    safe_target = os.path.join(internal_dir, session_name)
    
    candidates = [
        f"{session_name}.session",
        os.path.join(SCRIPT_DIR, f"{session_name}.session"),
        f"/sdcard/Download/{session_name}.session",
        f"/storage/emulated/0/Download/{session_name}.session",
        r"c:\Users\sheakmeng\Desktop\New folder\backup_session.session"
    ]
    for cand in candidates:
        if os.path.isfile(cand):
            try:
                shutil.copy2(cand, f"{safe_target}.session")
                break
            except Exception:
                pass
    return safe_target

async def main():
    print("=" * 65, flush=True)
    print("   🎬 DRAMABITE -> TELEGRAM AUTO BACKUP ENGINE", flush=True)
    print(f"   📁 Local Folder: {DRAMABITE_DOWNLOADS}", flush=True)
    print(f"   🌐 Bypass Engine: {'Ready ✅' if BYPASS_AVAILABLE else 'Not Found ❌'}", flush=True)
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

    # Connect Telegram Bot first
    print("\n🤖 កំពុងតភ្ជាប់ទៅកាន់ Telegram Bot (Backup Anime)...", flush=True)
    session_file = get_safe_session_path("backup_session")
    app = Client(
        session_file,
        api_id=api_id_int,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN
    )
    await app.start()
    print("✅ Telegram Bot connected successfully to channel!", flush=True)

    success_count = 0
    start_t = time.time()

    # ══════════════════════════════════════════════════
    # Phase 1: Backup Local Downloaded Files (Offline Mode)
    # ══════════════════════════════════════════════════
    all_dramabite_eps = scan_dramabite_downloads(custom_dir)
    pending_local = [ep for ep in all_dramabite_eps if ep["id"] not in manifest]

    if pending_local:
        print(f"\n📂 Phase 1 - Local Files: រកឃើញ {len(pending_local)} ភាគថ្មីត្រូវ Backup...", flush=True)
        for idx, ep in enumerate(pending_local, 1):
            print(f"\n[{idx}/{len(pending_local)}] 🚀 Local Upload: {ep['show_title']} (EP {ep['episode_number']}) - {ep['file_size_mb']} MB", flush=True)
            ok = await backup_dramabite_episode(app, ep, manifest, channel_id_int)
            if ok:
                success_count += 1
            await asyncio.sleep(1)
    else:
        print(f"\n📂 Phase 1 - Local Files: គ្រប់ File ក្នុង Folder ត្រូវបាន Backup រួចហើយ ✅", flush=True)

    # ══════════════════════════════════════════════════
    # Phase 2: Bypass Online Mode (Crawl DramaBite API + Unlock + Upload)
    # ══════════════════════════════════════════════════
    if BYPASS_AVAILABLE:
        print(f"\n🌐 Phase 2 - Online Bypass Mode: កំពុង Crawl & Bypass Unlock DramaBite API...", flush=True)
        pending_online = scan_dramabite_online(manifest)

        if pending_online:
            print(f"\n  🔓 រកឃើញ {len(pending_online)} ភាគដែលនៅខ្វះ Backup (Online Mode).", flush=True)
            for idx, ep in enumerate(pending_online, 1):
                elapsed_m = (time.time() - start_t) / 60
                show_title = ep["show_title"]
                ep_num = ep["episode_number"]
                print(f"\n[{idx}/{len(pending_online)}] 🔓 Online Bypass: {show_title} EP{ep_num} ({elapsed_m:.1f}m)...", flush=True)
                ok = await backup_online_episode(app, ep, manifest, channel_id_int)
                if ok:
                    success_count += 1
                await asyncio.sleep(2)
        else:
            print(f"  ✅ DramaBite Online: គ្រប់ភាគទាំងអស់ (Online) ត្រូវបាន Backup រួចរាល់ហើយ!", flush=True)
    else:
        print(f"\n⚠️ Phase 2 Skipped: DramaBite Bypass Engine not available on this device.", flush=True)
        print(f"💡 Bypass Engine ត្រូវការ Folder: {DRAMABITE_BASE_DIR}\\platforms\\", flush=True)

    # Summary
    if success_count > 0:
        try:
            summary = (
                f"🎬 **DramaBite Backup Complete**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"✅ **ទើប Backup ថ្មី:** +{success_count} ភាគ\n"
                f"📁 **សរុបទាំងអស់ក្នុង Archive:** {len(manifest)} ភាគ\n"
                f"⏱️ **រយៈពេល:** {(time.time() - start_t)/60:.1f} នាទី\n"
                f"🚀 **ស្ថានភាព:** ជោគជ័យ (Completed)"
            )
            await app.send_message(chat_id=channel_id_int, text=summary)
            print("📢 បានផ្ញើ Summary ចូល Telegram Channel រួចរាល់!", flush=True)
        except Exception:
            pass
    else:
        print(f"\n🎉 DramaBite ទាំង Local + Online: គ្រប់ភាគបាន Backup រួចអស់ហើយ! (All up to date)", flush=True)

    await app.stop()
    print(f"\n🏁 ចប់! (Total: {success_count} ភាគ, Time: {(time.time() - start_t)/60:.1f} min)", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
