from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import Qt
from src.config.slssteam import SLSsteamConfigManager
from src.config.settings import SettingsManager
from src.utils.paths import get_steam_path

class StatCard(QFrame):
    def __init__(self, title: str, value: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("background-color: #111319; border-radius: 12px; border: 1px solid #1E212B; padding: 15px;")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        val_label = QLabel(value)
        val_label.setStyleSheet("font-size: 24px; font-weight: 800; color: #818CF8; border: none;")
        val_label.setAlignment(Qt.AlignCenter)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 14px; color: #94A3B8; border: none;")
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
        title = QLabel("NEBULA — Steam Depot Manager & Tools")
        title.setStyleSheet("font-size: 26px; font-weight: 800; color: #F8FAFC; letter-spacing: 1px;")
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
        table_frame.setStyleSheet("background-color: #111319; border-radius: 12px; border: 1px solid #1E212B; padding: 10px;")
        table_layout = QVBoxLayout(table_frame)
        
        table_title = QLabel("Recent Downloads")
        table_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #E2E8F0; border: none;")
        table_layout.addWidget(table_title)
        
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Game", "Size", "Date", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setStyleSheet("QTableWidget { border: none; background-color: transparent; } QHeaderView::section { background-color: #1E212B; border: none; padding: 5px; color: #94A3B8; }")
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        table_layout.addWidget(self.table)
        
        bottom_layout.addWidget(table_frame, stretch=2)
        
        # Quick Info
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #111319; border-radius: 12px; border: 1px solid #1E212B; padding: 15px;")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setAlignment(Qt.AlignTop)
        
        info_title = QLabel("Quick Info")
        info_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #E2E8F0; border: none; margin-bottom: 10px;")
        info_layout.addWidget(info_title)
        
        steam_path = SettingsManager.get("steam_path", str(get_steam_path() or "Not found"))
        info_steam = QLabel(f"<b>Steam Path:</b><br>{steam_path}")
        info_steam.setWordWrap(True)
        info_steam.setStyleSheet("color: #94A3B8; border: none;")
        info_layout.addWidget(info_steam)
        
        bottom_layout.addWidget(info_frame, stretch=1)
        
        layout.addLayout(bottom_layout)
        
    def refresh_stats(self):
        try:
            from src.utils.paths import get_installed_apps
            app_ids = set(get_installed_apps().keys())
            cfg = SLSsteamConfigManager()
            app_ids.update(cfg.config_data.get("AppIds", []) or [])
            app_ids.update(cfg.config_data.get("AdditionalApps", []) or [])

            lua_count = 0
            lua_size = 0
            steam_path = get_steam_path()
            if steam_path:
                plugin_dir = steam_path / "config" / "stplug-in"
                if plugin_dir.exists():
                    lua_files = list(plugin_dir.glob("*.lua"))
                    lua_count = len(lua_files)
                    lua_size = sum(f.stat().st_size for f in lua_files if f.is_file())

            self.card_luas.layout().itemAt(0).widget().setText(str(lua_count))
            self.card_size.layout().itemAt(0).widget().setText(self._format_size(lua_size))
            self._load_recent_downloads()
        except Exception as e:
            print(f"Error refreshing Home stats: {e}")

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        gb = size_bytes / (1024 ** 3)
        if gb >= 1:
            return f"{gb:.2f} GB"
        mb = size_bytes / (1024 ** 2)
        if mb >= 1:
            return f"{mb:.1f} MB"
        kb = size_bytes / 1024
        if kb >= 1:
            return f"{kb:.1f} KB"
        return f"{size_bytes} B"

    def _load_recent_downloads(self):
        from src.config.settings import SettingsManager
        history = SettingsManager.get("download_history", []) or []
        self.table.setRowCount(0)
        for entry in reversed(history[-20:]):
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(entry.get("title", "")))
            self.table.setItem(row, 1, QTableWidgetItem(entry.get("size", "")))
            self.table.setItem(row, 2, QTableWidgetItem(entry.get("date", "")))
            self.table.setItem(row, 3, QTableWidgetItem(entry.get("status", "")))
