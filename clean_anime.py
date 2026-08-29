import json, httpx, sys

sys.stdout.reconfigure(encoding='utf-8')

GAS_URL = "https://script.google.com/macros/s/AKfycbyeNw3vClMRYMWssYT-gTncSntQUvVvHb43QcDYR5k4RXLrFPDzS5vEh5PZyWM95XXmSg/exec"

with open("backup_manifest.json", "r", encoding="utf-8") as f:
    manifest = json.load(f)

# Keep ONLY Dramaora dramas
dramaora_manifest = {}
deleted_shows = set()

for ep_id, item in manifest.items():
    source = item.get("source", "")
    show_id = str(item.get("show_id", ""))
    title = item.get("show_title", "")
    if source == "dramaora" or "dramaora" in show_id:
        dramaora_manifest[ep_id] = item
    else:
        deleted_shows.add(title)

print(f"🗑️ Deleted Anime Shows: {', '.join(deleted_shows)}")
print(f"✅ Remaining Dramaora Episodes: {len(dramaora_manifest)}")

# Save to local backup_manifest.json and www/backup_manifest.json
with open("backup_manifest.json", "w", encoding="utf-8") as f:
    json.dump(dramaora_manifest, f, ensure_ascii=False, indent=2)

with open("www/backup_manifest.json", "w", encoding="utf-8") as f:
    json.dump(dramaora_manifest, f, ensure_ascii=False, indent=2)

print("💾 Saved filtered manifest locally!")

# Sync to Google Sheets Web App
print("🌐 Syncing filtered manifest to Google Sheets...")
try:
    r = httpx.post(GAS_URL, json={"action": "bulk_sync", "manifest": dramaora_manifest}, timeout=30.0, follow_redirects=True)
    print("Google Sheets Response:", r.status_code, r.text[:200])
except Exception as e:
    print("Error syncing to Google Sheet:", e)
