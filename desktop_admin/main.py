"""
Animew Pro & DramaFlixHD Desktop Admin Suite
Main Window & Application Entry Point (PyQt5 + WebEngine)
"""

import os
import sys

# Ensure desktop_admin directory is on python sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon, QFontDatabase

from styles.dark_theme import DARK_THEME_QSS
from core.manifest_bridge import ManifestBridge
from ui.drama_manager import DramaManagerWidget
from ui.backup_controller import BackupControllerWidget
from ui.bot_controller import BotControllerWidget
from ui.mobile_simulator import MobileSimulatorWidget
from ui.vip_manager import VipManagerWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Animew Pro & DramaFlixHD - Desktop Admin Suite v3.0")
        self.resize(1380, 890)
        self.setMinimumSize(1150, 750)

        # Initialize core data bridge
        self.bridge = ManifestBridge(WORKSPACE_DIR)

        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Sidebar Navigation
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(14, 22, 14, 22)
        side_layout.setSpacing(10)

        # Brand Header Logo
        brand_box = QHBoxLayout()
        logo_icon = QLabel("🎬")
        logo_icon.setFont(QFont("Outfit", 24))
        logo_icon.setStyleSheet("background: linear-gradient(135deg, #6366f1, #06b6d4); padding: 4px; border-radius: 10px;")
        brand_box.addWidget(logo_icon)

        title_vbox = QVBoxLayout()
        title_lbl = QLabel("DramaFlixHD")
        title_lbl.setObjectName("brandTitle")
        title_lbl.setFont(QFont("Outfit", 16, QFont.Bold))
        sub_lbl = QLabel("DESKTOP ADMIN v3.0")
        sub_lbl.setObjectName("brandSub")
        sub_lbl.setFont(QFont("Outfit", 8, QFont.Bold))
        title_vbox.addWidget(title_lbl)
        title_vbox.addWidget(sub_lbl)
        brand_box.addLayout(title_vbox)

        side_layout.addLayout(brand_box)
        side_layout.addSpacing(18)

        # Navigation Buttons
        self.nav_buttons = []

        nav_items = [
            ("🎬  គ្រប់គ្រងរឿង (Catalog)", 0),
            ("⚡  Backup Engine", 1),
            ("🤖  Bot & Vercel Deploy", 2),
            ("📱  Mobile Simulator", 3),
            ("👑  VIP & Google Sheets", 4),
        ]

        for text, index in nav_items:
            btn = QPushButton(text)
            btn.setProperty("class", "nav-btn")
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.clicked.connect(lambda _, idx=index: self.switch_tab(idx))
            side_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        side_layout.addStretch()

        # Workspace path indicator at bottom of sidebar
        ws_card = QFrame()
        ws_card.setStyleSheet("background-color: #070b14; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 8px;")
        ws_layout = QVBoxLayout(ws_card)
        ws_layout.setContentsMargins(6, 6, 6, 6)
        
        ws_title = QLabel("📁 Workspace")
        ws_title.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 11px;")
        ws_info = QLabel(os.path.basename(WORKSPACE_DIR))
        ws_info.setStyleSheet("color: #94a3b8; font-size: 11px;")
        ws_layout.addWidget(ws_title)
        ws_layout.addWidget(ws_info)
        
        side_layout.addWidget(ws_card)

        root_layout.addWidget(sidebar)

        # 2. Right Main Content Area
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Top Header Bar
        top_header = QFrame()
        top_header.setStyleSheet("background-color: #0b1120; border-bottom: 1px solid rgba(255,255,255,0.06);")
        top_layout = QHBoxLayout(top_header)
        top_layout.setContentsMargins(20, 12, 20, 12)

        self.lbl_page_title = QLabel("🎬 គ្រប់គ្រងរឿង & ភាគ (Drama Catalog Manager)")
        self.lbl_page_title.setFont(QFont("Outfit", 13, QFont.Bold))
        top_layout.addWidget(self.lbl_page_title)

        top_layout.addStretch()

        # Live Stats Chips
        self.chip_dramas = QLabel(f"📚 {len(self.bridge.dramas)} Shows")
        self.chip_dramas.setProperty("class", "badge")
        top_layout.addWidget(self.chip_dramas)

        self.chip_eps = QLabel(f"📺 {len(self.bridge.manifest)} Episodes")
        self.chip_eps.setProperty("class", "badge badge-green")
        top_layout.addWidget(self.chip_eps)

        self.chip_sync = QLabel("🟢 Database Synced")
        self.chip_sync.setProperty("class", "badge badge-purple")
        top_layout.addWidget(self.chip_sync)

        right_layout.addWidget(top_header)

        # Stacked Pages
        self.stack = QStackedWidget()
        
        self.tab_drama = DramaManagerWidget(self.bridge)
        self.tab_backup = BackupControllerWidget(WORKSPACE_DIR)
        self.tab_bot = BotControllerWidget(WORKSPACE_DIR)
        self.tab_simulator = MobileSimulatorWidget(WORKSPACE_DIR)
        self.tab_vip = VipManagerWidget(WORKSPACE_DIR)

        self.stack.addWidget(self.tab_drama)
        self.stack.addWidget(self.tab_backup)
        self.stack.addWidget(self.tab_bot)
        self.stack.addWidget(self.tab_simulator)
        self.stack.addWidget(self.tab_vip)

        right_layout.addWidget(self.stack)
        root_layout.addWidget(right_container)

        # Default select first tab
        self.switch_tab(0)

    def switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

        titles = [
            "🎬 គ្រប់គ្រងរឿង & ភាគ (Drama Catalog Manager)",
            "⚡ បញ្ជាដំណើរការ Auto Backup Engine ទៅ Telegram",
            "🤖 គ្រប់គ្រង Telegram Bot & Vercel Cloud Deployment",
            "📱 ផ្ទាំង Mobile Mini App Simulator (Live Preview)",
            "👑 គ្រប់គ្រងសមាជិក VIP & Google Sheets Dashboard"
        ]
        self.lbl_page_title.setText(titles[index])
        self.update_stats_chips()

    def update_stats_chips(self):
        self.chip_dramas.setText(f"📚 {len(self.bridge.dramas)} Shows")
        self.chip_eps.setText(f"📺 {len(self.bridge.manifest)} Episodes")

def load_embedded_khmer_fonts():
    """Load bundled Khmer fonts into QFontDatabase."""
    fonts_dir = os.path.join(BASE_DIR, "fonts")
    loaded_families = []
    if os.path.isdir(fonts_dir):
        for f in os.listdir(fonts_dir):
            if f.lower().endswith((".ttf", ".otf")):
                font_path = os.path.join(fonts_dir, f)
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    loaded_families.extend(families)
    
    # Priority Khmer font list
    for preferred in ["Kantumruy Pro", "Battambang", "Siemreap", "Leelawadee UI", "Khmer UI"]:
        if preferred in loaded_families or preferred in QFontDatabase().families():
            default_font = QFont(preferred, 10)
            default_font.setStyleHint(QFont.SansSerif)
            return default_font
    return QFont("Segoe UI", 10)

def main():
    app = QApplication(sys.argv)
    
    # Apply crisp embedded Khmer typography
    app_font = load_embedded_khmer_fonts()
    app.setFont(app_font)
    
    app.setStyleSheet(DARK_THEME_QSS)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
