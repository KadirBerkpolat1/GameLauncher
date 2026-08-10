from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import Qt
from src.config.slssteam import SLSsteamConfigManager
from src.config.settings import SettingsManager
from src.utils.paths import get_steam_path

class StatCard(QFrame):
    def __init__(self, title: str, value: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("background-color: #161B22; border-radius: 8px; border: 1px solid #30363D; padding: 15px;")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        val_label = QLabel(value)
        val_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #58A6FF; border: none;")
        val_label.setAlignment(Qt.AlignCenter)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; color: #8B949E; border: none;")
        title_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(val_label)
        layout.addWidget(title_label)

class HomeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.refresh_stats()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Squeegee Manifest App - Steam Depot Manager & Tools")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(title)
        
        # Stats Row
        stats_layout = QHBoxLayout()
        self.card_games = StatCard("Games in Library", "0")
        self.card_luas = StatCard("Lua Files", "0")
        self.card_size = StatCard("Total Size", "0.00 GB")
        stats_layout.addWidget(self.card_games)
        stats_layout.addWidget(self.card_luas)
        stats_layout.addWidget(self.card_size)
        layout.addLayout(stats_layout)
        
        # Bottom Section
        bottom_layout = QHBoxLayout()
        
        # Recent Downloads Table
        table_frame = QFrame()
        table_frame.setStyleSheet("background-color: #161B22; border-radius: 8px; border: 1px solid #30363D; padding: 10px;")
        table_layout = QVBoxLayout(table_frame)
        
        table_title = QLabel("Recent Downloads")
        table_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #C9D1D9; border: none;")
        table_layout.addWidget(table_title)
        
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Game", "Size", "Date", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setStyleSheet("QTableWidget { border: none; background-color: transparent; } QHeaderView::section { background-color: #21262D; border: none; padding: 5px; color: #8B949E; }")
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        table_layout.addWidget(self.table)
        
        bottom_layout.addWidget(table_frame, stretch=2)
        
        # Quick Info
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #161B22; border-radius: 8px; border: 1px solid #30363D; padding: 15px;")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setAlignment(Qt.AlignTop)
        
        info_title = QLabel("Quick Info")
        info_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #C9D1D9; border: none; margin-bottom: 10px;")
        info_layout.addWidget(info_title)
        
        steam_path = SettingsManager.get("steam_path", str(get_steam_path() or "Not found"))
        info_steam = QLabel(f"<b>Steam Path:</b><br>{steam_path}")
        info_steam.setWordWrap(True)
        info_steam.setStyleSheet("color: #8B949E; border: none;")
        info_layout.addWidget(info_steam)
        
        bottom_layout.addWidget(info_frame, stretch=1)
        
        layout.addLayout(bottom_layout)
        
    def refresh_stats(self):
        try:
            cfg = SLSsteamConfigManager()
            apps = cfg.config.get("apps", {})
            self.card_games.layout().itemAt(0).widget().setText(str(len(apps)))
            
            # Count luas roughly
            lua_count = 0
            if get_steam_path():
                plugin_dir = get_steam_path() / "config" / "stplug-in"
                if plugin_dir.exists():
                    lua_count = len(list(plugin_dir.glob("*.lua")))
            self.card_luas.layout().itemAt(0).widget().setText(str(lua_count))
            
            # Table could be loaded from a local sqlite or settings history in the future
            # For now, we leave it empty to match a fresh install
        except Exception:
            pass
