DARK_THEME = """
/* Global - Premium Modern Theme */
QWidget {
    background-color: #0B0C10; /* Deep premium black/blue */
    color: #E2E8F0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    font-size: 14px;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: transparent;
    width: 12px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background-color: #2D3342;
    min-height: 30px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background-color: #3F475B;
}
QScrollBar::sub-line:vertical, QScrollBar::add-line:vertical, QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
    height: 0px;
    background: none;
}
QScrollBar::sub-page:vertical, QScrollBar::add-page:vertical {
    background-color: transparent;
}

/* Sidebar */
#Sidebar {
    background-color: #111319; /* Slightly lighter for contrast */
    border-right: 1px solid #1E212B;
}

#Sidebar QPushButton {
    background-color: transparent;
    border: none;
    text-align: left;
    padding: 14px 22px;
    margin: 6px 12px;
    border-radius: 10px;
    color: #94A3B8;
    font-weight: 600;
    font-size: 15px;
    letter-spacing: 0.5px;
}

#Sidebar QPushButton:hover {
    background-color: #1E212B;
    color: #F8FAFC;
}

#Sidebar QPushButton:checked {
    background-color: rgba(99, 102, 241, 0.15); /* Indigo tint */
    color: #818CF8; /* Vibrant Indigo */
    border-left: 4px solid #818CF8;
    border-radius: 8px;
    border-top-left-radius: 4px;
    border-bottom-left-radius: 4px;
}

/* Main Content Area */
#MainContent {
    background-color: #0B0C10;
}

/* Search & Inputs */
QLineEdit {
    background-color: #111319;
    border: 1px solid #1E212B;
    border-radius: 8px;
    padding: 12px 16px;
    color: #F8FAFC;
    font-size: 14px;
    selection-background-color: #6366F1;
}

QLineEdit:focus {
    border: 1px solid #6366F1; /* Indigo focus */
    background-color: #161822;
}

/* Standard Buttons */
QPushButton[cssClass="PrimaryAction"] {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #6366F1);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 700;
    font-size: 14px;
}

QPushButton[cssClass="PrimaryAction"]:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:1 #4F46E5);
}

QPushButton[cssClass="PrimaryAction"]:pressed {
    background-color: #3730A3;
}

QPushButton[cssClass="PrimaryAction"]:disabled {
    background-color: #2D3342;
    color: #94A3B8;
}

QPushButton[cssClass="SecondaryAction"] {
    background-color: #1E212B;
    color: #E2E8F0;
    border: 1px solid #2D3342;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 600;
    font-size: 14px;
}

QPushButton[cssClass="SecondaryAction"]:hover {
    background-color: #2D3342;
    border-color: #3F475B;
}

QPushButton[cssClass="SecondaryAction"]:pressed {
    background-color: #1E212B;
}

QPushButton[cssClass="SecondaryAction"]:disabled {
    background-color: transparent;
    color: #475569;
    border: 1px solid #1E212B;
}

/* Fix Buttons & Special Actions */
QPushButton[cssClass="FixAction"] {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10B981);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: bold;
}

QPushButton[cssClass="FixAction"]:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #047857, stop:1 #059669);
}

QPushButton[cssClass="DangerAction"] {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #DC2626, stop:1 #EF4444);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: bold;
}

QPushButton[cssClass="DangerAction"]:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #B91C1C, stop:1 #DC2626);
}

/* Game Cards */
QFrame[cssClass="GameCard"] {
    background-color: #111319;
    border: 1px solid #1E212B;
    border-radius: 16px;
    padding: 0px;
}

QFrame[cssClass="GameCard"]:hover {
    border: 1px solid #3F475B;
    background-color: #161822;
}

/* Labels */
QLabel[cssClass="GameTitle"] {
    font-size: 16px;
    font-weight: 800;
    color: #F8FAFC;
}

QLabel[cssClass="GameSubtitle"] {
    font-size: 13px;
    color: #94A3B8;
    font-weight: 500;
}

QLabel[cssClass="HeaderTitle"] {
    font-size: 28px;
    font-weight: 900;
    color: #FFFFFF;
    letter-spacing: 0.5px;
}

/* Dialogs */
QDialog {
    background-color: #0B0C10;
    border: 1px solid #1E212B;
    border-radius: 12px;
}

/* Progress Bars */
QProgressBar {
    background-color: #1E212B;
    border-radius: 6px;
    border: none;
    text-align: center;
    color: transparent; 
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #6366F1);
    border-radius: 6px;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #1E212B;
    background: #111319;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {

QComboBox:hover {
    border: 1px solid #3F475B;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left-width: 0px;
}

QComboBox QAbstractItemView {
    background-color: #111319;
    border: 1px solid #1E212B;
    border-radius: 8px;
    selection-background-color: rgba(99, 102, 241, 0.2);
    selection-color: #818CF8;
    outline: none;
}
    background: transparent;
    color: #94A3B8;
    padding: 10px 24px;
    font-weight: 600;
    font-size: 14px;
    border-bottom: 2px solid transparent;
}

QTabBar::tab:selected {
    color: #818CF8;
    border-bottom: 2px solid #818CF8;
}

QTabBar::tab:hover:!selected {
    color: #E2E8F0;
}

/* Pagination Controls */
QSpinBox {
    background-color: #111319;
    border: 1px solid #1E212B;
    border-radius: 6px;
    color: #F8FAFC;
    padding: 6px;
}

QSpinBox::up-button, QSpinBox::down-button {
    background-color: transparent;
    border: none;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #1E212B;
}

/* Available Badge */
QLabel.AvailableBadge {
    background-color: rgba(16, 185, 129, 0.15);
    color: #10B981;
    border: 1px solid #10B981;
    padding: 4px 10px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
}

/* List Widget (for dialogs) */
QListWidget {
    background-color: #111319;
    border: 1px solid #1E212B;
    border-radius: 8px;
    outline: none;
}

QListWidget::item {
    padding: 12px;
    border-bottom: 1px solid #1E212B;
}

QListWidget::item:hover {
    background-color: #1E212B;
}

QListWidget::item:selected {
    background-color: rgba(99, 102, 241, 0.2);
    color: #818CF8;
    border-left: 3px solid #818CF8;
}

/* Checkboxes */
QCheckBox {
    spacing: 8px;
    color: #E2E8F0;
    font-size: 14px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #3F475B;
    background-color: #111319;
}

QCheckBox::indicator:unchecked:hover {
    border: 1px solid #6366F1;
}

QCheckBox::indicator:checked {
    background-color: #6366F1;
    border: 1px solid #6366F1;
    image: url(check.png); /* Need an icon or just CSS, PySide6 supports basic checks but custom is better */
}


/* ComboBox */
QComboBox {
    background-color: #111319;
    border: 1px solid #1E212B;
    border-radius: 8px;
    padding: 8px 12px;
    color: #F8FAFC;
    font-size: 14px;
}

QComboBox:hover {
    border: 1px solid #3F475B;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left-width: 0px;
}

QComboBox QAbstractItemView {
    background-color: #111319;
    border: 1px solid #1E212B;
    border-radius: 8px;
    selection-background-color: rgba(99, 102, 241, 0.2);
    selection-color: #818CF8;
    outline: none;
}
"""
