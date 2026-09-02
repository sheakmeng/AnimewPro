"""
Embedded Mobile Mini App Simulator using PyQtWebEngine for Desktop Admin Suite.
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QFrame
)
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEngineSettings

class MobileSimulatorWidget(QWidget):
    def __init__(self, workspace_dir: str, parent=None):
        super().__init__(parent)
        self.workspace_dir = workspace_dir
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Control Bar
        control_bar = QHBoxLayout()
        
        lbl_device = QLabel("📱 Device Viewport:")
        lbl_device.setFont(QFont("Outfit", 10, QFont.Bold))
        control_bar.addWidget(lbl_device)

        self.device_combo = QComboBox()
        self.device_combo.addItems([
            "iPhone 15 Pro (393 x 852)",
            "Samsung Galaxy S24 (390 x 844)",
            "iPad Mini (768 x 1024)",
            "Responsive / Wide"
        ])
        self.device_combo.currentIndexChanged.connect(self.on_device_changed)
        control_bar.addWidget(self.device_combo)

        self.btn_live = QPushButton("🌐 Live Vercel")
        self.btn_live.clicked.connect(lambda: self.load_url("https://animewpro.vercel.app/"))
        control_bar.addWidget(self.btn_live)

        self.btn_local = QPushButton("💻 Local File")
        self.btn_local.clicked.connect(self.load_local)
        control_bar.addWidget(self.btn_local)

        self.btn_reload = QPushButton("🔄 Reload")
        self.btn_reload.clicked.connect(self.reload_view)
        control_bar.addWidget(self.btn_reload)

        control_bar.addStretch()
        layout.addLayout(control_bar)

        # Center Container for Mobile Phone Mock Frame
        self.center_box = QHBoxLayout()
        self.center_box.setAlignment(Qt.AlignCenter)

        self.phone_frame = QFrame()
        self.phone_frame.setStyleSheet("""
            QFrame {
                background: #000000;
                border: 4px solid #334155;
                border-radius: 28px;
                padding: 10px 4px 10px 4px;
            }
        """)
        
        phone_layout = QVBoxLayout(self.phone_frame)
        phone_layout.setContentsMargins(0, 0, 0, 0)

        # WebEngine View
        self.web_view = QWebEngineView()
        
        # Configure WebEngine settings
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
        settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)

        phone_layout.addWidget(self.web_view)

        # Default size: 393 x 852
        self.phone_frame.setFixedSize(405, 872)

        self.center_box.addWidget(self.phone_frame)
        layout.addLayout(self.center_box)

        # Initial Load: Live Vercel
        self.load_url("https://animewpro.vercel.app/")

    def on_device_changed(self, idx):
        if idx == 0: # iPhone 15 Pro
            self.phone_frame.setFixedSize(405, 872)
        elif idx == 1: # Samsung S24
            self.phone_frame.setFixedSize(402, 864)
        elif idx == 2: # iPad Mini
            self.phone_frame.setFixedSize(780, 1040)
        else: # Responsive
            self.phone_frame.setMinimumSize(400, 600)
            self.phone_frame.setMaximumSize(16777215, 16777215)

    def load_url(self, url: str):
        self.web_view.setUrl(QUrl(url))

    def load_local(self):
        local_path = os.path.join(self.workspace_dir, "index.html")
        if os.path.isfile(local_path):
            self.web_view.setUrl(QUrl.fromLocalFile(local_path))

    def reload_view(self):
        self.web_view.reload()
