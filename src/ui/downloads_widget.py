from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QGridLayout, QPushButton
from PySide6.QtCore import Qt
from src.ui.game_card import GameCard
from src.ui.active_download_widget import ActiveDownloadWidget
from src.ui.flow_layout import FlowLayout
from src.config.settings import SettingsManager
from src.utils.async_utils import get_async_loop

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
        header = QLabel("Active Downloads")
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
        # Removed combo_scope to use per-game DepotSelectionDialog

        self.btn_clear_history = QPushButton("Clear History")
        self.btn_clear_history.setProperty("cssClass", "SecondaryAction")
        self.btn_clear_history.clicked.connect(self._clear_history)
        action_layout.addStretch()
        action_layout.addWidget(self.btn_clear_history)
        layout.addWidget(action_bar)

        
        self.active_downloads_container = QWidget()
        self.active_downloads_layout = QVBoxLayout(self.active_downloads_container)
        self.active_downloads_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.active_scroll = QScrollArea()
        self.active_scroll.setWidgetResizable(True)
        self.active_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.active_scroll.setStyleSheet("background-color: transparent;")
        self.active_scroll.setMaximumHeight(200)
        self.active_scroll.setWidget(self.active_downloads_container)
        self.active_scroll.hide() # Hide initially
        layout.addWidget(self.active_scroll)

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

        self.history_scroll.setWidget(self.history_container)
        layout.addWidget(self.history_scroll)

        self._load_history()

    def _load_history(self) -> None:
        from src.config.settings import SettingsManager
        history = SettingsManager.get("download_history", []) or []
        for i in reversed(range(self.history_layout.count())):
            item = self.history_layout.itemAt(i)
            w = item.widget()
            if w:
                self.history_layout.removeWidget(w)
                w.deleteLater()
        if not history:
            empty = QLabel("No downloads yet.")
            empty.setStyleSheet("color: #888888;")
            self.history_layout.addWidget(empty)
            return
        for entry in reversed(history[-20:]):
            status = entry.get("status", "Completed")
            icon = "✓" if status == "Completed" else "✗"
            item = QLabel(f"{icon} {entry.get('title', '')} - {status} ({entry.get('date', '')})")
            item.setStyleSheet("color: #888888;")
            self.history_layout.addWidget(item)

    def _clear_history(self) -> None:
        from src.config.settings import SettingsManager
        SettingsManager.set("download_history", [])
        self._load_history()

    @staticmethod
    def _record_history(app_id: int, title: str, status: str, size: str = "") -> None:
        from src.config.settings import SettingsManager
        from datetime import datetime
        history = SettingsManager.get("download_history", []) or []
        history.append({
            "app_id": app_id,
            "title": title,
            "size": size,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": status,
        })
        SettingsManager.set("download_history", history)

    def start_download(self, app_id: int, title: str) -> None:
        """Starts a download process for a specific game."""
        loop = get_async_loop()
        loop.create_task(self._async_start_download(app_id, title))

    async def _async_start_download(self, app_id: int, title: str) -> None:
        try:
            from src.services.download import DownloadManager
            download_method = SettingsManager.get("download_method", "steam")
            
            try:
                # Extracts manifests for full game to parse Lua
                depots = await DownloadManager.prepare_game_data(app_id, scope="full")
                
                if download_method == "ddmod":
                    # --- Erken DDMod yolu kontrolü ---
                    from pathlib import Path
                    ddmod_path_str = SettingsManager.get("depotdownloadermod_path", "")
                    if not ddmod_path_str or not Path(ddmod_path_str).exists():
                        from PySide6.QtWidgets import QMessageBox
                        QMessageBox.critical(
                            self,
                            "DDMod Kurulu Değil",
                            "DepotDownloaderMod yolu bulunamadı.\n\n"
                            "Lütfen Settings → Advanced Tools bölümüne gidip DDMod'u kurun."
                        )
                        return

                    # Pause and ask for user selection using MetadataFetcher
                    from src.services.metadata import MetadataFetcher
                    from src.ui.depot_selection_dialog import DepotSelectionDialog
                    import asyncio

                    hubcap_depot_ids = [d.get("depot_id") for d in depots if d.get("depot_id")]
                    metadata = await MetadataFetcher.fetch_depot_metadata(app_id, hubcap_depot_ids)

                    future = asyncio.Future()
                    dialog = DepotSelectionDialog(title, metadata, self)

                    def on_accept():
                        if not future.done():
                            future.set_result(dialog.get_selected_depots())

                    def on_reject():
                        if not future.done():
                            future.set_result(None)

                    dialog.accepted.connect(on_accept)
                    dialog.rejected.connect(on_reject)
                    dialog.open()

                    selected_depot_ids = await future
                    dialog.deleteLater()

                    if selected_depot_ids is None:
                        print(f"User canceled installation for {app_id}")
                        return

                    # Depot'ların manifest_id kontrolü
                    selected_depots = [d for d in depots if d.get("depot_id") in selected_depot_ids]
                    valid_depots = [d for d in selected_depots if d.get("manifest_id")]
                    if not valid_depots:
                        from PySide6.QtWidgets import QMessageBox
                        QMessageBox.warning(
                            self, "İndirme Hatası",
                            f"{title} için geçerli depot/manifest verisi bulunamadı.\n"
                            "Hubcap bu oyun için indirme bilgisi sunmuyor olabilir."
                        )
                        return

                    from src.services.download_task import DownloadTask

                    task = DownloadTask(app_id, title, valid_depots)
                    dl_widget = ActiveDownloadWidget(task)

                    self.active_downloads_layout.addWidget(dl_widget)
                    self.active_scroll.show()

                    has_error = False

                    def progress_cb(line):
                        dl_widget.update_progress(line)

                    def error_cb(err_msg):
                        nonlocal has_error
                        has_error = True
                        dl_widget.mark_error(err_msg)
                        self._record_history(app_id, title, "Failed")
                        self._load_history()
                        print(f"DDMod Error for {app_id}: {err_msg}")

                    def complete_cb():
                        if not task.is_canceled and not has_error:
                            dl_widget.mark_complete()
                            self._record_history(app_id, title, "Completed")
                            self._load_history()

                    await task.run(progress_callback=progress_cb, error_callback=error_cb, complete_callback=complete_cb)

                    if task.is_canceled:
                        self._record_history(app_id, title, "Canceled")
                        self._load_history()
                        print(f"Task for {app_id} was canceled.")
                else:
                    # Fallback to Steam protocol
                    DownloadManager.install_via_steam(app_id)

            except Exception as e:
                print(f"Warning: Failed to prepare game data for {app_id}: {e}")

        except Exception as e:
            print(f"Error processing download: {e}")