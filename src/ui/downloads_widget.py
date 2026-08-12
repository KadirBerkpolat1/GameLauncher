from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QScrollArea, QPushButton, QFrame, QSizePolicy)
from PySide6.QtCore import Qt
from src.ui.active_download_widget import ActiveDownloadWidget
from src.config.settings import SettingsManager
from src.utils.async_utils import get_async_loop


class DownloadsWidget(QWidget):
    """
    Redesigned Downloads View featuring active task management,
    real-time speedometer cards, and detailed download history log.
    """
    def __init__(self) -> None:
        super().__init__()
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # =====================================================================
        # HEADER & STATUS BANNER
        # =====================================================================
        header_layout = QHBoxLayout()

        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        header = QLabel("Downloads & Task Manager")
        header.setProperty("cssClass", "HeaderTitle")

        self.lbl_status = QLabel("⚡  Status: Idle (No active downloads)")
        self.lbl_status.setStyleSheet("color: #818CF8; font-size: 13px; font-weight: 700;")

        title_box.addWidget(header)
        title_box.addWidget(self.lbl_status)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        self.btn_clear_history = QPushButton("🗑  Clear History")
        self.btn_clear_history.setProperty("cssClass", "SecondaryAction")
        self.btn_clear_history.clicked.connect(self._clear_history)
        header_layout.addWidget(self.btn_clear_history)

        layout.addLayout(header_layout)

        # =====================================================================
        # ACTIVE DOWNLOADS CONTAINER
        # =====================================================================
        active_lbl = QLabel("ACTIVE TASKS")
        active_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        layout.addWidget(active_lbl)

        self.active_downloads_container = QWidget()
        self.active_downloads_layout = QVBoxLayout(self.active_downloads_container)
        self.active_downloads_layout.setContentsMargins(0, 0, 0, 0)
        self.active_downloads_layout.setSpacing(12)
        self.active_downloads_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.active_scroll = QScrollArea()
        self.active_scroll.setWidgetResizable(True)
        self.active_scroll.setObjectName("ActiveScroll")
        self.active_scroll.setMinimumHeight(120)
        self.active_scroll.setWidget(self.active_downloads_container)
        layout.addWidget(self.active_scroll)

        # Empty active placeholder
        self.empty_active_lbl = QLabel("No active downloads. Add games from the Store to begin.")
        self.empty_active_lbl.setStyleSheet("color: #475569; font-size: 13px; font-style: italic; padding: 20px;")
        self.empty_active_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.active_downloads_layout.addWidget(self.empty_active_lbl)

        # =====================================================================
        # DOWNLOAD HISTORY
        # =====================================================================
        history_lbl = QLabel("DOWNLOAD HISTORY")
        history_lbl.setStyleSheet("color: #64748B; font-size: 11px; font-weight: 800; letter-spacing: 1px; margin-top: 10px;")
        layout.addWidget(history_lbl)

        self.history_scroll = QScrollArea()
        self.history_scroll.setWidgetResizable(True)
        self.history_scroll.setObjectName("HistoryScroll")

        self.history_container = QWidget()
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(10, 10, 10, 10)
        self.history_layout.setSpacing(8)
        self.history_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.history_scroll.setWidget(self.history_container)
        layout.addWidget(self.history_scroll)

        self._load_history()

    def _load_history(self) -> None:
        history = SettingsManager.get("download_history", []) or []
        for i in reversed(range(self.history_layout.count())):
            item = self.history_layout.itemAt(i)
            w = item.widget()
            if w:
                self.history_layout.removeWidget(w)
                w.deleteLater()

        if not history:
            empty = QLabel("No previous downloads in history.")
            empty.setStyleSheet("color: #475569; font-style: italic; padding: 15px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_layout.addWidget(empty)
            return

        for record in reversed(history[-30:]): # Show last 30 entries
            item_frame = QFrame()
            item_frame.setStyleSheet("""
                QFrame {
                    background-color: #121522;
                    border: 1px solid #1E2337;
                    border-radius: 8px;
                    padding: 8px 14px;
                }
                QFrame:hover {
                    background-color: #151928;
                    border: 1px solid #283252;
                }
            """)
            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(4, 4, 4, 4)

            title_lbl = QLabel(f"<b>{record.get('title', 'Unknown')}</b>  <span style='color: #64748B;'>(AppID: {record.get('app_id')})</span>")
            title_lbl.setTextFormat(Qt.TextFormat.RichText)
            
            status = record.get("status", "Unknown")
            if status == "Completed":
                status_badge = QLabel("✓  Completed")
                status_badge.setProperty("cssClass", "BadgeSuccess")
            elif status == "Failed":
                status_badge = QLabel("✕  Failed")
                status_badge.setProperty("cssClass", "BadgeDanger")
            else:
                status_badge = QLabel(f"•  {status}")
                status_badge.setProperty("cssClass", "BadgeWarning")

            item_layout.addWidget(title_lbl)
            item_layout.addStretch()
            item_layout.addWidget(status_badge)

            self.history_layout.addWidget(item_frame)

    def _remove_active_widget(self, widget) -> None:
        self.active_downloads_layout.removeWidget(widget)
        widget.deleteLater()
        
        # Check active count
        active_count = sum(1 for i in range(self.active_downloads_layout.count()) 
                          if self.active_downloads_layout.itemAt(i).widget() != self.empty_active_lbl)
        if active_count == 0:
            self.empty_active_lbl.show()
            self.lbl_status.setText("⚡  Status: Idle (No active downloads)")
        else:
            self.lbl_status.setText(f"⚡  Status: {active_count} Active Download(s)")

    def _clear_history(self) -> None:
        SettingsManager.set("download_history", [])
        SettingsManager.save()
        self._load_history()

    @staticmethod
    def _record_history(app_id: int, title: str, status: str, size: str = "") -> None:
        history = SettingsManager.get("download_history", []) or []
        history.append({
            "app_id": app_id,
            "title": title,
            "status": status,
            "size": size
        })
        SettingsManager.set("download_history", history)
        SettingsManager.save()

    def start_download(self, app_id: int, title: str) -> None:
        loop = get_async_loop()
        loop.create_task(self._async_start_download(app_id, title))

    async def _async_start_download(self, app_id: int, title: str) -> None:
        try:
            from src.services.download import DownloadManager
            download_method = SettingsManager.get("download_method", "steam")

            try:
                game_data = await DownloadManager.prepare_game_data(app_id, scope="full")
                depots = game_data.get("depots", {})

                if download_method == "ddmod":
                    from pathlib import Path
                    ddmod_path_str = SettingsManager.get("depotdownloadermod_path", "")
                    if not ddmod_path_str or not Path(ddmod_path_str).exists():
                        from PySide6.QtWidgets import QMessageBox
                        QMessageBox.critical(
                            self,
                            "DDMod Not Installed",
                            "DepotDownloaderMod was not found.\n\n"
                            "Please go to Settings → Advanced Tools to install DDMod."
                        )
                        return

                    from src.services.metadata import MetadataFetcher
                    from src.ui.depot_selection_dialog import DepotSelectionDialog
                    import asyncio

                    hubcap_depot_ids = list(depots.keys())
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
                        print(f"User canceled download for {app_id}")
                        return

                    selected_depots = {
                        d_id: d for d_id, d in depots.items()
                        if d_id in selected_depot_ids
                    }
                    if not selected_depots:
                        from PySide6.QtWidgets import QMessageBox
                        QMessageBox.warning(
                            self, "Download Error",
                            f"No valid depot metadata found for {title}."
                        )
                        return

                    game_data["depots"] = selected_depots
                    game_data["manifests"] = {
                        d_id: d.get("manifest_id")
                        for d_id, d in selected_depots.items()
                        if d.get("manifest_id")
                    }

                    from src.services.download_task import DownloadTask

                    task = DownloadTask(game_data, title)
                    dl_widget = ActiveDownloadWidget(task)
                    dl_widget.closed.connect(lambda w=dl_widget: self._remove_active_widget(w))

                    self.empty_active_lbl.hide()
                    self.active_downloads_layout.addWidget(dl_widget)
                    self.lbl_status.setText(f"⚡  Status: Downloading {title}...")

                    has_error = False

                    def progress_cb(line):
                        dl_widget.update_progress(line)

                    def error_cb(err_msg):
                        nonlocal has_error
                        has_error = True
                        dl_widget.mark_error(err_msg)
                        self._record_history(app_id, title, "Failed")
                        self._load_history()

                    def complete_cb():
                        if not task.is_canceled and not has_error:
                            dl_widget.mark_complete()
                            self._record_history(app_id, title, "Completed")
                            self._load_history()

                            # Auto-Goldberg Execution
                            try:
                                from src.services.drm_manager import DRMManager
                                DRMManager.apply_goldberg(str(app_id), task.download_dir)
                                print(f"Auto-applied Goldberg for {title} out-of-the-box.")
                            except Exception as e:
                                print(f"Failed to auto-apply Goldberg: {e}")

                    await task.run(progress_callback=progress_cb, error_callback=error_cb, complete_callback=complete_cb)

                    if task.is_canceled:
                        self._record_history(app_id, title, "Canceled")
                        self._load_history()
                else:
                    # Steam protocol
                    DownloadManager.install_via_steam(app_id)

            except Exception as e:
                print(f"Warning: Failed to prepare game data for {app_id}: {e}")

        except Exception as e:
            print(f"Error processing download: {e}")
