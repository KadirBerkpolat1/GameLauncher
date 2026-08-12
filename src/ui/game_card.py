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

    def __init__(self, app_id: int, title: str, image_url: str = "", mode: str = "search") -> None:
        super().__init__()
        self.app_id = app_id
        self.title = title
        self.image_url = image_url
        self.mode = mode
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
            self.btn_download = QPushButton("➕  Add to Library")
            self.btn_download.setProperty("cssClass", "PrimaryAction")
            self.btn_download.clicked.connect(self._add_to_library)
            btn_container.addWidget(self.btn_download)

        elif self.mode == "library":
            installed_path = getattr(self, '_installed_path', None)

            self.btn_download = QPushButton("⬇  Download" if not installed_path else "⚡ Re-download")
            self.btn_download.setProperty("cssClass", "PrimaryAction")
            self.btn_download.clicked.connect(self._request_download)
            btn_container.addWidget(self.btn_download)

            sub_row = QHBoxLayout()
            sub_row.setSpacing(6)

            if installed_path:
                self.btn_apply_fix = QPushButton("🔧  Fix")
                self.btn_apply_fix.setProperty("cssClass", "SecondaryAction")
                self.btn_apply_fix.clicked.connect(self._apply_fix_auto)
                sub_row.addWidget(self.btn_apply_fix)

            btn_text = "🗑  Uninstall" if installed_path else "✕  Delete"
            self.btn_uninstall = QPushButton(btn_text)
            self.btn_uninstall.setProperty("cssClass", "DangerAction")
            self.btn_uninstall.clicked.connect(self._uninstall_game)
            sub_row.addWidget(self.btn_uninstall)

            btn_container.addLayout(sub_row)

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
            url = f"https://www.steamgriddb.com/api/v2/grids/game/{self.app_id}?dimensions=600x900"
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(url, headers=headers, timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success") and data.get("data"):
                        grids = sorted(data["data"], key=lambda g: g.get("score", 0), reverse=True)
                        self.image_urls.insert(0, grids[0]["url"])
        except Exception as e:
            print(f"SteamGridDB error for {self.app_id}: {e}")

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
        self.btn_download.setText("Adding...")
        self.btn_download.setEnabled(False)
        loop = get_async_loop()
        loop.create_task(self._async_add_to_library())

    async def _async_add_to_library(self) -> None:
        try:
            from src.services.download import DownloadManager
            await DownloadManager.prepare_game_data(self.app_id, scope="full")
            self.btn_download.setText("✓ In Library")
            self.btn_download.setStyleSheet("background-color: #059669; color: white;")
        except Exception as e:
            self.btn_download.setText("Error")
            self.btn_download.setEnabled(True)
            print(f"Error adding to library: {e}")

    def _request_download(self) -> None:
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
        self.btn_apply_fix.setText("Closing Steam...")

        res = subprocess.run(["pgrep", "-x", "steam"], capture_output=True)
        if res.returncode == 0:
            subprocess.run(["steam", "-shutdown"], check=False)
            QTimer.singleShot(4000, self._start_fix_download)
        else:
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

            # Add Goldberg as an explicit offline choice
            fixes.append({
                "source": "goldberg",
                "title": "Remove Steam DRM (Singleplayer / Offline Only)",
                "version": "Auto",
                "url": ""
            })

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
            else:
                dest_dir = Path(tempfile.gettempdir())
                dest_file = await freetp_api.download_fix(best_fix["url"], dest_dir)
                if dest_file:
                    OnlineFixPatcher.apply_freetp_exe(str(dest_file), str(self.app_id), target_path)
                else:
                    OnlineFixPatcher.apply_patch(str(self.app_id), target_path)

            subprocess.Popen(["steam"], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            QMessageBox.information(self, "Success", f"Fix ({source}) applied and Steam restarted!")

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
