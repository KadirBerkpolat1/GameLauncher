from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QGridLayout, QPushButton
from PySide6.QtCore import Qt
from src.ui.game_card import GameCard
from src.ui.flow_layout import FlowLayout
from src.config.settings import SettingsManager

class DownloadsWidget(QWidget):
    """
    Acts as a staging area (queue) for games the user wants to download.
    Games added here are waiting to be installed to Steam and the Library.
    """
    def __init__(self) -> None:
        super().__init__()
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # --- Header ---
        header_layout = QVBoxLayout()
        header = QLabel("Downloads & History")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFFFFF;")
        
        # Status Indicator
        self.lbl_status = QLabel("Status: Idle")
        self.lbl_status.setStyleSheet("color: #58A6FF; font-weight: bold; font-size: 14px;")
        
        header_layout.addWidget(header)
        header_layout.addWidget(self.lbl_status)
        layout.addLayout(header_layout)

        # --- Action Bar ---
        action_bar = QWidget()
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_download_all = QPushButton("Install All Queued")
        self.btn_download_all.setProperty("cssClass", "PrimaryAction")
        self.btn_download_all.clicked.connect(self._process_queue)
        
        self.btn_clear_history = QPushButton("Clear History")
        self.btn_clear_history.setProperty("cssClass", "SecondaryAction")
        # self.btn_clear_history.clicked.connect(self._clear_history)

        action_layout.addWidget(self.btn_download_all)
        action_layout.addStretch()
        action_layout.addWidget(self.btn_clear_history)
        layout.addWidget(action_bar)

        # --- Grid Area (Queue) ---
        queue_lbl = QLabel("Queued For Installation")
        queue_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #DDDDDD;")
        layout.addWidget(queue_lbl)


        # Grid Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background-color: transparent;")

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background-color: transparent;")
        self.grid_layout = FlowLayout(self.grid_container, spacing=20)

        self.empty_label = QLabel("Queue is empty. Add games from the Search tab.")
        self.empty_label.setStyleSheet("color: #777777; font-size: 16px;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.grid_layout.addWidget(self.empty_label)

        self.scroll_area.setWidget(self.grid_container)
        layout.addWidget(self.scroll_area)

        # --- History Area ---
        history_lbl = QLabel("Download History")
        history_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #DDDDDD; margin-top: 15px;")
        layout.addWidget(history_lbl)

        self.history_scroll = QScrollArea()
        self.history_scroll.setWidgetResizable(True)
        self.history_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.history_scroll.setStyleSheet("background-color: transparent; border: 1px solid #30363D; border-radius: 8px;")
        self.history_scroll.setMaximumHeight(150)

        self.history_container = QWidget()
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Mock History Item
        mock_item = QLabel("✓ Cyberpunk 2077 - Download completed and added to library (Yesterday)")
        mock_item.setStyleSheet("color: #888888;")
        self.history_layout.addWidget(mock_item)

        self.history_scroll.setWidget(self.history_container)
        layout.addWidget(self.history_scroll)

    def _clear_grid(self) -> None:
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item.widget() and item.widget() != self.empty_label:
                item.widget().deleteLater()

    def load_queue(self) -> None:
        """Reads the queued downloads from SettingsManager."""
        self._clear_grid()
        queued = SettingsManager.get("download_queue", [])

        if not queued:
            self.empty_label.show()
            self.btn_download_all.hide()
            return

        self.empty_label.hide()
        self.btn_download_all.show()

        for game in queued:
            app_id = game.get("app_id", 0)
            title = game.get("title", f"App {app_id}")
            image_url = game.get("image_url", "")

            # Use 'queued' mode to show remove button or status
            card = GameCard(app_id, title, image_url, mode="queued")
            self.grid_layout.addWidget(card)

    def _process_queue(self) -> None:
        """Moves all queued games to SLSsteam config, fetches keys, and triggers Steam install."""
        queued = SettingsManager.get("download_queue", [])
        if not queued:
            return

        self.btn_download_all.setText("Processing...")
        self.btn_download_all.setEnabled(False)
        import asyncio
        loop = asyncio.get_event_loop()
        loop.create_task(self._async_process_queue(queued))

    async def _async_process_queue(self, queued: list) -> None:
        try:
            from src.services.download import DownloadManager
            download_method = SettingsManager.get("download_method", "steam")

            for game in queued:
                app_id = game.get("app_id")
                try:
                    # Extracts manifests to depotcache, injects VDF keys, updates config.yaml
                    depots = await DownloadManager.prepare_game_data(app_id)

                    if download_method == "ddmod":
                        self.btn_download_all.setText(f"Downloading {app_id} via DDMod...")
                        for depot in depots:
                            depot_id = depot.get("depot_id")
                            man_id = depot.get("manifest_id")
                            if depot_id and man_id:
                                try:
                                    async for progress in DownloadManager.install_via_ddmod(app_id, depot_id, man_id):
                                        print(f"[{app_id}] DDMod: {progress}")
                                except Exception as e:
                                    print(f"DDMod Error for depot {depot_id}: {e}")
                    else:
                        # Fallback to Steam protocol
                        DownloadManager.install_via_steam(app_id)

                except Exception as e:
                    print(f"Warning: Failed to prepare game data for {app_id}: {e}")

            # Clear queue
            SettingsManager.set("download_queue", [])
            self.load_queue()
            self.btn_download_all.setText("Download All")
            self.btn_download_all.setEnabled(True)
        except Exception as e:
            self.btn_download_all.setText("Error")
            self.btn_download_all.setEnabled(True)
            print(f"Error processing download queue: {e}")