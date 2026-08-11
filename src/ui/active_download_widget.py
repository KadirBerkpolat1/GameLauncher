import re
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QProgressBar, QFrame, QPushButton
from PySide6.QtCore import Qt, Signal

class ActiveDownloadWidget(QFrame):
    """
    Displays the progress, speed, and status of an active download.
    Parses DepotDownloader stdout to update the UI.
    """
    closed = Signal()

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.app_id = task.app_id
        self.title = task.title
        self.init_ui()

    def init_ui(self):
        self.setProperty("cssClass", "GameCard")
        
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        # Left: Title and App ID
        title_layout = QVBoxLayout()
        title_layout.setSpacing(5)
        
        lbl_title = QLabel(self.title)
        lbl_title.setProperty("cssClass", "GameTitle")
        lbl_appid = QLabel(f"App ID: {self.app_id}")
        lbl_appid.setProperty("cssClass", "GameSubtitle")
        
        title_layout.addWidget(lbl_title)
        title_layout.addWidget(lbl_appid)
        title_layout.addStretch()
        
        main_layout.addLayout(title_layout, stretch=2)

        # Middle: Progress bar and status
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(5)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(12)
        
        self.lbl_status = QLabel("Starting download...")
        self.lbl_status.setProperty("cssClass", "GameSubtitle")
        
        progress_layout.addStretch()
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.lbl_status)
        progress_layout.addStretch()
        
        main_layout.addLayout(progress_layout, stretch=4)

        # Right: Speed and Controls
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(5)
        
        self.lbl_speed = QLabel("-- MB/s")
        self.lbl_speed.setStyleSheet("color: #6366F1; font-size: 14px; font-weight: bold;")
        self.lbl_speed.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        btns_layout = QHBoxLayout()
        btns_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.btn_pause = QPushButton("Pause")
        self.btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pause.setProperty("cssClass", "SecondaryAction")
        self.btn_pause.clicked.connect(self._toggle_pause)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setProperty("cssClass", "DangerAction")
        self.btn_cancel.clicked.connect(self._cancel_download)

        self.btn_complete = QPushButton("Completed")
        self.btn_complete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_complete.setProperty("cssClass", "FixAction")
        self.btn_complete.hide()
        self.btn_complete.clicked.connect(self.closed)

        btns_layout.addWidget(self.btn_pause)
        btns_layout.addWidget(self.btn_cancel)
        btns_layout.addWidget(self.btn_complete)
        
        controls_layout.addWidget(self.lbl_speed)
        controls_layout.addLayout(btns_layout)
        
        main_layout.addLayout(controls_layout, stretch=1)

    def _toggle_pause(self):
        if self.task.is_paused:
            self.task.resume()
            self.lbl_status.setStyleSheet("") # Clear any inline styles to let cssClass work
            self.btn_pause.setText("Pause")
            self.lbl_status.setText("Resuming download...")
            self.lbl_status.setStyleSheet("color: #8B949E; font-size: 12px;")
        else:
            self.task.pause()
            self.btn_pause.setText("Resume")
            self.lbl_status.setStyleSheet("text-decoration: line-through;") # It's paused
            self.lbl_status.setStyleSheet("color: #D2A8FF; font-size: 12px; font-weight: bold;")
            self.lbl_speed.setText("-- MB/s")

    def _show_close_button(self, text: str = "Close"):
        """Replaces the Pause/Cancel controls with a single close button."""
        self.btn_pause.hide()
        self.btn_cancel.hide()
        self.btn_complete.setText(text)
        self.btn_complete.show()

    def _cancel_download(self):
        self.task.cancel()
        self._show_close_button()
        self.lbl_status.setText("Canceled")
        self.lbl_status.setStyleSheet("text-decoration: line-through;")
        self.lbl_speed.setText("")

    def update_progress(self, line: str):
        """
        Parses a stdout line from DepotDownloaderMod and updates the UI.
        Examples of lines:
        " 15.00%  150 MB / 1000 MB  ( 2.5 MB/s ) "
        """
        # Try to parse percentage
        pct_match = re.search(r'(\d+(?:\.\d+)?)%', line)
        if pct_match:
            try:
                progress = float(pct_match.group(1))
                self.progress_bar.setValue(int(progress))
            except ValueError:
                pass

        # Try to parse speed — DDMod prints IEC units (MiB/s, KiB/s, GiB/s)
        # and SI units (MB/s, KB/s, GB/s).
        speed_match = re.search(
            r'(\d+(?:\.\d+)?\s*[KMG]i?B/s)', line, re.IGNORECASE
        )
        if speed_match:
            self.lbl_speed.setText(speed_match.group(1).strip())

        bps_match = None
        if not speed_match:
            # Fallback: bare bytes/s (e.g. "at 850123 B/s")
            bps_match = re.search(
                r'(\d+(?:\.\d+)?)\s*B/s\b', line, re.IGNORECASE
            )
            if bps_match:
                self.lbl_speed.setText(bps_match.group(1) + " B/s")

        if not pct_match and not speed_match and not bps_match and line.strip():
            # filter out very long lines or debug noise if necessary
            if len(line) < 100:
                self.lbl_status.setText(line.strip())

    def mark_complete(self):
        self.progress_bar.setValue(100)
        self.lbl_status.setText("Download Complete")
        self.lbl_status.setStyleSheet("color: #3FB950; font-weight: bold; font-size: 14px;") # Green
        self.lbl_speed.setText("Done")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #21262D;
                border-radius: 6px;
            }
            QProgressBar::chunk {
                background-color: #3FB950;
                border-radius: 6px;
            }
        """)
        self._show_close_button("Completed")

    def mark_error(self, err_msg: str):
        self.lbl_status.setText(f"Hata: {err_msg}")
        self.lbl_status.setStyleSheet("color: #F85149; font-size: 12px; font-weight: bold;")
        self.lbl_speed.setText("Başarısız")
        self.lbl_speed.setStyleSheet("color: #F85149; font-size: 14px; font-weight: bold;")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #21262D;
                border-radius: 6px;
            }
            QProgressBar::chunk {
                background-color: #DA3633;
                border-radius: 6px;
            }
        """)
        self._show_close_button()
