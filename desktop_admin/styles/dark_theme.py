"""
Ultra-Premium Dark Theme QSS for Animew Pro & DramaFlixHD Desktop Admin Suite.
Designed for high elegance, modern glassmorphism, clean tables, and Khmer font support.
"""

DARK_THEME_QSS = """
/* ================= GLOBAL RESETS & TYPOGRAPHY ================= */
* {
    font-family: 'Kantumruy Pro', 'Outfit', 'Segoe UI', system-ui, -apple-system, sans-serif;
    outline: none;
}

QWidget {
    background-color: #080c18;
    color: #f1f5f9;
    font-size: 13px;
    selection-background-color: #6366f1;
    selection-color: #ffffff;
}

QMainWindow {
    background-color: #080c18;
}

/* ================= SIDEBAR NAVIGATION ================= */
#sidebar {
    background-color: #0b1120;
    border-right: 1px solid rgba(255, 255, 255, 0.06);
    min-width: 240px;
    max-width: 240px;
}

#brandTitle {
    font-size: 17px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.5px;
}

#brandSub {
    font-size: 10px;
    color: #38bdf8;
    font-weight: 700;
    letter-spacing: 1px;
}

QPushButton.nav-btn {
    background-color: transparent;
    color: #94a3b8;
    text-align: left;
    padding: 13px 18px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 13.5px;
    border: 1px solid transparent;
    margin: 3px 10px;
}

QPushButton.nav-btn:hover {
    background-color: rgba(255, 255, 255, 0.05);
    color: #f8fafc;
}

QPushButton.nav-btn:checked {
    background-color: #1e1b4b;
    color: #a5b4fc;
    border: 1px solid rgba(129, 140, 248, 0.35);
    font-weight: 700;
}

/* ================= CARDS & PANELS ================= */
QFrame.card {
    background-color: #0d1527;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 14px;
}

QFrame.card-glass {
    background-color: rgba(13, 21, 39, 0.85);
    border: 1px solid rgba(56, 189, 248, 0.2);
    border-radius: 14px;
}

/* ================= BUTTONS ================= */
QPushButton {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 9px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 12.5px;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #334155;
    border-color: rgba(255, 255, 255, 0.22);
}

QPushButton:pressed {
    background-color: #0f172a;
}

QPushButton.btn-primary {
    background-color: #6366f1;
    color: #ffffff;
    border: 1px solid #4f46e5;
}

QPushButton.btn-primary:hover {
    background-color: #4f46e5;
    border-color: #4338ca;
}

QPushButton.btn-success {
    background-color: #10b981;
    color: #ffffff;
    border: 1px solid #059669;
}

QPushButton.btn-success:hover {
    background-color: #059669;
}

QPushButton.btn-danger {
    background-color: #ef4444;
    color: #ffffff;
    border: 1px solid #dc2626;
}

QPushButton.btn-danger:hover {
    background-color: #dc2626;
}

QPushButton.btn-cyan {
    background-color: #0284c7;
    color: #ffffff;
    border: 1px solid #0369a1;
}

QPushButton.btn-cyan:hover {
    background-color: #0369a1;
}

/* ================= INPUTS & FORMS ================= */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #090e1a;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 9px;
    padding: 8px 12px;
    color: #f8fafc;
    font-size: 13px;
    selection-background-color: #6366f1;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #6366f1;
    background-color: #0c1322;
}

QComboBox {
    background-color: #090e1a;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 9px;
    padding: 7px 12px;
    color: #f8fafc;
    font-size: 12.5px;
    font-weight: 600;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #0f172a;
    border: 1px solid rgba(255, 255, 255, 0.15);
    selection-background-color: #6366f1;
    color: #f8fafc;
    padding: 6px;
    border-radius: 8px;
}

/* ================= TABLES & HEADERS (FIX WHITE BOX BUG) ================= */
QTableWidget {
    background-color: #090e1a;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 11px;
    gridline-color: rgba(255, 255, 255, 0.04);
    color: #e2e8f0;
    selection-background-color: rgba(99, 102, 241, 0.28);
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 7px 10px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

QTableWidget::item:selected {
    background-color: rgba(99, 102, 241, 0.28);
    color: #ffffff;
}

QTableWidget::item:hover {
    background-color: rgba(255, 255, 255, 0.03);
}

QHeaderView::section {
    background-color: #0e172a;
    color: #94a3b8;
    padding: 9px 12px;
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    font-weight: 700;
    font-size: 11.5px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Fix White Corner Box in QTableWidget */
QTableCornerButton::section {
    background-color: #0e172a;
    border: none;
}

/* ================= TERMINAL CONSOLE ================= */
QPlainTextEdit.terminal-box {
    background-color: #040711;
    color: #38bdf8;
    font-family: 'Consolas', 'Cascadia Code', monospace;
    font-size: 12px;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 10px;
    padding: 12px;
    line-height: 1.5;
}

/* ================= PROGRESS BAR ================= */
QProgressBar {
    background-color: #090e1a;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 9px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
    font-size: 11px;
    height: 22px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #38bdf8);
    border-radius: 8px;
}

/* ================= SCROLLBARS ================= */
QScrollBar:vertical {
    background: transparent;
    width: 7px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.16);
    min-height: 24px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 0.3);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: transparent;
    height: 7px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: rgba(255, 255, 255, 0.16);
    min-width: 24px;
    border-radius: 3px;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ================= BADGES & CHIPS ================= */
QLabel.badge {
    background-color: rgba(56, 189, 248, 0.15);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.3);
    border-radius: 7px;
    padding: 3px 10px;
    font-size: 11.5px;
    font-weight: 700;
}

QLabel.badge-green {
    background-color: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.3);
}

QLabel.badge-purple {
    background-color: rgba(168, 85, 247, 0.15);
    color: #c084fc;
    border: 1px solid rgba(168, 85, 247, 0.3);
}
"""
