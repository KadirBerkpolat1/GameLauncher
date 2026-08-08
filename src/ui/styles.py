DARK_THEME = """
/* Global */
QWidget {
    background-color: #0D1117; /* Ultra-modern deep dark */
    color: #C9D1D9;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px;
}

/* Sidebar */
#Sidebar {
    background-color: #161B22;
    border-right: 1px solid #21262D;
}

#Sidebar QPushButton {
    background-color: transparent;
    border: none;
    text-align: left;
    padding: 12px 20px;
    margin: 4px 12px;
    border-radius: 8px;
    color: #8B949E;
    font-weight: 600;
    font-size: 15px;
}

#Sidebar QPushButton:hover {
    background-color: #21262D;
    color: #C9D1D9;
}

#Sidebar QPushButton:checked {
    background-color: #1F6FEB; /* Sleek accent blue */
    color: #FFFFFF;
}

/* Main Content Area */
#MainContent {
    background-color: #0D1117;
}

/* Search & Inputs */
QLineEdit {
    background-color: #161B22;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 10px 14px;
    color: #C9D1D9;
    font-size: 14px;
}

QLineEdit:focus {
    border: 1px solid #58A6FF;
    background-color: #0D1117;
}

/* Standard Buttons */
QPushButton[cssClass="PrimaryAction"] {
    background-color: #238636; /* Modern action green */
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 10px 16px;
    font-weight: 600;
    font-size: 14px;
}

QPushButton[cssClass="PrimaryAction"]:hover {
    background-color: #2EA043;
}

QPushButton[cssClass="PrimaryAction"]:disabled {
    background-color: #1B2027;
    color: #484F58;
}

QPushButton[cssClass="SecondaryAction"] {
    background-color: #21262D;
    color: #C9D1D9;
    border: 1px solid #30363D;
    border-radius: 6px;
    padding: 10px 16px;
    font-weight: 600;
    font-size: 14px;
}

QPushButton[cssClass="SecondaryAction"]:hover {
    background-color: #30363D;
    border-color: #8B949E;
}

QPushButton[cssClass="SecondaryAction"]:disabled {
    background-color: #161B22;
    color: #484F58;
    border-color: #30363D;
}

/* Game Card */
#GameCard {
    background-color: #161B22;
    border-radius: 12px;
    border: 1px solid #30363D;
}

#GameCard:hover {
    background-color: #21262D;
    border: 1px solid #58A6FF;
}

#GameCardImage {
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: transparent;
    width: 12px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #30363D;
    min-height: 40px;
    border-radius: 6px;
    margin: 3px;
}

QScrollBar::handle:vertical:hover {
    background-color: #484F58;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Groups */
QGroupBox {
    border: 1px solid #30363D;
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 15px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #58A6FF;
    font-weight: 600;
}
"""