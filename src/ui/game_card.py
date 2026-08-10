from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from src.config.slssteam import SLSsteamConfigManager
from src.services.download import DownloadManager

class GameCard(QFrame):
    """
    A visual card representing a single game in the library or search results.
    Fetches the cover art natively using QNetworkAccessManager.
    """
    def __init__(self, app_id: int, title: str, image_url: str = "", mode: str = "search") -> None:
        super().__init__()
        self.app_id = app_id
        self.title = title
        self.image_url = image_url
        self.mode = mode
        self.setObjectName("GameCard")
        # Increased height slightly to give buttons more breathing room
        self.setFixedSize(200, 320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(5)

        # Image Label
        self.image_label = QLabel()
        self.image_label.setObjectName("GameCardImage")
        self.image_label.setStyleSheet("background-color: #1B2027; border-top-left-radius: 12px; border-top-right-radius: 12px;")
        self.image_label.setFixedSize(200, 240)
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
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(10, 0, 10, 0)

        if self.mode == "search":
            self.btn_download = QPushButton("Queue")
            self.btn_download.setProperty("cssClass", "PrimaryAction")
            self.btn_download.clicked.connect(self._queue_download)

            btn_layout.addWidget(self.btn_download)
        elif self.mode == "store":
            self.badge = QLabel("Available", self.image_label)
            self.badge.setStyleSheet("background-color: #238636; color: white; padding: 4px 8px; border-radius: 4px; font-size: 10px; font-weight: bold;")
            self.badge.move(135, 10)

            self.btn_download = QPushButton("Download")
            self.btn_download.setProperty("cssClass", "PrimaryAction")
            self.btn_download.clicked.connect(self._queue_download)

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
            self.btn_remove_lib = QPushButton("Delete Lua")
            self.btn_remove_lib.setProperty("cssClass", "SecondaryAction")
            self.btn_remove_lib.setStyleSheet("background-color: #DA3633; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: 600;")
            self.btn_remove_lib.clicked.connect(self._remove_from_library)

            self.btn_uninstall = QPushButton("Uninstall")
            self.btn_uninstall.setProperty("cssClass", "PrimaryAction")
            self.btn_uninstall.clicked.connect(self._download_game) # Existing download trigger logic can be reused or replaced later

            btn_layout.addWidget(self.btn_remove_lib)
            btn_layout.addWidget(self.btn_uninstall)
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
                import asyncio
                asyncio.get_event_loop().create_task(self._resolve_and_fetch_sgdb(sgdb_key))
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
                200, 240,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(pixmap)
            self.image_label.setText("")
        else:
            self._fetch_image(getattr(self, 'current_url_index', 0) + 1)

        reply.deleteLater()
    def _remove_from_queue(self) -> None:
        try:
            from src.config.settings import SettingsManager
            queue = SettingsManager.get("download_queue", [])
            queue = [g for g in queue if g.get("app_id") != self.app_id]
            SettingsManager.set("download_queue", queue)
            self.hide() # visually remove the card
        except Exception as e:
            print(f"Error removing from queue: {e}")

    def _commit_and_download(self) -> None:
        """Commits the game to the library (SLSsteam config), writes VDF keys, and triggers Steam."""
        self.btn_commit.setText("Processing...")
        self.btn_commit.setEnabled(False)
        import asyncio
        loop = asyncio.get_event_loop()
        loop.create_task(self._async_commit())

    async def _async_commit(self) -> None:
        try:
            from src.config.settings import SettingsManager
            from src.services.download import DownloadManager
            
            # 1. API üzerinden çek, manifestleri hazırla ve config'e ekle
            depots = await DownloadManager.prepare_game_data(self.app_id)
            
            download_method = SettingsManager.get("download_method", "steam")
            
            if download_method == "ddmod":
                self.btn_commit.setText("Downloading...")
                for depot in depots:
                    depot_id = depot.get("depot_id")
                    man_id = depot.get("manifest_id")
                    if depot_id and man_id:
                        async for progress in DownloadManager.install_via_ddmod(self.app_id, depot_id, man_id):
                            print(f"[{self.app_id}] DDMod: {progress}")
                
                self.btn_commit.setText("İndi")
            else:
                self.btn_commit.setText("Steam'i Yeniden Başlatın")
                
            # Visually and logically remove from queue (or keep it if you want to show 'İndi')
            # Biz arka planda işlem bittikten 2 saniye sonra listeden kaldıralım.
            import asyncio
            await asyncio.sleep(2)
            self._remove_from_queue()
        except Exception as e:
            self.btn_commit.setText("Error")
            self.btn_commit.setEnabled(True)
            print(f"Error committing download: {e}")

    def _queue_download(self) -> None:
        try:
            from src.config.settings import SettingsManager
            queue = SettingsManager.get("download_queue", [])
            if not any(g.get("app_id") == self.app_id for g in queue):
                queue.append({
                    "app_id": self.app_id,
                    "title": self.title,
                    "image_url": self.image_url
                })
                SettingsManager.set("download_queue", queue)

            self.btn_download.setText("Queued")
            self.btn_download.setEnabled(False)
            self.btn_download.setStyleSheet("background-color: #238636; color: #FFFFFF; border: none;")
        except Exception as e:
            self.btn_download.setText("Error")
            print(f"Error queueing download: {e}")

    def _remove_from_library(self) -> None:
        """Removes the game from the SLSsteam configuration and visually hides the card."""
        try:
            from src.config.slssteam import SLSsteamConfigManager
            manager = SLSsteamConfigManager()
            # Tip uyuşmazlıklarına ve YAML parser'ın boş değerleri None yapmasına karşı tam güvenlik
            manager.config_data["AdditionalApps"] = [x for x in (manager.config_data.get("AdditionalApps") or []) if str(x) != str(self.app_id)]
            manager.config_data["AppIds"] = [x for x in (manager.config_data.get("AppIds") or []) if str(x) != str(self.app_id)]
            manager.save()
            self.deleteLater() # Sadece gizlemek yerine widget'ı tamamen bellekten ve ekrandan sil
        except Exception as e:
            print(f"Error removing from library: {e}")

    def _download_game(self) -> None:
        """Triggers the download directly from the library using the selected engine."""
        self.btn_play.setText("Processing...")
        self.btn_play.setEnabled(False)
        import asyncio
        loop = asyncio.get_event_loop()
        loop.create_task(self._async_download_game())

    async def _async_download_game(self) -> None:
        try:
            from src.config.settings import SettingsManager
            from src.services.download import DownloadManager

            download_method = SettingsManager.get("download_method", "steam")

            # Extract manifests, inject keys, and update config
            depots = await DownloadManager.prepare_game_data(self.app_id)

            if download_method == "ddmod":
                self.btn_play.setText("Downloading...")
                for depot in depots:
                    depot_id = depot.get("depot_id")
                    man_id = depot.get("manifest_id")
                    if depot_id and man_id:
                        async for progress in DownloadManager.install_via_ddmod(self.app_id, depot_id, man_id):
                            print(f"[{self.app_id}] DDMod: {progress}")

                self.btn_play.setText("Install / Download")
                self.btn_play.setEnabled(True)
            else:
                # Steam metodu seçiliyse otomatik indirme tetikleme. Kullanıcıyı yeniden başlatmaya yönlendir.
                # DownloadManager.install_via_steam(self.app_id)
                self.btn_play.setText("Steam'i Yeniden Başlatın")
                self.btn_play.setEnabled(True)
        except Exception as e:
            self.btn_play.setText("Error")
            self.btn_play.setEnabled(True)
            print(f"Download Error: {e}")