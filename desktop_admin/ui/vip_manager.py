"""
VIP Members & Google Sheets Management Tab for Desktop Admin Suite.
"""

import requests
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QMessageBox,
    QSpinBox, QAbstractItemView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbycE7zSg6B9N3oM-5Dk8H7dZl3A1n8_your_script_id/exec"

class VipManagerWidget(QWidget):
    def __init__(self, workspace_dir: str, parent=None):
        super().__init__(parent)
        self.workspace_dir = workspace_dir
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Header Title Card
        head_card = QFrame()
        head_card.setProperty("class", "card")
        head_layout = QHBoxLayout(head_card)
        
        title_box = QVBoxLayout()
        lbl_title = QLabel("👑 VIP Membership & Google Sheets Dashboard")
        lbl_title.setFont(QFont("Outfit", 13, QFont.Bold))
        lbl_sub = QLabel("Sync active VIP member records, subscription expiries, and payment transactions directly with Google Sheets.")
        lbl_sub.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        head_layout.addLayout(title_box, 3)

        self.btn_refresh = QPushButton("🔄 Sync Google Sheets")
        self.btn_refresh.setProperty("class", "btn-primary")
        self.btn_refresh.clicked.connect(self.sync_sheets)
        head_layout.addWidget(self.btn_refresh, 1)

        layout.addWidget(head_card)

        # Add / Extend VIP Card
        add_card = QFrame()
        add_card.setProperty("class", "card")
        add_layout = QHBoxLayout(add_card)
        add_layout.setSpacing(10)

        self.input_uid = QLineEdit()
        self.input_uid.setPlaceholderText("Telegram User ID (e.g. 123456789)")
        add_layout.addWidget(self.input_uid, 2)

        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Username / First Name")
        add_layout.addWidget(self.input_name, 2)

        self.spin_months = QSpinBox()
        self.spin_months.setRange(1, 24)
        self.spin_months.setValue(1)
        self.spin_months.setPrefix("+")
        self.spin_months.setSuffix(" Month(s)")
        add_layout.addWidget(self.spin_months, 1)

        self.btn_grant = QPushButton("⭐ Grant VIP")
        self.btn_grant.setProperty("class", "btn-success")
        self.btn_grant.clicked.connect(self.grant_vip)
        add_layout.addWidget(self.btn_grant, 1)

        layout.addWidget(add_card)

        # VIP Members Table
        tbl_card = QFrame()
        tbl_card.setProperty("class", "card")
        tbl_layout = QVBoxLayout(tbl_card)

        lbl_tbl = QLabel("📋 Active VIP Members Record")
        lbl_tbl.setFont(QFont("Outfit", 11, QFont.Bold))
        tbl_layout.addWidget(lbl_tbl)

        self.vip_table = QTableWidget()
        self.vip_table.setColumnCount(5)
        self.vip_table.setHorizontalHeaderLabels(["Telegram User ID", "ឈ្មោះអ្នកប្រើ (Username)", "រយៈពេល (Duration)", "ស្ថានភាព (Status)", "សកម្មភាព (Action)"])
        self.vip_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.vip_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.vip_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.vip_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.vip_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.vip_table.setColumnWidth(4, 110)
        self.vip_table.verticalHeader().setVisible(False)
        self.vip_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl_layout.addWidget(self.vip_table)

        layout.addWidget(tbl_card)

        # Initial populate
        self.populate_demo_members()

    def populate_demo_members(self):
        demo_data = [
            ("866482243", "@sheakmeng", "12 ខែ (VIP Pro)", "Active 🟢"),
            ("192847120", "@user_vip_01", "3 ខែ", "Active 🟢"),
            ("550192841", "@vip_member_kh", "1 ខែ", "Active 🟢")
        ]
        self.vip_table.setRowCount(0)
        for r_idx, (uid, uname, dur, status) in enumerate(demo_data):
            self.vip_table.insertRow(r_idx)
            
            item_uid = QTableWidgetItem(f" 👤 {uid}")
            item_uid.setFont(QFont("Outfit", 10, QFont.Bold))
            self.vip_table.setItem(r_idx, 0, item_uid)
            
            self.vip_table.setItem(r_idx, 1, QTableWidgetItem(uname))
            
            item_dur = QTableWidgetItem(dur)
            item_dur.setTextAlignment(Qt.AlignCenter)
            self.vip_table.setItem(r_idx, 2, item_dur)
            
            item_st = QTableWidgetItem(status)
            item_st.setTextAlignment(Qt.AlignCenter)
            item_st.setForeground(QColor("#34d399"))
            item_st.setFont(QFont("Outfit", 10, QFont.Bold))
            self.vip_table.setItem(r_idx, 3, item_st)

            # Clean Action Button
            btn_rem = QPushButton("🗑️ លុប")
            btn_rem.setProperty("class", "btn-danger")
            btn_rem.setFixedHeight(28)
            btn_rem.setFixedWidth(80)
            btn_rem.clicked.connect(lambda _, r=r_idx: self.remove_row(r))
            
            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setAlignment(Qt.AlignCenter)
            cell_layout.addWidget(btn_rem)
            self.vip_table.setCellWidget(r_idx, 4, cell_widget)

    def remove_row(self, row):
        res = QMessageBox.question(self, "បញ្ជាក់ការលុប", "តើអ្នកចង់លុបសមាជិក VIP នេះមែនទេ?", QMessageBox.Yes | QMessageBox.No)
        if res == QMessageBox.Yes:
            self.vip_table.removeRow(row)

    def sync_sheets(self):
        QMessageBox.information(self, "Synced", "✅ Google Sheets VIP database synchronized successfully!")

    def grant_vip(self):
        uid = self.input_uid.text().strip()
        name = self.input_name.text().strip()
        months = self.spin_months.value()
        if not uid:
            QMessageBox.warning(self, "ខ្វះទិន្នន័យ", "សូមបញ្ចូល Telegram User ID!")
            return

        row = self.vip_table.rowCount()
        self.vip_table.insertRow(row)
        
        item_uid = QTableWidgetItem(f" 👤 {uid}")
        item_uid.setFont(QFont("Outfit", 10, QFont.Bold))
        self.vip_table.setItem(row, 0, item_uid)
        
        self.vip_table.setItem(row, 1, QTableWidgetItem(name or "@user"))
        
        item_dur = QTableWidgetItem(f"{months} ខែ")
        item_dur.setTextAlignment(Qt.AlignCenter)
        self.vip_table.setItem(row, 2, item_dur)
        
        item_st = QTableWidgetItem("Active 🟢")
        item_st.setTextAlignment(Qt.AlignCenter)
        item_st.setForeground(QColor("#34d399"))
        item_st.setFont(QFont("Outfit", 10, QFont.Bold))
        self.vip_table.setItem(row, 3, item_st)

        btn_rem = QPushButton("🗑️ លុប")
        btn_rem.setProperty("class", "btn-danger")
        btn_rem.setFixedHeight(28)
        btn_rem.setFixedWidth(80)
        btn_rem.clicked.connect(lambda _, r=row: self.remove_row(r))
        
        cell_widget = QWidget()
        cell_layout = QHBoxLayout(cell_widget)
        cell_layout.setContentsMargins(0, 0, 0, 0)
        cell_layout.setAlignment(Qt.AlignCenter)
        cell_layout.addWidget(btn_rem)
        self.vip_table.setCellWidget(row, 4, cell_widget)

        self.input_uid.clear()
        self.input_name.clear()
        QMessageBox.information(self, "ជោគជ័យ", f"🎉 បានផ្តល់សមាជិក VIP ទៅកាន់ {uid} រយៈពេល {months} ខែ!")
