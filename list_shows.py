import json, sys

sys.stdout.reconfigure(encoding='utf-8')

with open("backup_manifest.json", "r", encoding="utf-8") as f:
    manifest = json.load(f)

shows = {}
for ep_id, item in manifest.items():
    title = item.get("show_title", "Unknown")
    source = item.get("source", "")
    show_id = item.get("show_id", "")
    if title not in shows:
        shows[title] = {"count": 0, "source": source, "show_id": show_id, "ep_ids": []}
    shows[title]["count"] += 1
    shows[title]["ep_ids"].append(ep_id)

print("=== ALL SHOWS IN MANIFEST ===")
for t, d in shows.items():
    print(f"- {t}: {d['count']} eps | Source: {d['source']} | ID: {d['show_id']}")
