import os
import sys
import asyncio
import tempfile
import httpx
import pyrogram.utils

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Fix Pyrogram 64-bit Channel ID support
pyrogram.utils.MIN_CHANNEL_ID = -100999999999999
pyrogram.utils.MAX_CHANNEL_ID = -1000000000000

from pyrogram import Client

API_ID = 20360418
API_HASH = "3990d0d3cc6c5bd81c93a13cd5e3a311"
BOT_TOKEN = "8890281595:AAGEvtsLcj_bJI1AoNQE3-BUh9-AdqzVN5g"
CHANNEL_ID = -1003943277744

SUPABASE_URL = "https://dowjxhkijtlsdvhyuddt.supabase.co"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRvd2p4aGtpanRsc2R2aHl1ZGR0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYyMjE3MTIsImV4cCI6MjEwMTc5NzcxMn0.ulxBnNG6fc6muqPrAxzEGw0VPyZpR5ug8bY713PyWGg"

async def main():
    print("🚀 [Step 1/4] កំពុងតភ្ជាប់ទៅកាន់ Telegram Bot...", flush=True)
    app = Client("test_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True, ipv6=False)
    await app.start()
    print("✅ [Step 1/4] Bot បានតភ្ជាប់ជោគជ័យ!", flush=True)

    print("🔍 [Step 2/4] កំពុងទាញយកព័ត៌មានវីដេអូពី Database...", flush=True)
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {ANON_KEY}"}
    async with httpx.AsyncClient(timeout=30) as client:
        # Get episode with valid s3 link
        r = await client.get(
            f"{SUPABASE_URL}/rest/v1/episodes?select=id,show_id,title,episode_number,video_url&video_url=like.*s3.nintanime.com*&order=created_at.desc&limit=1",
            headers=headers
        )
        episodes = r.json()
        ep = episodes[0]
        
        r_show = await client.get(
            f"{SUPABASE_URL}/rest/v1/shows?select=id,title&id=eq.{ep['show_id']}",
            headers=headers
        )
        show = r_show.json()[0]

    show_title = show.get("title", "Anime")
    ep_num = ep.get("episode_number", 1)
    video_url = ep["video_url"]

    print(f"🎬 ជ្រើសរើសវីដេអូ: {show_title} (ភាគ {ep_num})", flush=True)
    print(f"🔗 Video URL: {video_url}", flush=True)

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        print("⏳ [Step 3/4] កំពុង Download វីដេអូពី Server...", flush=True)
        headers_dl = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=30.0), follow_redirects=True) as dl_client:
            async with dl_client.stream("GET", video_url, headers=headers_dl) as resp:
                total_bytes = 0
                with open(temp_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
                        total_bytes += len(chunk)
                        print(f"\r  📥 Downloaded: {total_bytes / (1024 * 1024):.1f} MB", end="", flush=True)

        size_mb = os.path.getsize(temp_path) / (1024 * 1024)
        print(f"\n✅ [Step 3/4] Download រួចរាល់! ទំហំសរុប: {size_mb:.1f} MB", flush=True)

        print("📤 [Step 4/4] កំពុង Upload វីដេអូទៅកាន់ Telegram Channel...", flush=True)
        
        last_pct = 0
        def progress(current, total):
            nonlocal last_pct
            pct = int((current / total) * 100)
            if pct != last_pct and pct % 5 == 0:
                last_pct = pct
                print(f"\r  🚀 Uploading: {current / (1024*1024):.1f} MB / {total / (1024*1024):.1f} MB ({pct}%)", end="", flush=True)

        caption = (
            f"🎬 **{show_title}**\n"
            f"📌 **ភាគ / Episode:** x{ep_num}\n"
            f"⚡ **Quality:** 1080p FHD\n"
            f"📦 **Size:** {size_mb:.1f} MB\n"
            f"🆔 `ep_id: {ep['id']}`"
        )

        msg = await app.send_video(
            chat_id=CHANNEL_ID,
            video=temp_path,
            caption=caption,
            supports_streaming=True,
            progress=progress
        )

        print(f"\n\n🎉 [ជោគជ័យ ១០០%] វីដេអូត្រូវបាន Upload ចូល Telegram Channel រួចរាល់! (Message ID: {msg.id})", flush=True)

    except Exception as err:
        print(f"\n❌ Error: {err}", flush=True)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
