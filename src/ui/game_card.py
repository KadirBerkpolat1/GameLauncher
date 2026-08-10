from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QUrl, Signal, QTimer
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from src.utils.async_utils import get_async_loop

def get_installed_game_path(app_id: int):
    from src.utils.paths import get_steam_libraries
    from pathlib import Path
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
            except:
                pass
    return None

class GameCard(QFrame):
    """
    A visual card representing a single game in the library or search results.
    Fetches the cover art natively using QNetworkAccessManager.
    """
    download_requested = Signal(int, str)
    uninstalled = Signal(int)

    def __init__(self, app_id: int, title: str, image_url: str = "", mode: str = "search") -> None:
        super().__init__()
        self.app_id = app_id
        self.title = title
        self.image_url = image_url
        self.mode = mode
        self.setObjectName("GameCard")
        # Enlarge card to fit 2:3 aspect ratio covers and vertical buttons
        self.setFixedSize(240, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(5)

        # Image Label
        self.image_label = QLabel()
        self.image_label.setObjectName("GameCardImage")
        self.image_label.setStyleSheet("background-color: #1B2027; border-top-left-radius: 12px; border-top-right-radius: 12px;")
        self.image_label.setFixedSize(240, 360)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setText("Loading...")
        layout.addWidget(self.image_label)

        # Title
        self.title_label = QLabel(self.title)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-weight: bold; padding: 0 10px; color: #FFFFFF;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # Action Buttons (Contextual based on mode)
        btn_layout = QVBoxLayout() if self.mode == "library" else QHBoxLayout()
        btn_layout.setContentsMargins(10, 0, 10, 0)

        if self.mode == "search":
            self.btn_download = QPushButton("Add to Library")
            self.btn_download.setProperty("cssClass", "PrimaryAction")
            self.btn_download.clicked.connect(self._add_to_library)

            btn_layout.addWidget(self.btn_download)
        elif self.mode == "store":
            self.badge = QLabel("Available", self.image_label)
            self.badge.setStyleSheet("background-color: #238636; color: white; padding: 4px 8px; border-radius: 4px; font-size: 10px; font-weight: bold;")
            self.badge.move(175, 10)

            self.btn_download = QPushButton("Add to Library")
            self.btn_download.setProperty("cssClass", "PrimaryAction")
            self.btn_download.clicked.connect(self._add_to_library)

            btn_layout.addWidget(self.btn_download)
        elif self.mode == "queued":
            self.btn_commit = QPushButton("Download")
            self.btn_commit.setProperty("cssClass", "PrimaryAction")
            self.btn_commit.clicked.connect(self._commit_and_download)

            self.btn_remove = QPushButton("Remove")
            self.btn_remove.setProperty("cssClass", "SecondaryAction")
            self.btn_remove.clicked.connect(self._remove_from_queue)

            btn_layout.addWidget(self.btn_remove)
            btn_layout.addWidget(self.btn_commit)
        elif self.mode == "library":
            self.btn_uninstall = QPushButton("Uninstall")
            self.btn_uninstall.setProperty("cssClass", "SecondaryAction")
            self.btn_uninstall.setStyleSheet("background-color: #DA3633; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: 600;")
            self.btn_uninstall.clicked.connect(self._uninstall_game)

            self.btn_download = QPushButton("Download")
            self.btn_download.setProperty("cssClass", "PrimaryAction")
            self.btn_download.clicked.connect(self._request_download)

            btn_layout.addWidget(self.btn_uninstall)
            btn_layout.addWidget(self.btn_download)
            installed_path = get_installed_game_path(self.app_id)
            if installed_path:
                self.btn_apply_fix = QPushButton("Apply Fix")
                self.btn_apply_fix.clicked.connect(self._apply_fix_auto)
                btn_layout.addWidget(self.btn_apply_fix)
            self._installed_path = installed_path
        layout.addLayout(btn_layout)

        # Network Manager for Image Downloading
        self.network_manager = QNetworkAccessManager(self)
        self.network_manager.finished.connect(self._on_image_loaded)

        if self.app_id and self.app_id != 0:
            self._fetch_image()
        else:
            self.image_label.setText("No Image")

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
            url = f"https://www.steamgriddb.com/api/v2/grids/game/steam/{self.app_id}?dimensions=600x900"
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(url, headers=headers, timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success") and data.get("data"):
                        sgdb_image_url = data["data"][0]["url"]
                        self.image_urls.insert(0, sgdb_image_url)
        except Exception as e:
            print(f"SteamGridDB API error for {self.app_id}: {e}")
        
        self._start_network_fetch(0)

    def _start_network_fetch(self, index: int) -> None:
        if index < len(self.image_urls):
            self.current_url_index = index
            request = QNetworkRequest(QUrl(self.image_urls[index]))
            self.network_manager.get(request)
        else:
            self.image_label.setText("No Image Available")

    def _on_image_loaded(self, reply: QNetworkReply) -> None:
        status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        if reply.error() == QNetworkReply.NetworkError.NoError and status_code == 200:
            image_data = reply.readAll()
            image = QImage()
            image.loadFromData(image_data)

            pixmap = QPixmap(image).scaled(
                240, 360,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(pixmap)
            self.image_label.setText("")
        else:
            self._fetch_image(getattr(self, 'current_url_index', 0) + 1)

        reply.deleteLater()
    def _add_to_library(self) -> None:
        self.btn_download.setText("Adding...")
        self.btn_download.setEnabled(False)
        
        loop = get_async_loop()
        loop.create_task(self._async_add_to_library())
        
    async def _async_add_to_library(self) -> None:
        try:
            from src.services.download import DownloadManager
            # prepare_game_data fetches the lua and updates SLSsteamConfigManager
            await DownloadManager.prepare_game_data(self.app_id, scope="full")
            self.btn_download.setText("Added to Library")
            self.btn_download.setStyleSheet("background-color: #238636; color: white;")
        except Exception as e:
            self.btn_download.setText("Error")
            self.btn_download.setEnabled(True)
            print(f"Error adding to library: {e}")
            
    def _request_download(self) -> None:
        self.download_requested.emit(self.app_id, self.title)

    def _apply_fix_auto(self) -> None:
        from src.utils.onlinefix_patcher import OnlineFixPatcher
        from PySide6.QtWidgets import QMessageBox
        OnlineFixPatcher.apply_patch(self.app_id, self._installed_path)
        QMessageBox.information(self, "Success", "OnlineFix applied successfully!")

    def _uninstall_game(self) -> None:
        from PySide6.QtWidgets import QMessageBox, QPushButton

        box = QMessageBox(self)
        box.setWindowTitle("Gelişmiş Kaldırma Seçenekleri")
        box.setText(f"{self.title} için neleri kaldırmak istiyorsunuz?")

        btn_both = box.addButton("Her İkisini Sil", QMessageBox.ButtonRole.AcceptRole)
        btn_game = box.addButton("Sadece Oyun Dosyalarını Sil", QMessageBox.ButtonRole.AcceptRole)
        btn_lua = box.addButton("Sadece Lua'yı (Kütüphaneden) Sil", QMessageBox.ButtonRole.AcceptRole)
        btn_cancel = box.addButton("İptal", QMessageBox.ButtonRole.RejectRole)

        box.exec()

        if box.clickedButton() == btn_cancel:
            return

        remove_files = box.clickedButton() in (btn_both, btn_game)
        remove_lua = box.clickedButton() in (btn_both, btn_lua)

        self.btn_uninstall.setEnabled(False)
        self.btn_uninstall.setText("Uninstalling...")

        def _run() -> None:
            try:
                from src.services.uninstall import uninstall_game
                summary = uninstall_game(self.app_id, remove_files=remove_files, remove_lua=remove_lua)
                QTimer.singleShot(0, lambda: self._on_uninstall_done(summary))
            except Exception as e:
                QTimer.singleShot(0, lambda: self._on_uninstall_error(str(e)))

        import threading
        threading.Thread(target=_run, daemon=True).start()

    def _on_uninstall_done(self, summary: dict) -> None:
        from PySide6.QtWidgets import QMessageBox
        details = []
        if summary.get("files"):
            details.append("Game files deleted")
        if summary.get("acf"):
            details.append("appmanifest deleted")
        if summary.get("prefix"):
            details.append("Proton prefix deleted")
        if summary.get("depotcache"):
            details.append(f"{summary['depotcache']} depotcache manifest(s) deleted")
        if summary.get("config"):
            details.append("Library entry removed")
        QMessageBox.information(
            self,
            "Uninstall Complete",
            f"\"{self.title}\" has been uninstalled.\n\n" + ("\n".join(details) if details else "Nothing found to delete."),
        )
        self.uninstalled.emit(self.app_id)
        self.deleteLater()

    def _on_uninstall_error(self, error: str) -> None:
        from PySide6.QtWidgets import QMessageBox
        self.btn_uninstall.setEnabled(True)
        self.btn_uninstall.setText("Uninstall")
        QMessageBox.warning(self, "Uninstall Failed", f"An error occurred:\n{error}")
