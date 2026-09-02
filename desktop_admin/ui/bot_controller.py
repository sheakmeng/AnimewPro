"""
Telegram Bot Manager & Vercel Cloud Deployment Tab for Desktop Admin Suite.
"""

import os
import requests
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QPlainTextEdit, QFrame, QMessageBox, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor
from core.process_runner import ProcessRunner

class BotControllerWidget(QWidget):
    def __init__(self, workspace_dir: str, parent=None):
        super().__init__(parent)
        self.workspace_dir = workspace_dir
        self.bot_runner = ProcessRunner(self)
        self.deploy_runner = ProcessRunner(self)
        
        self.bot_runner.output_received.connect(self.append_bot_log)
        self.bot_runner.started.connect(self.on_bot_started)
        self.bot_runner.finished.connect(self.on_bot_finished)

        self.deploy_runner.output_received.connect(self.append_deploy_log)
        self.deploy_runner.started.connect(self.on_deploy_started)
        self.deploy_runner.finished.connect(self.on_deploy_finished)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # 1. Telegram Bot Section Card
        bot_card = QFrame()
        bot_card.setProperty("class", "card")
        bot_layout = QVBoxLayout(bot_card)
        bot_layout.setSpacing(10)

        bot_head = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_bot = QLabel("🤖 Telegram Mini App Bot Controller")
        lbl_bot.setFont(QFont("Outfit", 13, QFont.Bold))
        lbl_bot_sub = QLabel("Manage background Telegram Bot polling, welcome messages, and Mini App menu buttons.")
        lbl_bot_sub.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(lbl_bot)
        title_box.addWidget(lbl_bot_sub)
        bot_head.addLayout(title_box, 3)

        self.bot_status = QLabel("🔴 Stopped")
        self.bot_status.setProperty("class", "badge")
        self.bot_status.setAlignment(Qt.AlignCenter)
        self.bot_status.setFixedWidth(110)
        bot_head.addWidget(self.bot_status, 1)

        bot_layout.addLayout(bot_head)

        # Bot Actions Row
        bot_actions = QHBoxLayout()
        self.btn_start_bot = QPushButton("▶️ Start Bot")
        self.btn_start_bot.setProperty("class", "btn-success")
        self.btn_start_bot.clicked.connect(self.start_bot)
        bot_actions.addWidget(self.btn_start_bot)

        self.btn_stop_bot = QPushButton("⏹️ Stop Bot")
        self.btn_stop_bot.setProperty("class", "btn-danger")
        self.btn_stop_bot.setEnabled(False)
        self.btn_stop_bot.clicked.connect(self.stop_bot)
        bot_actions.addWidget(self.btn_stop_bot)

        self.btn_set_menu = QPushButton("🔗 Set Mini App Menu Button")
        self.btn_set_menu.setProperty("class", "btn-cyan")
        self.btn_set_menu.clicked.connect(self.set_menu_button)
        bot_actions.addWidget(self.btn_set_menu)

        bot_layout.addLayout(bot_actions)
        layout.addWidget(bot_card)

        # 2. Cloud Deployment & Git Sync Card
        deploy_card = QFrame()
        deploy_card.setProperty("class", "card")
        deploy_layout = QVBoxLayout(deploy_card)
        deploy_layout.setSpacing(10)

        lbl_deploy = QLabel("☁️ Cloud Deployment & Git Synchronization")
        lbl_deploy.setFont(QFont("Outfit", 13, QFont.Bold))
        deploy_layout.addWidget(lbl_deploy)

        deploy_grid = QGridLayout()
        self.btn_vercel = QPushButton("🚀 1-Click Deploy to Vercel Production")
        self.btn_vercel.setProperty("class", "btn-primary")
        self.btn_vercel.clicked.connect(self.deploy_vercel)
        deploy_grid.addWidget(self.btn_vercel, 0, 0)

        self.btn_git = QPushButton("📦 1-Click Git Commit & Push")
        self.btn_git.setProperty("class", "btn-cyan")
        self.btn_git.clicked.connect(self.git_push)
        deploy_grid.addWidget(self.btn_git, 0, 1)

        deploy_layout.addLayout(deploy_grid)
        layout.addWidget(deploy_card)

        # 3. Live Console / Deploy Logs Card
        log_card = QFrame()
        log_card.setProperty("class", "card")
        log_layout = QVBoxLayout(log_card)

        lbl_log = QLabel("📟 System & Deployment Logs")
        lbl_log.setFont(QFont("Outfit", 11, QFont.Bold))
        log_layout.addWidget(lbl_log)

        self.console = QPlainTextEdit()
        self.console.setProperty("class", "terminal-box")
        self.console.setReadOnly(True)
        log_layout.addWidget(self.console)

        layout.addWidget(log_card)

    def start_bot(self):
        script = os.path.join(self.workspace_dir, "bot_miniapp.py")
        if not os.path.isfile(script):
            QMessageBox.critical(self, "Error", f"Script not found: {script}")
            return
        self.console.appendPlainText("🚀 Starting Telegram Bot daemon in background...")
        self.bot_runner.start_python_script(script, cwd=self.workspace_dir)

    def stop_bot(self):
        self.bot_runner.stop()
        self.console.appendPlainText("🛑 Telegram Bot daemon stopped.")
        self.bot_status.setText("🔴 Stopped")
        self.bot_status.setProperty("class", "badge")
        self.bot_status.style().unpolish(self.bot_status)
        self.bot_status.style().polish(self.bot_status)
        self.btn_start_bot.setEnabled(True)
        self.btn_stop_bot.setEnabled(False)

    def on_bot_started(self):
        self.bot_status.setText("🟢 Online")
        self.bot_status.setProperty("class", "badge badge-green")
        self.bot_status.style().unpolish(self.bot_status)
        self.bot_status.style().polish(self.bot_status)
        self.btn_start_bot.setEnabled(False)
        self.btn_stop_bot.setEnabled(True)

    def on_bot_finished(self, code):
        self.bot_status.setText("🔴 Stopped")
        self.bot_status.setProperty("class", "badge")
        self.bot_status.style().unpolish(self.bot_status)
        self.bot_status.style().polish(self.bot_status)
        self.btn_start_bot.setEnabled(True)
        self.btn_stop_bot.setEnabled(False)

    def set_menu_button(self):
        bot_token = "8664822430:AAFW9z9BL1KLt-_tYypVM4zqnWWBmoXkzuw"
        url = f"https://api.telegram.org/bot{bot_token}/setChatMenuButton"
        payload = {
            "menu_button": {
                "type": "web_app",
                "text": "🎬 DramaFlixHD",
                "web_app": {
                    "url": "https://animewpro.vercel.app/"
                }
            }
        }
        try:
            r = requests.post(url, json=payload, timeout=10)
            res = r.json()
            if res.get("ok"):
                self.console.appendPlainText("✅ [SUCCESS] Telegram Menu Button set to https://animewpro.vercel.app/!")
                QMessageBox.information(self, "Success", "Telegram Menu Button updated successfully!")
            else:
                self.console.appendPlainText(f"⚠️ [WARN] Telegram API response: {res}")
        except Exception as e:
            self.console.appendPlainText(f"❌ [ERROR] Failed to set menu button: {e}")

    def deploy_vercel(self):
        self.console.appendPlainText("🚀 [VERCEL] Initiating Vercel Production Build & Deploy...")
        self.deploy_runner.start_command("npx", ["vercel", "--prod", "--yes"], cwd=self.workspace_dir)

    def git_push(self):
        self.console.appendPlainText("📦 [GIT] Running Git Add, Commit & Push...")
        # Execute via powershell
        cmd = 'git add . ; git commit -m "update: admin desktop sync" ; git push'
        self.deploy_runner.start_command("powershell", ["-Command", cmd], cwd=self.workspace_dir)

    def on_deploy_started(self):
        self.btn_vercel.setEnabled(False)
        self.btn_git.setEnabled(False)

    def on_deploy_finished(self, code):
        self.btn_vercel.setEnabled(True)
        self.btn_git.setEnabled(True)
        if code == 0:
            self.console.appendPlainText("🎉 [DEPLOY] Operation completed successfully!")
        else:
            self.console.appendPlainText(f"⚠️ [DEPLOY] Operation ended with code {code}")

    def append_bot_log(self, text):
        self.console.moveCursor(QTextCursor.End)
        self.console.insertPlainText(f"[BOT] {text}")
        self.console.moveCursor(QTextCursor.End)

    def append_deploy_log(self, text):
        self.console.moveCursor(QTextCursor.End)
        self.console.insertPlainText(text)
        self.console.moveCursor(QTextCursor.End)
