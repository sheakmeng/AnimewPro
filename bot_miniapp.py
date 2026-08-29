"""
Telegram Mini App Bot for Animew Pro & Dramaora Stream
Bot Token: 8664822430:AAEPSmxJgq4CEAFp94869dhLGVEAcyScde8
Web App URL: https://sheakmeng.github.io/AnimewPro/
"""

import sys
import time
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BOT_TOKEN = "8664822430:AAEPSmxJgq4CEAFp94869dhLGVEAcyScde8"
MINI_APP_URL = "https://sheakmeng.github.io/AnimewPro/"
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

def setup_menu_button():
    """Sets the Telegram Chat Menu Button to open the Mini App directly"""
    url = f"{API_BASE}/setChatMenuButton"
    payload = {
        "menu_button": {
            "type": "web_app",
            "text": "🎬 បើកទស្សនារឿង",
            "web_app": {
                "url": MINI_APP_URL
            }
        }
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        res = r.json()
        if res.get("ok"):
            logging.info("✅ Menu Button set successfully to Mini App!")
        else:
            logging.warning(f"⚠️ Failed to set menu button: {res}")
    except Exception as e:
        logging.error(f"Error setting menu button: {e}")

def send_welcome_message(chat_id, user_first_name=""):
    """Sends a rich welcome card with a 1-click Web App button"""
    url = f"{API_BASE}/sendMessage"
    welcome_text = (
        f"👋 សួស្តី <b>{user_first_name or 'ប្រិយមិត្ត'}</b>!\n\n"
        "✨ សូមស្វាគមន៍មកកាន់ <b>Animew Pro & Dramaora Mini App</b>!\n"
        "🎬 អ្នកអាចទស្សនារឿងភាគខ្លីៗ និងរឿងពេញនិយមច្រើនជាង <b>395+ ភាគ</b> កម្រិតរូបភាព <b>1080p FHD</b> ដោយឥតគិតថ្លៃ ១០០% លើ Telegram។\n\n"
        "👇 <b>ចុចប៊ូតុងខាងក្រោមដើម្បីបើកមើលរឿងភ្លាមៗ៖</b>"
    )
    
    payload = {
        "chat_id": chat_id,
        "text": welcome_text,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": "🎬 បើកទស្សនារឿង (Open Mini App)",
                        "web_app": {
                            "url": MINI_APP_URL
                        }
                    }
                ],
                [
                    {
                        "text": "🔄 ចូលរួម Channel Update",
                        "url": "https://t.me/telegram"
                    }
                ]
            ]
        }
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f"Error sending welcome message: {e}")

def run_polling():
    """Runs long polling for the Bot"""
    logging.info("🚀 Starting Animew Pro Telegram Mini App Bot...")
    setup_menu_button()
    
    offset = 0
    while True:
        try:
            url = f"{API_BASE}/getUpdates?offset={offset}&timeout=30"
            r = requests.get(url, timeout=40)
            if r.status_code == 200:
                data = r.json()
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message")
                    if not msg:
                        continue
                    
                    chat_id = msg["chat"]["id"]
                    first_name = msg["from"].get("first_name", "")
                    text = msg.get("text", "")
                    
                    if text.startswith("/start") or text.startswith("/app"):
                        send_welcome_message(chat_id, first_name)
                    else:
                        send_welcome_message(chat_id, first_name)
            time.sleep(1)
        except Exception as e:
            logging.error(f"Polling loop error: {e}")
            time.sleep(3)

if __name__ == "__main__":
    run_polling()
