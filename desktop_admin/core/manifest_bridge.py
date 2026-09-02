"""
Manifest Bridge for Animew Pro & DramaFlixHD Desktop Admin.
Handles bidirectional syncing between backup_manifest.json, data.js, and in-memory structures.
"""

import os
import json
import time

class ManifestBridge:
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        self.manifest_path = os.path.join(workspace_dir, "backup_manifest.json")
        self.data_js_path = os.path.join(workspace_dir, "data.js")
        self.www_data_js_path = os.path.join(workspace_dir, "www", "data.js")
        self.manifest = {}
        self.dramas = {} # Keyed by show_id
        self.load()

    def load(self) -> bool:
        """Load manifest and build structured drama records."""
        if os.path.isfile(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    self.manifest = json.load(f)
            except Exception as e:
                print(f"[ManifestBridge] Load error: {e}")
                self.manifest = {}
        else:
            self.manifest = {}

        self.rebuild_dramas()
        return True

    def rebuild_dramas(self):
        """Group episodes into show records."""
        shows = {}
        for ep_id, item in self.manifest.items():
            s_id = item.get("show_id") or "unknown_show"
            if s_id not in shows:
                source = item.get("source") or ("dramaora" if s_id.startswith("dramaora") else "dramabite")
                shows[s_id] = {
                    "id": s_id,
                    "title": item.get("show_title", s_id),
                    "source": source,
                    "poster_url": item.get("poster_url", ""),
                    "synopsis": item.get("synopsis", ""),
                    "is_vip": bool(item.get("is_vip", False)),
                    "episodes": []
                }
            
            # Prefer best poster
            if not shows[s_id]["poster_url"] and item.get("poster_url"):
                shows[s_id]["poster_url"] = item.get("poster_url")

            shows[s_id]["episodes"].append({
                "id": ep_id,
                "episode_number": int(item.get("episode_number") or 1),
                "original_url": item.get("original_url", ""),
                "hls_source_url": item.get("hls_source_url", ""),
                "telegram_message_id": item.get("telegram_message_id"),
                "file_size_mb": item.get("file_size_mb", 0),
                "is_locked": bool(item.get("is_locked", False)),
                "backed_up_at": item.get("backed_up_at", "")
            })

        # Sort episodes by episode_number
        for s_id in shows:
            shows[s_id]["episodes"].sort(key=lambda x: x["episode_number"])

        self.dramas = shows

    def save(self) -> bool:
        """Save memory manifest to backup_manifest.json and export to data.js files."""
        try:
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(self.manifest, f, ensure_ascii=False, indent=2)

            # Export data.js
            js_content = "window.INITIAL_MANIFEST = " + json.dumps(self.manifest, ensure_ascii=False, indent=2) + ";\n"
            
            with open(self.data_js_path, "w", encoding="utf-8") as f:
                f.write(js_content)

            if os.path.isdir(os.path.dirname(self.www_data_js_path)):
                with open(self.www_data_js_path, "w", encoding="utf-8") as f:
                    f.write(js_content)

            self.rebuild_dramas()
            return True
        except Exception as e:
            print(f"[ManifestBridge] Save error: {e}")
            return False

    def update_show_metadata(self, show_id: str, title: str, poster_url: str, synopsis: str = ""):
        """Update show title and poster across all its episode entries."""
        for ep_id, item in self.manifest.items():
            if item.get("show_id") == show_id:
                if title: item["show_title"] = title
                if poster_url: item["poster_url"] = poster_url
                if synopsis is not None: item["synopsis"] = synopsis
        self.save()

    def update_episode(self, ep_id: str, stream_url: str, ep_num: int = None):
        """Update stream URL for a specific episode."""
        if ep_id in self.manifest:
            self.manifest[ep_id]["original_url"] = stream_url
            if ep_num:
                self.manifest[ep_id]["episode_number"] = ep_num
            self.save()

    def add_custom_episode(self, show_id: str, show_title: str, ep_num: int, stream_url: str, poster_url: str = ""):
        """Add or overwrite an episode in the manifest."""
        ep_id = f"{show_id}_{ep_num}"
        source = "dramaora" if show_id.startswith("dramaora") else "dramabite_online"
        self.manifest[ep_id] = {
            "show_id": show_id,
            "show_title": show_title,
            "episode_number": ep_num,
            "original_url": stream_url,
            "poster_url": poster_url,
            "source": source,
            "backed_up_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        self.save()

    def delete_episode(self, ep_id: str):
        """Delete an episode from the manifest."""
        if ep_id in self.manifest:
            del self.manifest[ep_id]
            self.save()

    def delete_show(self, show_id: str):
        """Delete an entire show and all its episodes."""
        to_del = [ep_id for ep_id, item in self.manifest.items() if item.get("show_id") == show_id]
        for ep_id in to_del:
            del self.manifest[ep_id]
        self.save()
