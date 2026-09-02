"""
Drama & Episode Catalog Management Tab for Desktop Admin Suite.
Polished UX with rich typography, table header fixes, and clean Khmer layout.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QTextEdit,
    QComboBox, QMessageBox, QFrame, QInputDialog, QAbstractItemView
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QColor, QFont
import requests

class DramaManagerWidget(QWidget):
    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.current_show_id = None
        self.init_ui()
        self.load_drama_table()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # 1. Top Search & Filter Bar
        top_card = QFrame()
        top_card.setProperty("class", "card")
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(12, 10, 12, 10)
        top_layout.setSpacing(10)

        # Search Input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 ស្វែងរកឈ្មោះរឿង ឬ Show ID (Search title or ID)...")
        self.search_input.textChanged.connect(self.filter_dramas)
        top_layout.addWidget(self.search_input, 4)

        # Platform & Category Filter Dropdown
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "🌐 គ្រប់ប្រភេទ (All Categories)",
            "🟣 Dramaora",
            "🔵 DramaBite",
            "🇨🇳 រឿងភាគចិន (Chinese)",
            "🇰🇷 រឿងភាគកូរ៉េ (Korean)",
            "👑 VIP ផ្តាច់មុខ (VIP Only)",
            "🔥 ពេញនិយម (Trending)",
            "❤️ ស្នេហា / CEO (Romance)",
            "⚔️ សកម្មភាព (Action)"
        ])
        self.filter_combo.currentIndexChanged.connect(self.filter_dramas)
        top_layout.addWidget(self.filter_combo, 2)

        # Refresh Button
        self.btn_reload = QPushButton("🔄 Refresh")
        self.btn_reload.clicked.connect(self.reload_all)
        top_layout.addWidget(self.btn_reload)

        # Add New Drama Button
        self.btn_add_drama = QPushButton("➕ បន្ថែមរឿងថ្មី (Add Drama)")
        self.btn_add_drama.setProperty("class", "btn-primary")
        self.btn_add_drama.clicked.connect(self.add_new_drama_dialog)
        top_layout.addWidget(self.btn_add_drama)

        main_layout.addWidget(top_card)

        # 2. Main Horizontal Splitter (Left: Table, Right: Inspector)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(8)

        # Left Panel (Drama Catalog Table)
        left_panel = QFrame()
        left_panel.setProperty("class", "card")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)

        lbl_list = QLabel("📚 បញ្ជីរឿងទាំងអស់ (Drama Catalog)")
        lbl_list.setFont(QFont("Outfit", 12, QFont.Bold))
        left_layout.addWidget(lbl_list)

        self.drama_table = QTableWidget()
        self.drama_table.setColumnCount(4)
        self.drama_table.setHorizontalHeaderLabels(["ចំណងជើងរឿង (Drama Title)", "ប្រភព (Source)", "ភាគ (Eps)", "Show ID"])
        self.drama_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.drama_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.drama_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.drama_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.drama_table.verticalHeader().setVisible(False)  # Hide ugly 1,2,3 row numbers
        self.drama_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.drama_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.drama_table.itemSelectionChanged.connect(self.on_drama_selected)
        left_layout.addWidget(self.drama_table)

        splitter.addWidget(left_panel)

        # Right Panel (Show Inspector & Episode Editor)
        right_panel = QFrame()
        right_panel.setProperty("class", "card")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(10)

        lbl_details = QLabel("🎬 ព័ត៌មានលម្អិត & កែសម្រួលភាគ (Show Inspector)")
        lbl_details.setFont(QFont("Outfit", 12, QFont.Bold))
        right_layout.addWidget(lbl_details)

        # Show Metadata Card Box
        meta_card = QFrame()
        meta_card.setStyleSheet("background-color: #090e1a; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 10px;")
        meta_layout = QHBoxLayout(meta_card)
        meta_layout.setSpacing(14)
        
        # Left Inputs
        input_layout = QVBoxLayout()
        input_layout.setSpacing(6)

        lbl_t = QLabel("ចំណងជើងរឿង (Show Title):")
        lbl_t.setStyleSheet("font-weight: 700; color: #94a3b8; font-size: 11.5px;")
        self.input_title = QLineEdit()
        self.input_title.setPlaceholderText("Enter Drama Title...")
        input_layout.addWidget(lbl_t)
        input_layout.addWidget(self.input_title)

        lbl_p = QLabel("រូបភាព Poster URL:")
        lbl_p.setStyleSheet("font-weight: 700; color: #94a3b8; font-size: 11.5px;")
        self.input_poster = QLineEdit()
        self.input_poster.setPlaceholderText("https://... (Image link)")
        self.input_poster.textChanged.connect(self.preview_poster)
        input_layout.addWidget(lbl_p)
        input_layout.addWidget(self.input_poster)

        lbl_c = QLabel("ប្រភេទរឿង / Category Tab:")
        lbl_c.setStyleSheet("font-weight: 700; color: #94a3b8; font-size: 11.5px;")
        self.input_category = QComboBox()
        self.input_category.addItems([
            "🎬 Dramaora",
            "⚡ DramaBite",
            "🇨🇳 រឿងភាគចិន (Chinese)",
            "🇰🇷 រឿងភាគកូរ៉េ (Korean)",
            "👑 VIP ផ្តាច់មុខ (VIP Only)",
            "🔥 ពេញនិយម (Trending)",
            "❤️ ស្នេហា / CEO (Romance)",
            "⚔️ សកម្មភាព (Action)"
        ])
        input_layout.addWidget(lbl_c)
        input_layout.addWidget(self.input_category)

        lbl_s = QLabel("សង្ខេបរឿង (Synopsis):")
        lbl_s.setStyleSheet("font-weight: 700; color: #94a3b8; font-size: 11.5px;")
        self.input_synopsis = QTextEdit()
        self.input_synopsis.setPlaceholderText("Synopsis / Story Description...")
        self.input_synopsis.setMaximumHeight(55)
        input_layout.addWidget(lbl_s)
        input_layout.addWidget(self.input_synopsis)

        meta_layout.addLayout(input_layout, 3)

        # Poster Image Preview Box
        poster_vbox = QVBoxLayout()
        poster_vbox.setAlignment(Qt.AlignCenter)
        self.poster_preview = QLabel("No Poster")
        self.poster_preview.setFixedSize(100, 145)
        self.poster_preview.setAlignment(Qt.AlignCenter)
        self.poster_preview.setStyleSheet("""
            QLabel {
                border: 2px solid rgba(56, 189, 248, 0.3);
                border-radius: 10px;
                background-color: #050811;
                color: #64748b;
                font-size: 11px;
            }
        """)
        poster_vbox.addWidget(self.poster_preview)
        meta_layout.addLayout(poster_vbox, 1)

        right_layout.addWidget(meta_card)

        # Action Buttons Row
        show_btn_row = QHBoxLayout()
        self.btn_save_show = QPushButton("💾 រក្សាទុកទិន្នន័យ (Save Metadata)")
        self.btn_save_show.setProperty("class", "btn-primary")
        self.btn_save_show.clicked.connect(self.save_show_metadata)
        show_btn_row.addWidget(self.btn_save_show, 2)

        self.btn_delete_show = QPushButton("🗑️ លុបរឿងចោល (Delete Drama)")
        self.btn_delete_show.setProperty("class", "btn-danger")
        self.btn_delete_show.clicked.connect(self.delete_current_show)
        show_btn_row.addWidget(self.btn_delete_show, 1)

        right_layout.addLayout(show_btn_row)

        # Episodes Section Header
        ep_head = QHBoxLayout()
        lbl_eps = QLabel("📺 បញ្ជីភាគវីដេអូ (Episodes)")
        lbl_eps.setFont(QFont("Outfit", 11, QFont.Bold))
        ep_head.addWidget(lbl_eps)

        self.btn_add_ep = QPushButton("➕ បន្ថែមភាគថ្មី (Add Episode)")
        self.btn_add_ep.setProperty("class", "btn-cyan")
        self.btn_add_ep.clicked.connect(self.add_episode_dialog)
        ep_head.addWidget(self.btn_add_ep)

        right_layout.addLayout(ep_head)

        # Episodes Table
        self.ep_table = QTableWidget()
        self.ep_table.setColumnCount(4)
        self.ep_table.setHorizontalHeaderLabels(["ភាគ (EP)", "🔗 Stream Video URL", "ទំហំ (Size)", "លុប (Action)"])
        self.ep_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.ep_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.ep_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.ep_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.ep_table.verticalHeader().setVisible(False)
        self.ep_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        right_layout.addWidget(self.ep_table)

        splitter.addWidget(right_panel)
        splitter.setSizes([450, 600])
        main_layout.addWidget(splitter)

    def reload_all(self):
        self.bridge.load()
        self.load_drama_table()

    def load_drama_table(self):
        self.drama_table.setRowCount(0)
        search = self.search_input.text().lower().strip()
        filter_type = self.filter_combo.currentText()

        dramas = list(self.bridge.dramas.values())
        row = 0
        for s in dramas:
            title = s.get("title", "")
            s_id = s.get("id", "")
            source = s.get("source", "")

            # Filter search
            if search and (search not in title.lower() and search not in s_id.lower()):
                continue

            # Filter source & category
            cat_val = s.get("category", "").lower()
            if "DramaBite" in filter_type and "dramabite" not in source.lower() and "dramabite" not in cat_val:
                continue
            if "Dramaora" in filter_type and "dramaora" not in source.lower() and "dramaora" not in cat_val:
                continue
            if "VIP" in filter_type and not s.get("is_vip") and "vip" not in cat_val:
                continue
            if "Chinese" in filter_type and "chinese" not in cat_val and "ចិន" not in cat_val:
                continue
            if "Korean" in filter_type and "korean" not in cat_val and "កូរ៉េ" not in cat_val:
                continue
            if "Romance" in filter_type and "romance" not in cat_val and "ស្នេហា" not in cat_val and "ceo" not in cat_val:
                continue
            if "Action" in filter_type and "action" not in cat_val and "សកម្មភាព" not in cat_val and "ក្បាច់គុន" not in cat_val:
                continue
            if "Trending" in filter_type and "trending" not in cat_val and "ពេញនិយម" not in cat_val:
                continue

            self.drama_table.insertRow(row)
            
            # Column 0: Title
            item_title = QTableWidgetItem(f"  🎬 {title}")
            item_title.setFont(QFont("Outfit", 11, QFont.Bold))
            item_title.setData(Qt.UserRole, s_id)
            self.drama_table.setItem(row, 0, item_title)

            # Column 1: Source
            is_bite = "dramabite" in source.lower()
            src_name = "🔵 DramaBite" if is_bite else "🟣 Dramaora"
            item_src = QTableWidgetItem(src_name)
            item_src.setTextAlignment(Qt.AlignCenter)
            item_src.setForeground(QColor("#38bdf8" if is_bite else "#c084fc"))
            self.drama_table.setItem(row, 1, item_src)

            # Column 2: Ep count
            ep_count = len(s.get("episodes", []))
            item_eps = QTableWidgetItem(f"{ep_count} ភាគ")
            item_eps.setTextAlignment(Qt.AlignCenter)
            item_eps.setFont(QFont("Outfit", 10, QFont.Bold))
            self.drama_table.setItem(row, 2, item_eps)

            # Column 3: ID
            item_id = QTableWidgetItem(s_id)
            item_id.setForeground(QColor("#64748b"))
            self.drama_table.setItem(row, 3, item_id)

            row += 1

        if self.drama_table.rowCount() > 0:
            self.drama_table.selectRow(0)

    def filter_dramas(self):
        self.load_drama_table()

    def on_drama_selected(self):
        selected_rows = self.drama_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        item = self.drama_table.item(row, 0)
        if not item:
            return
        show_id = item.data(Qt.UserRole)
        self.current_show_id = show_id
        self.populate_show_details(show_id)

    def populate_show_details(self, show_id):
        show = self.bridge.dramas.get(show_id)
        if not show:
            return

        self.input_title.setText(show.get("title", ""))
        self.input_poster.setText(show.get("poster_url", ""))
        self.input_synopsis.setPlainText(show.get("synopsis", ""))
        
        # Load category
        cat = show.get("category", "")
        if cat:
            for idx in range(self.input_category.count()):
                if cat.lower() in self.input_category.itemText(idx).lower() or self.input_category.itemText(idx).lower() in cat.lower():
                    self.input_category.setCurrentIndex(idx)
                    break
        else:
            is_bite = "dramabite" in show.get("source", "").lower()
            self.input_category.setCurrentIndex(1 if is_bite else 0)

        self.preview_poster(show.get("poster_url", ""))

        # Populate episodes
        self.ep_table.setRowCount(0)
        episodes = show.get("episodes", [])
        for r_idx, ep in enumerate(episodes):
            self.ep_table.insertRow(r_idx)
            
            # EP #
            ep_num = ep.get("episode_number", r_idx + 1)
            item_ep = QTableWidgetItem(f"EP {ep_num:02d}")
            item_ep.setTextAlignment(Qt.AlignCenter)
            item_ep.setFont(QFont("Outfit", 10, QFont.Bold))
            item_ep.setData(Qt.UserRole, ep.get("id"))
            self.ep_table.setItem(r_idx, 0, item_ep)

            # Stream URL
            url = ep.get("original_url") or ep.get("hls_source_url") or ""
            item_url = QTableWidgetItem(url)
            self.ep_table.setItem(r_idx, 1, item_url)

            # Size
            size_mb = ep.get("file_size_mb") or 0
            size_str = f"{size_mb:.1f} MB" if size_mb else "-"
            item_size = QTableWidgetItem(size_str)
            item_size.setTextAlignment(Qt.AlignCenter)
            item_size.setForeground(QColor("#94a3b8"))
            self.ep_table.setItem(r_idx, 2, item_size)

            # Action button
            btn_del = QPushButton("🗑️")
            btn_del.setFixedWidth(40)
            btn_del.setProperty("class", "btn-danger")
            ep_id = ep.get("id")
            btn_del.clicked.connect(lambda _, eid=ep_id: self.delete_episode(eid))
            self.ep_table.setCellWidget(r_idx, 3, btn_del)

    def preview_poster(self, url):
        url = url.strip()
        if not url or not url.startswith("http"):
            self.poster_preview.setText("No Poster")
            return
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(r.content)
                self.poster_preview.setPixmap(pixmap.scaled(100, 145, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            self.poster_preview.setText("Image Err")

    def save_show_metadata(self):
        if not self.current_show_id:
            return
        title = self.input_title.text().strip()
        poster = self.input_poster.text().strip()
        synopsis = self.input_synopsis.toPlainText().strip()
        category = self.input_category.currentText().strip()
        self.bridge.update_show_metadata(self.current_show_id, title, poster, synopsis, category)
        QMessageBox.information(self, "ជោគជ័យ", "✅ បានរក្សាទុកទិន្នន័យ និង Sync ចូល data.js រួចរាល់!")
        self.load_drama_table()

    def delete_current_show(self):
        if not self.current_show_id:
            return
        res = QMessageBox.question(self, "បញ្ជាក់ការលុប", f"តើអ្នកប្រាកដជាចង់លុបរឿងនេះ និងភាគទាំងអស់ចោលមែនទេ?",
                                   QMessageBox.Yes | QMessageBox.No)
        if res == QMessageBox.Yes:
            self.bridge.delete_show(self.current_show_id)
            self.load_drama_table()
            QMessageBox.information(self, "បានលុប", "រឿងត្រូវបានលុបដោយជោគជ័យ!")

    def add_new_drama_dialog(self):
        title, ok = QInputDialog.getText(self, "បន្ថែមរឿងថ្មី", "បញ្ចូលចំណងជើងរឿង (Drama Title):")
        if ok and title.strip():
            s_id = "dramaora_" + "".join(c for c in title.lower().replace(" ", "_") if c.isalnum() or c == "_")
            ep_url, ok2 = QInputDialog.getText(self, "Link វីដេអូភាគ ១", "បញ្ចូល Link វីដេអូភាគ ១ (MP4 / M3U8):")
            if ok2 and ep_url.strip():
                self.bridge.add_custom_episode(s_id, title.strip(), 1, ep_url.strip())
                self.load_drama_table()
                QMessageBox.information(self, "ជោគជ័យ", "🎉 បានបន្ថែមរឿងថ្មីដោយជោគជ័យ!")

    def add_episode_dialog(self):
        if not self.current_show_id:
            return
        show = self.bridge.dramas.get(self.current_show_id)
        next_ep = len(show.get("episodes", [])) + 1
        url, ok = QInputDialog.getText(self, f"បន្ថែមភាគ {next_ep}", f"បញ្ចូល Stream URL សម្រាប់ភាគ {next_ep}:")
        if ok and url.strip():
            self.bridge.add_custom_episode(self.current_show_id, show.get("title", ""), next_ep, url.strip(), show.get("poster_url", ""))
            self.populate_show_details(self.current_show_id)
            QMessageBox.information(self, "ជោគជ័យ", f"✅ បានបន្ថែមភាគ {next_ep} រួចរាល់!")

    def delete_episode(self, ep_id):
        res = QMessageBox.question(self, "បញ្ជាក់", "តើចង់លុបភាគនេះចោលមែនទេ?", QMessageBox.Yes | QMessageBox.No)
        if res == QMessageBox.Yes:
            self.bridge.delete_episode(ep_id)
            self.populate_show_details(self.current_show_id)
