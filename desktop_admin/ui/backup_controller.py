"""
Backup Engine Controller Tab with Live Terminal Logs for Desktop Admin Suite.
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QPlainTextEdit, QFrame, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor
from core.process_runner import ProcessRunner

class BackupControllerWidget(QWidget):
    def __init__(self, workspace_dir: str, parent=None):
        super().__init__(parent)
        self.workspace_dir = workspace_dir
        self.runner = ProcessRunner(self)
        self.runner.output_received.connect(self.append_log)
        self.runner.started.connect(self.on_process_started)
        self.runner.finished.connect(self.on_process_finished)
        self.runner.error_occurred.connect(self.on_process_error)
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
        lbl_title = QLabel("⚡ Automated Backup Engine Controller")
        lbl_title.setFont(QFont("Outfit", 13, QFont.Bold))
        lbl_sub = QLabel("Run automated DramaBite Bypass & Dramaora cloud backup engines to Telegram with live terminal telemetry.")
        lbl_sub.setStyleSheet("color: #94a3b8; font-size: 12px;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        head_layout.addLayout(title_box, 3)

        self.status_badge = QLabel("⚪ Idle")
        self.status_badge.setProperty("class", "badge")
        self.status_badge.setAlignment(Qt.AlignCenter)
        self.status_badge.setFixedWidth(110)
        head_layout.addWidget(self.status_badge, 1)

        layout.addWidget(head_card)

        # Control Action Buttons Row
        btn_card = QFrame()
        btn_card.setProperty("class", "card")
        btn_layout = QHBoxLayout(btn_card)
        btn_layout.setSpacing(10)

        self.btn_dramabite = QPushButton("⚡ Run DramaBite Backup (Online Bypass)")
        self.btn_dramabite.setProperty("class", "btn-primary")
        self.btn_dramabite.clicked.connect(self.run_dramabite_backup)
        btn_layout.addWidget(self.btn_dramabite)

        self.btn_dramaora = QPushButton("🎬 Run Dramaora Backup")
        self.btn_dramaora.setProperty("class", "btn-cyan")
        self.btn_dramaora.clicked.connect(self.run_dramaora_backup)
        btn_layout.addWidget(self.btn_dramaora)

        self.btn_stop = QPushButton("🛑 Stop Engine")
        self.btn_stop.setProperty("class", "btn-danger")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_engine)
        btn_layout.addWidget(self.btn_stop)

        layout.addWidget(btn_card)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Ready")
        layout.addWidget(self.progress_bar)

        # Terminal Console Box Card
        term_card = QFrame()
        term_card.setProperty("class", "card")
        term_layout = QVBoxLayout(term_card)
        term_layout.setContentsMargins(10, 10, 10, 10)

        term_head = QHBoxLayout()
        lbl_term = QLabel("📟 Live Execution Terminal")
        lbl_term.setFont(QFont("Outfit", 11, QFont.Bold))
        term_head.addWidget(lbl_term)

        btn_copy = QPushButton("📋 Copy Logs")
        btn_copy.clicked.connect(self.copy_logs)
        term_head.addWidget(btn_copy)

        btn_clear = QPushButton("🧹 Clear")
        btn_clear.clicked.connect(self.clear_logs)
        term_head.addWidget(btn_clear)

        term_layout.addLayout(term_head)

        self.terminal = QPlainTextEdit()
        self.terminal.setProperty("class", "terminal-box")
        self.terminal.setReadOnly(True)
        term_layout.addWidget(self.terminal)

        layout.addWidget(term_card)

    def run_dramabite_backup(self):
        script = os.path.join(self.workspace_dir, "backup_dramabite.py")
        if not os.path.isfile(script):
            QMessageBox.critical(self, "Error", f"Script not found: {script}")
            return
        self.terminal.appendPlainText(f"🚀 [INIT] Launching DramaBite Standalone Bypass Backup Engine...")
        self.runner.start_python_script(script, cwd=self.workspace_dir)

    def run_dramaora_backup(self):
        script = os.path.join(self.workspace_dir, "backup_dramaora.py")
        if not os.path.isfile(script):
            QMessageBox.critical(self, "Error", f"Script not found: {script}")
            return
        self.terminal.appendPlainText(f"🚀 [INIT] Launching Dramaora Backup Engine...")
        self.runner.start_python_script(script, cwd=self.workspace_dir)

    def stop_engine(self):
        self.runner.stop()
        self.terminal.appendPlainText("🛑 [STOPPED] Backup engine terminated by user.")
        self.set_idle_state()

    def on_process_started(self):
        self.status_badge.setText("🟢 Running")
        self.status_badge.setProperty("class", "badge badge-green")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        self.btn_dramabite.setEnabled(False)
        self.btn_dramaora.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_bar.setFormat("Backup in progress...")
        self.progress_bar.setRange(0, 0) # Indeterminate spinner

    def on_process_finished(self, exit_code):
        self.set_idle_state()
        if exit_code == 0:
            self.terminal.appendPlainText("🎉 [SUCCESS] Backup process completed successfully!")
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("Completed 100%")
        else:
            self.terminal.appendPlainText(f"⚠️ [FINISHED] Process exited with code {exit_code}")
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Finished with errors")

    def on_process_error(self, err_msg):
        self.terminal.appendPlainText(f"❌ [ERROR] {err_msg}")
        self.set_idle_state()

    def set_idle_state(self):
        self.status_badge.setText("⚪ Idle")
        self.status_badge.setProperty("class", "badge")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        self.btn_dramabite.setEnabled(True)
        self.btn_dramaora.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def append_log(self, text):
        self.terminal.moveCursor(QTextCursor.End)
        self.terminal.insertPlainText(text)
        self.terminal.moveCursor(QTextCursor.End)

    def copy_logs(self):
        QApplication.clipboard().setText(self.terminal.toPlainText())
        QMessageBox.information(self, "Copied", "Logs copied to clipboard!")

    def clear_logs(self):
        self.terminal.clear()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Ready")
