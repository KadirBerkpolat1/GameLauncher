from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QScrollArea, QPushButton, QLineEdit, QComboBox)
from PySide6.QtCore import Qt, Signal
from src.config.slssteam import SLSsteamConfigManager
from src.ui.game_card import GameCard
from src.api.hubcap import hubcap_api
from src.ui.flow_layout import FlowLayout
from src.utils.async_utils import get_async_loop

class LibraryWidget(QWidget):
    download_requested = Signal(int, str)
    restart_steam_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._load_generation = 0
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # --- Header & Stats ---
        header_layout = QHBoxLayout()
        header = QLabel("My Library")
        header.setProperty("cssClass", "HeaderTitle")
        self.lbl_stats = QLabel("0 Lua, 0 Steam, 0 GB Size")
        self.lbl_stats.setProperty("cssClass", "GameSubtitle")
        self.lbl_stats.setStyleSheet("margin-left: 20px;") # keep just the margin if needed, or rely on layout
        header_layout.addWidget(header)
        header_layout.addWidget(self.lbl_stats)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # --- Action Toolbar ---
        action_bar = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setProperty("cssClass", "SecondaryAction")
        self.btn_refresh.clicked.connect(self.load_library)
        self.btn_refresh_cache = QPushButton("Refresh Cache")
        self.btn_refresh_cache.setProperty("cssClass", "SecondaryAction")
        self.btn_refresh_cache.clicked.connect(self._refresh_cache)
        self.btn_toggle_updates = QPushButton("Toggle Updates")
        self.btn_toggle_updates.setProperty("cssClass", "SecondaryAction")
        self.btn_toggle_updates.clicked.connect(self._toggle_updates)
        self.btn_export_luas = QPushButton("Export Luas")
        self.btn_export_luas.setProperty("cssClass", "SecondaryAction")
        self.btn_export_luas.clicked.connect(self._export_luas)
        self.btn_restart_steam = QPushButton("Restart Steam")
        self.btn_restart_steam.setProperty("cssClass", "PrimaryAction")
        self.btn_restart_steam.clicked.connect(self.restart_steam_requested.emit)

        action_bar.addWidget(self.btn_refresh)
        action_bar.addWidget(self.btn_refresh_cache)
        action_bar.addWidget(self.btn_toggle_updates)
        action_bar.addWidget(self.btn_export_luas)
        action_bar.addWidget(self.btn_restart_steam)
        action_bar.addStretch()
        layout.addLayout(action_bar)

        # --- Filters Toolbar ---
        filters_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search in library...")
        self.search_input.setFixedWidth(250)
        
        self.combo_category = QComboBox()
        self.combo_category.addItems(["All", "Games", "DLC"])
        
        self.combo_sort = QComboBox()
        self.combo_sort.addItems(["Sort: Name", "Sort: Size", "Sort: Recent"])

        self.btn_list_view = QPushButton("List View")
        self.btn_list_view.setProperty("cssClass", "SecondaryAction")
        self.btn_select_mode = QPushButton("Select Mode")
        self.btn_select_mode.setProperty("cssClass", "SecondaryAction")

        filters_bar.addWidget(self.search_input)
        filters_bar.addWidget(self.combo_category)
        filters_bar.addWidget(self.combo_sort)
        filters_bar.addStretch()
        filters_bar.addWidget(self.btn_select_mode)
        filters_bar.addWidget(self.btn_list_view)
        layout.addLayout(filters_bar)

        # Grid Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background-color: transparent;")

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background-color: transparent;")
        self.grid_layout = FlowLayout(self.grid_container, spacing=20)

        # Empty state label
        self.empty_label = QLabel("Your library is empty. Go to Search to add games.")
        self.empty_label.setProperty("cssClass", "GameSubtitle")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.grid_layout.addWidget(self.empty_label)

        self.scroll_area.setWidget(self.grid_container)
        layout.addWidget(self.scroll_area)

    def _clear_grid(self) -> None:
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item.widget() and item.widget() != self.empty_label:
                item.widget().deleteLater()

    def _refresh_cache(self) -> None:
        hubcap_api.clear_cache()
        self.load_library()

    def _toggle_updates(self) -> None:
        try:
            manager = SLSsteamConfigManager()
            manager.config_data["DisableUpdates"] = not bool(manager.config_data.get("DisableUpdates", True))
            manager.save()
            state = "OFF" if manager.config_data["DisableUpdates"] else "ON"
            self.btn_toggle_updates.setText(f"Updates: {state}")
        except Exception as e:
            print(f"Error toggling updates: {e}")

    def _export_luas(self) -> None:
        import shutil
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from src.utils.paths import get_steam_path
        steam_path = get_steam_path()
        if not steam_path:
            QMessageBox.warning(self, "Error", "Steam path not configured. Set it in Settings first.")
            return
        plugin_dir = steam_path / "config" / "stplug-in"
        if not plugin_dir.exists() or not list(plugin_dir.glob("*.lua")):
            QMessageBox.information(self, "No Lua Files", "No Lua files found to export.")
            return
        dest = QFileDialog.getExistingDirectory(self, "Select export folder")
        if not dest:
            return
        count = 0
        for f in plugin_dir.glob("*.lua"):
            try:
                shutil.copy2(f, Path(dest) / f.name)
                count += 1
            except Exception as e:
                print(f"Failed to export {f.name}: {e}")
        QMessageBox.information(self, "Export Complete", f"Exported {count} Lua file(s) to {dest}")

    def load_library(self) -> None:
        """Reads the SLSsteam config and populates the library view."""
        self._clear_grid()
        try:
            manager = SLSsteamConfigManager()
            # Combine AppIds and AdditionalApps to show everything in the launcher library
            raw_app_ids = (manager.config_data.get("AppIds", []) or []) + (manager.config_data.get("AdditionalApps", []) or [])
            app_ids = set(int(x) for x in raw_app_ids if x)

            if not app_ids:
                self.empty_label.show()
                self.lbl_stats.setText("0 Lua, 0 Steam, 0 GB Size")
                return

            self.empty_label.hide()

            # Real stats: count Lua files on disk and compute their total size
            from src.utils.paths import get_steam_path
            steam_path = get_steam_path()
            lua_count = 0
            lua_size = 0
            if steam_path:
                plugin_dir = steam_path / "config" / "stplug-in"
                if plugin_dir.exists():
                    lua_files = list(plugin_dir.glob("*.lua"))
                    lua_count = len(lua_files)
                    lua_size = sum(f.stat().st_size for f in lua_files if f.is_file())
            size_gb = lua_size / (1024 ** 3)
            self.lbl_stats.setText(f"{lua_count} Lua, {len(app_ids)} Steam, {size_gb:.2f} GB Size")

            # Fetch game details asynchronously
            loop = get_async_loop()
            self._load_generation += 1
            loop.create_task(self._fetch_and_display_library(list(app_ids)))

        except Exception as e:
            self.empty_label.setText(f"Error loading library: {e}")
            self.empty_label.show()

    async def _fetch_and_display_library(self, app_ids: list) -> None:
        import httpx

        generation = self._load_generation

        async with httpx.AsyncClient() as client:
            for app_id in app_ids:
                if generation != self._load_generation:
                    return
                title = f"App {app_id}"
                image_url = ""
                try:
                    steam_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
                    response = await client.get(steam_url, timeout=5.0)
                    if response.status_code == 200:
                        data = response.json()
                        app_data = data.get(str(app_id), {})
                        if app_data.get("success"):
                            title = app_data.get("data", {}).get("name", title)
                except Exception as e:
                    print(f"Error fetching name for {app_id}: {e}")

                if generation != self._load_generation:
                    return

                card = GameCard(app_id, title, image_url, mode="library")
                card.download_requested.connect(self.download_requested.emit)
                card.uninstalled.connect(lambda _app_id: self.load_library())
                card.image_load_failed.connect(self._push_card_to_end)
                self.grid_layout.addWidget(card)

    def _push_card_to_end(self, card) -> None:
        self.grid_layout.removeWidget(card)
        self.grid_layout.addWidget(card)
