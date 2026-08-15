import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse, unquote

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
                               QDialog, QListWidget, QListWidgetItem, QDialogButtonBox,
                               QMessageBox, QFileDialog)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QUrl, Signal, QTimer
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from src.utils.async_utils import get_async_loop
from src.api.onlinefix import onlinefix_api, OnlineFixError, OnlineFixNotFoundError
from src.api.freetp import freetp_api
from src.api.unified_fix import UnifiedFixFetcher
from src.utils.onlinefix_patcher import OnlineFixPatcher


def get_installed_game_path(app_id: int):
    from src.utils.paths import get_steam_libraries
    import vdf
    for lib in get_steam_libraries():
        acf = Path(lib) / "steamapps" / f"appmanifest_{app_id}.acf"
        if acf.exists():
            try:
                with open(acf, 'r', encoding='utf-8') as f:
                    data = vdf.load(f)
                    installdir = data.get("AppState", {}).get("installdir", "")
                    if installdir:
                        return str(Path(lib) / "steamapps" / "common" / installdir)
            except Exception:
                pass
    return None


class GameCard(QFrame):
    """
    Redesigned Gaming Card featuring vertical cover art with fallback chain,
    SteamGridDB resolution, status pills, and contextual action buttons.
    """
    download_requested = Signal(int, str)
    uninstalled = Signal(int)
    image_load_failed = Signal(object)
    cloud_status_changed = Signal(int, bool)  # app_id, is_enabled
    def __init__(self, app_id: int, title: str, image_url: str = "", mode: str = "search") -> None:
        super().__init__()
        try:
            self.app_id = int(app_id)
        except (ValueError, TypeError):
            self.app_id = 0
        self.title = title
        self.image_url = image_url
        self.mode = mode
        self._hidden = False  # For manual library filtering
        self.setObjectName("GameCard")
        self.setFixedSize(230, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(6)

        # =====================================================================
        # COVER ART & BADGES
        # =====================================================================
        self.image_label = QLabel()
        self.image_label.setObjectName("GameCardImage")
        self.image_label.setFixedSize(230, 310)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setText("Loading...")
        layout.addWidget(self.image_label)

        # Top Badge Overlay
        if self.mode == "store":
            self.badge = QLabel("✨ Available", self.image_label)
            self.badge.setStyleSheet("""
                background-color: rgba(5, 150, 105, 0.85);
                color: #FFFFFF;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 10px;
                font-weight: 800;
            """)
            self.badge.move(140, 10)
        elif self.mode == "library":
            installed_path = get_installed_game_path(self.app_id)
            self._installed_path = installed_path
            
            self.badge = QLabel("✓ Installed" if installed_path else "⚡ Lua", self.image_label)
            bg_color = "rgba(16, 185, 129, 0.85)" if installed_path else "rgba(99, 102, 241, 0.85)"
            self.badge.setStyleSheet(f"""
                background-color: {bg_color};
                color: #FFFFFF;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 10px;
                font-weight: 800;
            """)
            self.badge.move(145 if installed_path else 165, 10)

        # =====================================================================
        # TITLE
        # =====================================================================
        self.title_label = QLabel(self.title)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-weight: 700; font-size: 13px; padding: 0 10px; color: #FFFFFF;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFixedHeight(36)
        layout.addWidget(self.title_label)

        # =====================================================================
        # ACTION BUTTONS (Contextual)
        # =====================================================================
        btn_container = QVBoxLayout()
        btn_container.setContentsMargins(10, 0, 10, 0)
        btn_container.setSpacing(6)

        if self.mode in ("search", "store"):
            from src.config.settings import SettingsManager
            mode = SettingsManager.get("steam_integration_mode", "classic")
            
            if mode == "moon":
                # Moon mode: Multiple action buttons
                moon_btn_layout = QVBoxLayout()
                moon_btn_layout.setSpacing(6)
                
                # Main action: Add to Steam
                self.btn_download = QPushButton("➕ Add to Steam (Moon)")
                self.btn_download.setProperty("cssClass", "PrimaryAction")
                self.btn_download.clicked.connect(self._add_to_library)
                moon_btn_layout.addWidget(self.btn_download)
                
                # Secondary: Add + Fix (Moon)
                self.btn_add_fix = QPushButton("🔧 Add + Fix (Moon)")
                self.btn_add_fix.setProperty("cssClass", "SecondaryAction")
                self.btn_add_fix.clicked.connect(self._add_to_library_with_fix)
                moon_btn_layout.addWidget(self.btn_add_fix)
                
                # Tertiary: Add + DLC (Moon) - only show if DLCs available
                self.btn_add_dlc = QPushButton("📦 Add + DLC (Moon)")
                self.btn_add_dlc.setProperty("cssClass", "SecondaryAction")
                self.btn_add_dlc.clicked.connect(self._add_to_library_with_dlc)
                self.btn_add_dlc.setVisible(False)  # Hidden by default, shown when DLCs detected
                moon_btn_layout.addWidget(self.btn_add_dlc)
                
                btn_container.addLayout(moon_btn_layout)
            else:
                self.btn_download = QPushButton("➕ Add to Library")
                self.btn_download.setProperty("cssClass", "PrimaryAction")
                self.btn_download.clicked.connect(self._add_to_library)
                btn_container.addWidget(self.btn_download)
        elif self.mode == "library":
            installed_path = getattr(self, '_installed_path', None)

            if installed_path:
                # Primary action: PLAY
                self.btn_play = QPushButton("▶  Play")
                self.btn_play.setProperty("cssClass", "PrimaryAction")
                self.btn_play.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10B981);
                        color: #FFFFFF;
                        font-weight: 700;
                        font-size: 13px;
                        border-radius: 6px;
                        padding: 7px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #34D399);
                    }
                """)
                self.btn_play.clicked.connect(self._launch_game)
                btn_container.addWidget(self.btn_play)

                # Sub Row 1: Fix & Cloud
                sub_row1 = QHBoxLayout()
                sub_row1.setSpacing(4)

                self.btn_apply_fix = QPushButton("🔧 Fix")
                self.btn_apply_fix.setProperty("cssClass", "SecondaryAction")
                self.btn_apply_fix.clicked.connect(self._apply_fix_auto)
                sub_row1.addWidget(self.btn_apply_fix)

                self.btn_cloud = QPushButton("☁ Cloud")
                self.btn_cloud.setProperty("cssClass", "SecondaryAction")
                self.btn_cloud.clicked.connect(self._toggle_cloud_save)
                self._update_cloud_btn_style()
                sub_row1.addWidget(self.btn_cloud)
                btn_container.addLayout(sub_row1)

                # Sub Row 2: Re-dl & Uninstall
                sub_row2 = QHBoxLayout()
                sub_row2.setSpacing(4)

                from src.config.settings import SettingsManager
                mode = SettingsManager.get("steam_integration_mode", "classic")
                if mode != "moon":
                    self.btn_download = QPushButton("⚡ Re-dl")
                self.btn_uninstall = QPushButton("🗑 Delete")
                self.btn_uninstall.setProperty("cssClass", "DangerAction")
                self.btn_uninstall.clicked.connect(self._uninstall_game)
                sub_row2.addWidget(self.btn_uninstall)
                btn_container.addLayout(sub_row2)
            else:
                from src.config.settings import SettingsManager
                mode = SettingsManager.get("steam_integration_mode", "classic")
                if mode == "moon":
                    self.btn_download = QPushButton("➕ Install via Steam (Moon)")
                    self.btn_download.setProperty("cssClass", "PrimaryAction")
                    self.btn_download.clicked.connect(self._add_to_library)
                else:
                    self.btn_download = QPushButton("⬇  Download")
                    self.btn_download.setProperty("cssClass", "PrimaryAction")
                    self.btn_download.clicked.connect(self._request_download)
                btn_container.addWidget(self.btn_download)

                self.btn_uninstall = QPushButton("✕  Remove from list")
                self.btn_uninstall.setProperty("cssClass", "DangerAction")
                self.btn_uninstall.clicked.connect(self._uninstall_game)
                btn_container.addWidget(self.btn_uninstall)
        # Context menu for library items (both installed and not installed)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        layout.addLayout(btn_container)

        # Network Manager for Image Loading
        self.network_manager = QNetworkAccessManager(self)
        self.network_manager.finished.connect(self._on_image_loaded)

        if self.app_id and self.app_id != 0:
            self._fetch_image()
        else:
            self.image_label.setText("No Image")

    # =========================================================================
    # IMAGE FETCHING & STEAMGRIDDB
    # =========================================================================
    def _fetch_image(self, index: int = 0) -> None:
        if not hasattr(self, 'image_urls'):
            self.image_urls = [
                f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{self.app_id}/library_600x900.jpg",
                f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{self.app_id}/header.jpg",
                f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{self.app_id}/capsule_616x353.jpg",
            ]
            if self.image_url and self.image_url not in self.image_urls:
                self.image_urls.append(self.image_url)

        if index == 0:
            from src.config.settings import SettingsManager
            sgdb_key = SettingsManager.get("steamgriddb_api_key", "")
            if sgdb_key:
                get_async_loop().create_task(self._resolve_and_fetch_sgdb(sgdb_key))
                return

        self._start_network_fetch(index)

    async def _resolve_and_fetch_sgdb(self, api_key: str) -> None:
        try:
            import httpx
            url = f"https://www.steamgriddb.com/api/v2/grids/steam/{self.app_id}?dimensions=600x900&types=static"
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(url, headers=headers, timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success") and data.get("data"):
                        grids = sorted(data["data"], key=lambda g: g.get("score", 0), reverse=True)
                        if grids and grids[0].get("url"):
                            self.image_urls.insert(0, grids[0]["url"])
        except Exception as e:
            pass

        self._start_network_fetch(0)

    def _start_network_fetch(self, index: int) -> None:
        try:
            if index < len(self.image_urls):
                self.current_url_index = index
                request = QNetworkRequest(QUrl(self.image_urls[index]))
                if hasattr(self, 'network_manager') and self.network_manager:
                    self.network_manager.get(request)
            else:
                if not getattr(self, '_steam_fallback_tried', False):
                    self._steam_fallback_tried = True
                    get_async_loop().create_task(self._fetch_steam_api_fallback())
                else:
                    self.image_label.setText("No Image")
                    self.image_load_failed.emit(self)
        except (RuntimeError, Exception):
            pass

    async def _fetch_steam_api_fallback(self) -> None:
        try:
            import httpx
            url = f"https://store.steampowered.com/api/appdetails?appids={self.app_id}"
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(url, timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    app_data = data.get(str(self.app_id), {})
                    if app_data.get("success") and "data" in app_data:
                        game_data = app_data["data"]
                        fallback_img = game_data.get("header_image") or game_data.get("capsule_image")
                        if fallback_img and fallback_img not in self.image_urls:
                            self.image_urls.append(fallback_img)
                            self._start_network_fetch(len(self.image_urls) - 1)
                            return
        except Exception as e:
            pass

        try:
            self.image_label.setText("No Image")
            self.image_load_failed.emit(self)
        except Exception:
            pass

    def _on_image_loaded(self, reply: QNetworkReply) -> None:
        try:
            status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
            if reply.error() == QNetworkReply.NetworkError.NoError and status_code == 200:
                image_data = reply.readAll()
                image = QImage()
                image.loadFromData(image_data)

                pixmap = QPixmap(image).scaled(
                    230, 310,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_label.setPixmap(pixmap)
                self.image_label.setText("")
            else:
                self._fetch_image(getattr(self, 'current_url_index', 0) + 1)
        except (RuntimeError, Exception):
            pass
        finally:
            reply.deleteLater()
    # =========================================================================
    # ACTIONS: LIBRARY & FIX PATCHING
    # =========================================================================
    def _add_to_library(self) -> None:
        self.btn_download.setText("Processing...")
        self.btn_download.setEnabled(False)
        loop = get_async_loop()
        loop.create_task(self._async_add_to_library())

    async def _async_add_to_library(self) -> None:
        try:
            from src.config.settings import SettingsManager
            mode = SettingsManager.get("steam_integration_mode", "classic")
            
            if mode == "moon":
                from src.services.download import DownloadManager
                success = await DownloadManager.inject_lua_to_steam(self.app_id)
                if success:
                    self.btn_download.setText("✓ In Steam")
                    self.btn_download.setStyleSheet("background-color: #059669; color: white;")
                    # Open Steam install dialog directly
                    import subprocess
                    subprocess.Popen(["xdg-open", f"steam://install/{self.app_id}"], start_new_session=True)
                    QMessageBox.information(self, "Moon Engine", 
                        f"{self.title} injected to Steam.\nSteam download dialog should open automatically.\nIf not, restart Steam and check Library.")
                else:
                    raise Exception("Failed to inject Lua into Steam.")
            else:
                from src.services.download import DownloadManager
                await DownloadManager.prepare_game_data(self.app_id, scope="full")
                self.btn_download.setText("✓ In Library")
                self.btn_download.setStyleSheet("background-color: #059669; color: white;")
        except Exception as e:
            self.btn_download.setText("Error")
            self.btn_download.setEnabled(True)
            print(f"Error adding to library: {e}")

    async def _async_add_to_library_with_fix(self) -> None:
        """Moon mode: Inject Lua with fix pre-selected, then open Steam install."""
        try:
            from src.config.settings import SettingsManager
            from src.services.download import DownloadManager
            
            # First, inject Lua
            success = await DownloadManager.inject_lua_to_steam(self.app_id)
            if not success:
                raise Exception("Failed to inject Lua into Steam.")
            
            # Fetch available fixes
            from src.api.unified_fix import UnifiedFixFetcher
            fixes = await UnifiedFixFetcher.get_available_fixes(self.title)
            
            if fixes:
                # Add Goldberg option
                fixes.append({
                    "source": "goldberg",
                    "title": "Remove Steam DRM (Singleplayer / Offline Only)",
                    "version": "Auto",
                    "url": ""
                })
                
                from src.ui.fix_pick_dialog import FixPickDialog
                from PySide6.QtWidgets import QDialog
                dlg = FixPickDialog(fixes, self)
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    best_fix = dlg.get_selected_fix()
                    if best_fix:
                        source = best_fix["source"]
                        # Download and apply fix to temp, then Steam will pick it up
                        # For Moon mode, the fix will be applied via launch options
                        from src.config.slssteam import SLSsteamConfigManager
                        SLSsteamConfigManager().apply_fix_launch_options(self.app_id, source)
            
            # Update button state
            self.btn_add_fix.setText("✓ Fix Ready")
            self.btn_add_fix.setStyleSheet("background-color: #059669; color: white;")
            
            # Open Steam install
            import subprocess
            subprocess.Popen(["xdg-open", f"steam://install/{self.app_id}"], start_new_session=True)
            QMessageBox.information(self, "Moon Engine + Fix", 
                f"{self.title} injected to Steam with fix pre-configured.\nSteam download dialog should open automatically.")
                
        except Exception as e:
            self.btn_add_fix.setText("Error")
            self.btn_add_fix.setEnabled(True)
            print(f"Error adding with fix: {e}")

    async def _async_add_to_library_with_dlc(self) -> None:
        """Moon mode: Inject Lua + open Steam install with DLCs."""
        try:
            from src.config.settings import SettingsManager
            from src.services.download import DownloadManager
            
            # Inject Lua
            success = await DownloadManager.inject_lua_to_steam(self.app_id)
            if not success:
                raise Exception("Failed to inject Lua into Steam.")
            
            # Fetch game data with DLCs
            game_data = await DownloadManager.prepare_game_data(self.app_id, scope="full")
            dlcs = game_data.get("dlcs", {})
            
            if dlcs:
                # Build steam://install URL with DLCs
                dlc_ids = ",".join(str(dlc_id) for dlc_id in dlcs.keys())
                install_url = f"steam://install/{self.app_id},{dlc_ids}"
            else:
                install_url = f"steam://install/{self.app_id}"
            
            # Update button state
            self.btn_add_dlc.setText("✓ DLC Ready")
            self.btn_add_dlc.setStyleSheet("background-color: #059669; color: white;")
            
            # Open Steam install with DLCs
            import subprocess
            subprocess.Popen(["xdg-open", install_url], start_new_session=True)
            QMessageBox.information(self, "Moon Engine + DLC", 
                f"{self.title} injected to Steam with {len(dlcs)} DLC(s).\nSteam download dialog should open automatically.")
                
        except Exception as e:
            self.btn_add_dlc.setText("Error")
            self.btn_add_dlc.setEnabled(True)
            print(f"Error adding with DLC: {e}")
    def _add_to_library_with_fix(self) -> None:
        """Sync wrapper for async _async_add_to_library_with_fix."""
        self.btn_add_fix.setText("Processing...")
        self.btn_add_fix.setEnabled(False)
        loop = get_async_loop()
        loop.create_task(self._async_add_to_library_with_fix())

    def _add_to_library_with_dlc(self) -> None:
        """Sync wrapper for async _async_add_to_library_with_dlc."""
        self.btn_add_dlc.setText("Processing...")
        self.btn_add_dlc.setEnabled(False)
        loop = get_async_loop()
        loop.create_task(self._async_add_to_library_with_dlc())

    def _request_download(self) -> None:
        from src.config.settings import SettingsManager
        mode = SettingsManager.get("steam_integration_mode", "classic")
        if mode == "moon":
            self._add_to_library()
        else:
            self.download_requested.emit(self.app_id, self.title)

    def _apply_fix_auto(self) -> None:
        target_path = getattr(self, '_installed_path', None)

        if not target_path or not Path(target_path).exists():
            default_dir = str(Path.home() / ".local/share/Steam/steamapps/common")
            target_path = QFileDialog.getExistingDirectory(self, "Select Game Folder", default_dir)

        if not target_path:
            return

        self._fix_target_path = target_path
        self.btn_apply_fix.setEnabled(False)
        self._start_fix_download()
    def _start_fix_download(self) -> None:
        self.btn_apply_fix.setText("Fetching...")
        get_async_loop().create_task(self._async_fetch_and_apply_fix())

    async def _async_fetch_and_apply_fix(self) -> None:
        target_path = getattr(self, '_fix_target_path', None)
        if not target_path:
            return

        try:
            self.btn_apply_fix.setText("Searching...")
            fixes = await UnifiedFixFetcher.get_available_fixes(self.title)
            
            # UnifiedFixFetcher already adds Goldberg, no need to add again

            from src.ui.fix_pick_dialog import FixPickDialog
            dlg = FixPickDialog(fixes, self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                self.btn_apply_fix.setText("🔧 Fix")
                self.btn_apply_fix.setEnabled(True)
                return

            best_fix = dlg.get_selected_fix()
            if not best_fix:
                self.btn_apply_fix.setText("🔧 Fix")
                self.btn_apply_fix.setEnabled(True)
                return
            source = best_fix["source"]
            self.btn_apply_fix.setText(f"Applying ({source})...")

            if source == "goldberg":
                from src.services.drm_manager import DRMManager
                DRMManager.apply_goldberg(str(self.app_id), target_path)
            elif source == "ryuu":
                url = best_fix["url"]
                import httpx
                from src.config.settings import SettingsManager
                dest = Path(tempfile.gettempdir()) / f"ryuu_{self.app_id}_fix.zip"
                headers = {}
                ryuu_key = SettingsManager.get("ryuu_api_key", "").strip()
                if ryuu_key:
                    headers["X-Auth-Key"] = ryuu_key
                async with httpx.AsyncClient(follow_redirects=True, timeout=120.0, headers=headers) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    dest.write_bytes(resp.content)
                from src.utils.onlinefix_patcher import OnlineFixPatcher
                OnlineFixPatcher.apply_patch_from_archive(str(dest), str(self.app_id), target_path, password="")
            elif source == "onlinefix":
                game_url = best_fix["url"]
                page = await onlinefix_api.get_game_page(game_url)
                hoster_url = page.get("hoster_link")
                if hoster_url:
                    game_name = unquote(urlparse(hoster_url).path.strip("/"))
                    entries = await onlinefix_api.get_fix_entries(game_name)
                    fix = onlinefix_api.pick_fix(entries)
                    if fix:
                        direct, cookies = await onlinefix_api.resolve_direct(fix)
                        dest = Path(tempfile.gettempdir()) / f"ofme_{self.app_id}_{fix['file_name']}"
                        await onlinefix_api.download(direct, str(dest), cookies)
                        OnlineFixPatcher.apply_patch_from_archive(str(dest), str(self.app_id), target_path)
                    else:
                        OnlineFixPatcher.apply_patch(str(self.app_id), target_path)
                else:
                    OnlineFixPatcher.apply_patch(str(self.app_id), target_path)
            elif source == "crackbypass":
                # Use the new provider interface
                from src.api.crackbypass import crackbypass_api
                import tempfile
                with tempfile.TemporaryDirectory() as tmpdir:
                    extracted = await crackbypass_api.download_fix(best_fix, tmpdir)
                    if extracted:
                        from src.utils.onlinefix_patcher import OnlineFixPatcher
                        OnlineFixPatcher.apply_patch_from_archive(extracted, str(self.app_id), target_path)
                    else:
                        OnlineFixPatcher.apply_patch(str(self.app_id), target_path)
            else:
                dest_dir = Path(tempfile.gettempdir())
                dest_file = await freetp_api.download_fix(best_fix["url"], dest_dir)
                if dest_file:
                    OnlineFixPatcher.apply_freetp_exe(str(dest_file), str(self.app_id), target_path)
                else:
                    OnlineFixPatcher.apply_patch(str(self.app_id), target_path)

            # Apply launch options so fix works from Steam client without restart
            from src.config.slssteam import SLSsteamConfigManager
            SLSsteamConfigManager().apply_fix_launch_options(self.app_id, source)

            QMessageBox.information(
                self, "Success",
                f"Fix ({source}) applied successfully!\nLaunch options updated - no Steam restart needed!"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply fix: {e}")
        finally:
            self.btn_apply_fix.setText("🔧 Fix")
            self.btn_apply_fix.setEnabled(True)

    def _uninstall_game(self) -> None:
        from src.services.uninstall import UninstallManager
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self, "Uninstall",
            f"Are you sure you want to remove '{self.title}' (AppID: {self.app_id})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        success, error = UninstallManager.uninstall_game(self.app_id)
        if success:
            self.uninstalled.emit(self.app_id)
        else:
            QMessageBox.warning(self, "Error", f"Failed to uninstall: {error}")
    def _launch_game(self) -> None:
        """Launches the game via Steam protocol."""
        import shutil
        steam_cmd = "steam"
        try:
            subprocess.Popen(["xdg-open", f"steam://rungameid/{self.app_id}"], start_new_session=True)
        except Exception as e:
            try:
                subprocess.Popen([steam_cmd, f"steam://rungameid/{self.app_id}"], start_new_session=True)
            except Exception as err:
                QMessageBox.warning(self, "Launch Error", f"Failed to launch game: {err}")

    def _is_cloud_enabled_for_game(self) -> bool:
        """Checks if CloudRedirect LD_PRELOAD is active for this game."""
        from src.utils.vdf_parser import LocalConfigManager
        from src.services.cloud_redirect import CR_SO_PATH
        manager = LocalConfigManager()
        opts = manager.get_launch_options(str(self.app_id)) or ""
        return str(CR_SO_PATH.name) in opts or "cloud_redirect.so" in opts

    def _update_cloud_btn_style(self) -> None:
        """Updates the Cloud button appearance based on its hook status."""
        if not hasattr(self, 'btn_cloud'):
            return
        is_active = self._is_cloud_enabled_for_game()
        if is_active:
            self.btn_cloud.setText("☁ Cloud: ON")
            self.btn_cloud.setStyleSheet("""
                QPushButton {
                    background-color: rgba(16, 185, 129, 0.2);
                    color: #10B981;
                    border: 1px solid #10B981;
                    font-weight: 700;
                    font-size: 11px;
                    border-radius: 6px;
                    padding: 5px;
                }
            """)
        else:
            self.btn_cloud.setText("☁ Cloud: OFF")
            self.btn_cloud.setStyleSheet("""
                QPushButton {
                    background-color: #1A1F30;
                    color: #94A3B8;
                    border: 1px solid #283252;
                    font-size: 11px;
                    border-radius: 6px;
                    padding: 5px;
                }
            """)

    def _toggle_cloud_save(self) -> None:
        """Toggles CloudRedirect hook for this game."""
        from src.services.cloud_redirect import CloudRedirectManager
        if not CloudRedirectManager.is_installed():
            reply = QMessageBox.question(
                self, "CloudRedirect Hook Missing",
                "CloudRedirect hook is not installed yet. Would you like to install it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                get_async_loop().create_task(self._async_install_and_enable_cloud())
            return

        is_active = self._is_cloud_enabled_for_game()
        if is_active:
            CloudRedirectManager.remove_game_hook(self.app_id)
        self._update_cloud_btn_style()
        self.cloud_status_changed.emit(self.app_id, not is_active)
    async def _async_install_and_enable_cloud(self) -> None:
        from src.services.cloud_redirect import CloudRedirectManager
        try:
            await CloudRedirectManager.ensure_installed()
            CloudRedirectManager.apply_game_hook(self.app_id)
            self._update_cloud_btn_style()
            QMessageBox.information(self, "Success", f"CloudRedirect installed and enabled for {self.title}!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to setup CloudRedirect: {e}")
    def set_hidden(self, hidden: bool) -> None:
        """Set hidden state for manual library filtering."""
        self._hidden = hidden
        self.setVisible(not hidden)

    def is_hidden(self) -> bool:
        return self._hidden
    def _show_context_menu(self, pos) -> None:
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        
        if self.is_hidden():
            show_action = menu.addAction("👁  Show in Library")
            show_action.triggered.connect(lambda: self.set_hidden(False))
        else:
            hide_action = menu.addAction("🙈  Hide from Library")
            hide_action.triggered.connect(lambda: self.set_hidden(True))
        
        menu.exec(self.mapToGlobal(pos))
