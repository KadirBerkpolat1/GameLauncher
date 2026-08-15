from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QScrollArea, QPushButton, QLineEdit, QComboBox,
                               QFrame, QSizePolicy)
from PySide6.QtCore import Qt, Signal
from src.config.slssteam import SLSsteamConfigManager
from src.ui.game_card import GameCard
from src.api.hubcap import hubcap_api
from src.ui.flow_layout import FlowLayout
from src.utils.async_utils import get_async_loop


class LibraryWidget(QWidget):
    """
    Redesigned My Library view featuring stat cards, instant filter/search,
    responsive card flow, and quick management tools.
    """
    download_requested = Signal(int, str)
    restart_steam_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._load_generation = 0
        self._all_cards = []
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # =====================================================================
        # HEADER & STATS BANNER
        # =====================================================================
        header_layout = QHBoxLayout()
        
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        header = QLabel("My Library")
        header.setProperty("cssClass", "HeaderTitle")
        sub = QLabel("Manage your installed games, apply fixes, and configure plugins")
        sub.setProperty("cssClass", "SubHeader")
        title_box.addWidget(header)
        title_box.addWidget(sub)

        header_layout.addLayout(title_box)
        header_layout.addStretch()

        # Top Action Buttons
        self.btn_refresh = QPushButton("🔄  Refresh")
        self.btn_refresh.setProperty("cssClass", "SecondaryAction")
        self.btn_refresh.clicked.connect(self.load_library)

        self.btn_export = QPushButton("📤  Export Luas")
        self.btn_export.setProperty("cssClass", "SecondaryAction")
        self.btn_export.clicked.connect(self._export_luas)

        self.btn_cache = QPushButton("🧹  Clear Cache")
        self.btn_cache.setProperty("cssClass", "SecondaryAction")
        self.btn_cache.clicked.connect(self._refresh_cache)

        header_layout.addWidget(self.btn_refresh)
        header_layout.addWidget(self.btn_export)
        header_layout.addWidget(self.btn_cache)

        layout.addLayout(header_layout)

        # =====================================================================
        # 3 STAT CARDS BANNER
        # =====================================================================
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        self.card_games = self._create_stat_card("🎮  TOTAL GAMES", "0 Games", "Installed on disk & library")
        self.card_luas = self._create_stat_card("⚡  LUA PLUGINS", "0 Active", "SLSsteam plugins enabled")
        self.card_size = self._create_stat_card("💾  TOTAL STORAGE", "0.00 GB", "Estimated storage used")

        stats_layout.addWidget(self.card_games)
        stats_layout.addWidget(self.card_luas)
        stats_layout.addWidget(self.card_size)

        layout.addLayout(stats_layout)

        # =====================================================================
        # SEARCH & FILTER TOOLBAR
        # =====================================================================
        filters_bar = QHBoxLayout()
        filters_bar.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search games in library...")
        self.search_input.setFixedWidth(280)
        self.search_input.textChanged.connect(self._filter_cards)
        self.combo_category = QComboBox()
        self.combo_category.addItems(["All Items", "Installed Only", "Lua Config Only", "Hidden"])
        self.combo_category.currentIndexChanged.connect(self._filter_cards)

        self.combo_sort = QComboBox()
        self.combo_sort.addItems(["Sort: Name (A-Z)", "Sort: App ID"])

        self.btn_toggle_updates = QPushButton("Updates: ON")
        self.btn_toggle_updates.setProperty("cssClass", "SecondaryAction")
        self.btn_toggle_updates.clicked.connect(self._toggle_updates)

        filters_bar.addWidget(self.search_input)
        filters_bar.addWidget(self.combo_category)
        filters_bar.addWidget(self.combo_sort)
        filters_bar.addStretch()
        filters_bar.addWidget(self.btn_toggle_updates)

        layout.addLayout(filters_bar)

        # =====================================================================
        # GAME GRID AREA
        # =====================================================================
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("LibraryScroll")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.grid_container = QWidget()
        self.grid_layout = FlowLayout(self.grid_container, spacing=20)

        # Empty state widget
        self.empty_widget = QFrame()
        self.empty_widget.setObjectName("SurfaceCard")
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setContentsMargins(40, 40, 40, 40)
        empty_layout.setSpacing(12)

        empty_icon = QLabel("🎮")
        empty_icon.setStyleSheet("font-size: 40px;")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.empty_title = QLabel("Your Library is Empty")
        self.empty_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #FFFFFF;")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.empty_sub = QLabel("Explore the Store to download games or add manifest Lua files.")
        self.empty_sub.setProperty("cssClass", "SubHeader")
        self.empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_layout.addWidget(empty_icon)
        empty_layout.addWidget(self.empty_title)
        empty_layout.addWidget(self.empty_sub)

        self.grid_layout.addWidget(self.empty_widget)

        self.scroll_area.setWidget(self.grid_container)
        layout.addWidget(self.scroll_area)

        # Load initial library state
        self.load_library()

    def _create_stat_card(self, title: str, main_val: str, desc: str) -> QFrame:
        card = QFrame()
        card.setObjectName("StatCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #818CF8; font-size: 11px; font-weight: 800; letter-spacing: 1px;")

        lbl_val = QLabel(main_val)
        lbl_val.setStyleSheet("color: #FFFFFF; font-size: 20px; font-weight: 800;")

        lbl_desc = QLabel(desc)
        lbl_desc.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 500;")

        card_layout.addWidget(lbl_title)
        card_layout.addWidget(lbl_val)
        card_layout.addWidget(lbl_desc)

        # Store value and desc labels for live updates
        card._val_label = lbl_val
        card._desc_label = lbl_desc
        return card

    def _clear_grid(self) -> None:
        self._all_cards.clear()
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item and item.widget() != self.empty_widget:
                taken = self.grid_layout.takeAt(i)
                if taken and taken.widget():
                    taken.widget().deleteLater()
    def refresh_library(self) -> None:
        self.load_library()

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
        """Shows games installed on disk (steamapps manifests) plus SLSsteam config entries."""
        self._clear_grid()
        try:
            manager = SLSsteamConfigManager()
            raw_app_ids = (manager.config_data.get("AppIds", []) or []) + (manager.config_data.get("AdditionalApps", []) or [])
            config_app_ids = {int(x) for x in raw_app_ids if x}

            from src.utils.paths import get_installed_apps
            installed = get_installed_apps()
            app_ids = config_app_ids | set(installed.keys())

            if not app_ids:
                self.empty_widget.show()
                self.card_games._val_label.setText("0 Games")
                self.card_luas._val_label.setText("0 Active")
                self.card_size._val_label.setText("0.00 GB")
                return

            self.empty_widget.hide()
            # Real stats calculation
            self._update_storage_stats(installed)

            # Fetch game details asynchronously
            loop = get_async_loop()
            self._load_generation += 1
            loop.create_task(self._fetch_and_display_library(app_ids, installed))

        except Exception as e:
            self.empty_title.setText("Error Loading Library")
            self.empty_sub.setText(str(e))
            self.empty_widget.show()

    def _update_storage_stats(self, installed: dict) -> None:
        from pathlib import Path
        import os
        from src.ui.game_card import get_installed_game_path

        def _get_folder_size(path: Path) -> int:
            total = 0
            try:
                for entry in os.scandir(path):
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat().st_size
                    elif entry.is_dir(follow_symlinks=False):
                        total += _get_folder_size(Path(entry.path))
            except Exception:
                pass
            return total

        installed_bytes = 0
        installed_count = 0
        for app_id in installed.keys():
            p = get_installed_game_path(app_id)
            if p and Path(p).exists():
                installed_count += 1
                installed_bytes += _get_folder_size(Path(p))

        size_gb = installed_bytes / (1024 ** 3)
        self.card_size._val_label.setText(f"{size_gb:.2f} GB")
        self.card_size._desc_label.setText(f"{installed_count} Games Installed on Disk")
        self.card_luas._val_label.setText(f"{installed_count} Active")
    async def _fetch_and_display_library(self, app_ids: set, installed_names: dict) -> None:
        import httpx

        generation = self._load_generation
        total_valid_games = 0
        async with httpx.AsyncClient() as client:
            for app_id in sorted(app_ids):
                if generation != self._load_generation:
                    return
                
                title = installed_names.get(app_id)
                image_url = ""
                is_dlc = False

                # Query Steam appdetails to get name and verify app type
                try:
                    steam_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
                    response = await client.get(steam_url, timeout=5.0)
                    if response.status_code == 200:
                        app_data = response.json().get(str(app_id), {})
                        if app_data.get("success"):
                            data = app_data.get("data", {})
                            app_type = data.get("type", "game")
                            if app_type in ("dlc", "music", "demo", "advertising"):
                                is_dlc = True
                            if not title:
                                title = data.get("name", f"App {app_id}")
                except Exception as e:
                    print(f"Error fetching metadata for {app_id}: {e}")

                # Skip DLCs from being displayed as standalone game cards in the library
                if is_dlc:
                    continue

                if not title:
                    title = f"App {app_id}"

                if generation != self._load_generation:
                    return

                total_valid_games += 1
                self.card_games._val_label.setText(f"{total_valid_games} Games")

                card = GameCard(app_id, title, image_url, mode="library")
                card.download_requested.connect(self.download_requested.emit)
                card.uninstalled.connect(lambda _app_id: self.load_library())
                card.cloud_status_changed.connect(self._on_card_cloud_changed)
                
                self._all_cards.append(card)
                self.grid_layout.addWidget(card)

        if total_valid_games == 0 and not installed_names:
            self.empty_widget.show()
            self.card_games._val_label.setText("0 Games")
    def _filter_cards(self) -> None:
        query = self.search_input.text().lower().strip()
        cat = self.combo_category.currentText()

        for card in self._all_cards:
            match_query = (not query) or (query in card.title.lower()) or (query in str(card.app_id))
            
            match_cat = True
            if cat == "Installed Only":
                match_cat = bool(getattr(card, '_installed_path', None))
            elif cat == "Lua Config Only":
                match_cat = not bool(getattr(card, '_installed_path', None))
            elif cat == "Hidden":
                match_cat = card.is_hidden()

            if match_query and match_cat:
                card.show()
            else:
                card.hide()
    def _on_card_cloud_changed(self, app_id: int, is_on: bool) -> None:
        """Called when a game card's cloud status changes."""
        # Find the card and update its button style
        for card in self._all_cards:
            if card.app_id == app_id:
                card._update_cloud_btn_style()
                break
