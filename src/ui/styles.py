"""
Premium Cyber-Dark Theme for Nebula Game Launcher
Designed for high-end desktop gaming feel with glassmorphic accents,
refined gradients, glowing indicators, and ultra-crisp typography.
"""

DARK_THEME = """
/* =========================================================================
   GLOBAL RESET & TYPOGRAPHY
   ========================================================================= */
QWidget {
    background-color: #090A0F;
    color: #F1F5F9;
    font-family: 'Segoe UI', 'Inter', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    selection-background-color: #6366F1;
    selection-color: #FFFFFF;
}

QLabel {
    background-color: transparent;
    color: #F1F5F9;
}

/* =========================================================================
   SCROLL AREAS & SCROLLBARS
   ========================================================================= */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollArea#HistoryScroll, QScrollArea#SettingsScroll {
    background-color: #0F121C;
    border: 1px solid #1E2337;
    border-radius: 12px;
}

QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    margin: 4px 2px;
}

QScrollBar::handle:vertical {
    background-color: #262D47;
    min-height: 36px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4F46E5;
}

QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical,
QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
    height: 0px;
    background: none;
}

QScrollBar::sub-page:vertical, QScrollBar::add-page:vertical {
    background-color: transparent;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    margin: 2px 4px;
}

QScrollBar::handle:horizontal {
    background-color: #262D47;
    min-width: 36px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #4F46E5;
}

/* =========================================================================
   SIDEBAR NAVIGATION
   ========================================================================= */
#Sidebar {
    background-color: #0D0F17;
    border-right: 1px solid #191E30;
}

#Sidebar QWidget, #Sidebar QLabel {
    background-color: transparent;
}

#Sidebar QPushButton {
    border: none;
    text-align: left;
    padding: 12px 18px;
    margin: 3px 12px;
    border-radius: 10px;
    color: #94A3B8;
    font-weight: 600;
    font-size: 14px;
    letter-spacing: 0.3px;
}

#Sidebar QPushButton:hover {
    background-color: #161A29;
    color: #F8FAFC;
}

#Sidebar QPushButton:checked {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(99, 102, 241, 0.22), stop:1 rgba(139, 92, 246, 0.08));
    color: #A5B4FC;
    border-left: 4px solid #6366F1;
    border-radius: 8px;
    border-top-left-radius: 2px;
    border-bottom-left-radius: 2px;
    font-weight: 700;
}

/* =========================================================================
   MAIN CONTENT & CONTAINERS
   ========================================================================= */
#MainContent {
    background-color: #090A0F;
}

QFrame#StatCard, QFrame#SurfaceCard {
    background-color: #121522;
    border: 1px solid #1E243A;
    border-radius: 12px;
    padding: 16px;
}

QFrame#StatCard:hover {
    border: 1px solid #2D3758;
    background-color: #151928;
}

/* =========================================================================
   INPUTS & TEXT FIELDS
   ========================================================================= */
QLineEdit {
    background-color: #121522;
    border: 1px solid #20273F;
    border-radius: 10px;
    padding: 10px 16px;
    color: #F8FAFC;
    font-size: 13px;
}

QLineEdit:hover {
    border: 1px solid #2D3758;
    background-color: #151827;
}

QLineEdit:focus {
    border: 1px solid #6366F1;
    background-color: #171A2B;
}

QSpinBox, QComboBox {
    background-color: #121522;
    border: 1px solid #20273F;
    border-radius: 8px;
    padding: 8px 14px;
    color: #F8FAFC;
    font-weight: 600;
}

QComboBox:hover, QSpinBox:hover {
    border: 1px solid #2D3758;
}

QComboBox:focus, QSpinBox:focus {
    border: 1px solid #6366F1;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left: none;
}

QComboBox QAbstractItemView {
    background-color: #121522;
    border: 1px solid #20273F;
    border-radius: 8px;
    color: #F8FAFC;
    selection-background-color: #4F46E5;
    padding: 4px;
}

/* =========================================================================
   BUTTONS
   ========================================================================= */
QPushButton[cssClass="PrimaryAction"], QPushButton#PrimaryBtn {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #7C3AED);
    color: #FFFFFF;
    border: 1px solid #6366F1;
    border-radius: 8px;
    padding: 9px 18px;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.3px;
}

QPushButton[cssClass="PrimaryAction"]:hover, QPushButton#PrimaryBtn:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:1 #6D28D9);
    border: 1px solid #818CF8;
}

QPushButton[cssClass="PrimaryAction"]:pressed, QPushButton#PrimaryBtn:pressed {
    background-color: #3730A3;
}

QPushButton[cssClass="SecondaryAction"], QPushButton#SecondaryBtn {
    background-color: #161A2B;
    color: #CBD5E1;
    border: 1px solid #242D4A;
    border-radius: 8px;
    padding: 9px 18px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton[cssClass="SecondaryAction"]:hover, QPushButton#SecondaryBtn:hover {
    background-color: #1E243A;
    color: #FFFFFF;
    border: 1px solid #3B4670;
}

QPushButton[cssClass="DangerAction"], QPushButton#DangerBtn {
    background-color: rgba(239, 68, 68, 0.15);
    color: #F87171;
    border: 1px solid rgba(239, 68, 68, 0.35);
    border-radius: 8px;
    padding: 9px 18px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton[cssClass="DangerAction"]:hover, QPushButton#DangerBtn:hover {
    background-color: #DC2626;
    color: #FFFFFF;
    border: 1px solid #EF4444;
}

QPushButton[cssClass="SuccessAction"], QPushButton#SuccessBtn {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10B981);
    color: #FFFFFF;
    border: 1px solid #34D399;
    border-radius: 8px;
    padding: 9px 18px;
    font-weight: 700;
    font-size: 13px;
}

QPushButton[cssClass="SuccessAction"]:hover, QPushButton#SuccessBtn:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #047857, stop:1 #059669);
}

QPushButton:disabled {
    background-color: #131724;
    color: #475569;
    border: 1px solid #1B2135;
}

/* =========================================================================
   GAME CARD STYLING
   ========================================================================= */
QFrame#GameCard {
    background-color: #111420;
    border: 1px solid #1C2237;
    border-radius: 14px;
}

QFrame#GameCard:hover {
    background-color: #151929;
    border: 1px solid #6366F1;
}

QLabel#GameCardImage {
    border-top-left-radius: 13px;
    border-top-right-radius: 13px;
    background-color: #0E1018;
}

/* =========================================================================
   DOWNLOADS & PROGRESS BARS
   ========================================================================= */
QProgressBar {
    background-color: #121624;
    border: 1px solid #1F253C;
    border-radius: 6px;
    text-align: center;
    color: #FFFFFF;
    font-weight: 700;
    font-size: 11px;
    height: 14px;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #8B5CF6);
    border-radius: 5px;
}

QFrame#ActiveDownloadCard {
    background-color: #121522;
    border: 1px solid #1F253D;
    border-radius: 12px;
    padding: 14px;
}

QFrame#ActiveDownloadCard:hover {
    border: 1px solid #333D63;
    background-color: #151928;
}

/* =========================================================================
   DIALOGS & MODALS
   ========================================================================= */
QDialog {
    background-color: #0C0E16;
    color: #F1F5F9;
    border: 1px solid #232A42;
    border-radius: 14px;
}

QGroupBox {
    background-color: #111420;
    border: 1px solid #1E243A;
    border-radius: 10px;
    margin-top: 14px;
    padding: 14px;
    font-weight: 700;
    color: #E2E8F0;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: #818CF8;
}

QCheckBox {
    color: #E2E8F0;
    font-size: 13px;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #2B3554;
    border-radius: 5px;
    background-color: #121522;
}

QCheckBox::indicator:hover {
    border: 1px solid #6366F1;
}

QCheckBox::indicator:checked {
    background-color: #6366F1;
    border: 1px solid #818CF8;
    image: none; /* Qt default checkmark rendered cleanly */
}

/* =========================================================================
   LISTS & TABLES
   ========================================================================= */
QListWidget, QTableWidget {
    background-color: #0E111B;
    border: 1px solid #1C2237;
    border-radius: 10px;
    padding: 6px;
    color: #F1F5F9;
}

QListWidget::item {
    padding: 10px 14px;
    border-radius: 8px;
    margin-bottom: 2px;
}

QListWidget::item:hover {
    background-color: #171C2E;
}

QListWidget::item:selected {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:1 #6366F1);
    color: #FFFFFF;
    font-weight: 600;
}

/* =========================================================================
   PILLS, BADGES & HEADER LABELS
   ========================================================================= */
QLabel[cssClass="HeaderTitle"] {
    font-size: 24px;
    font-weight: 800;
    color: #F8FAFC;
    letter-spacing: -0.5px;
}

QLabel[cssClass="SubHeader"] {
    font-size: 14px;
    color: #94A3B8;
    font-weight: 500;
}

QLabel[cssClass="Badge"] {
    background-color: #1E253E;
    color: #818CF8;
    border: 1px solid #2D375B;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
}

QLabel[cssClass="BadgeSuccess"] {
    background-color: rgba(16, 185, 129, 0.15);
    color: #34D399;
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
}

QLabel[cssClass="BadgeWarning"] {
    background-color: rgba(245, 158, 11, 0.15);
    color: #FBBF24;
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
}
"""
