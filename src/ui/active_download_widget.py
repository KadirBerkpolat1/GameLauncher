import re
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QProgressBar, QFrame
from PySide6.QtCore import Qt

class ActiveDownloadWidget(QFrame):
    """
    Displays the progress, speed, and status of an active download.
    Parses DepotDownloader stdout to update the UI.
    """
    def __init__(self, app_id: int, title: str = "Unknown Game", parent=None):
        super().__init__(parent)
        self.app_id = app_id
        self.title = title
        self.init_ui()

    def init_ui(self):
        self.setObjectName("ActiveDownloadFrame")
        self.setStyleSheet("""
            #ActiveDownloadFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 8px;
            }
        """)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        # Left: Title and App ID
        title_layout = QVBoxLayout()
        title_layout.setSpacing(5)
        
        lbl_title = QLabel(self.title)
        lbl_title.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold;")
        lbl_appid = QLabel(f"App ID: {self.app_id}")
        lbl_appid.setStyleSheet("color: #8B949E; font-size: 12px;")
        
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
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 6px;
                background-color: #21262D;
            }
            QProgressBar::chunk {
                background-color: #238636;
                border-radius: 6px;
            }
        """)
        
        self.lbl_status = QLabel("Starting download...")
        self.lbl_status.setStyleSheet("color: #8B949E; font-size: 12px;")
        
        progress_layout.addStretch()
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.lbl_status)
        progress_layout.addStretch()
        
        main_layout.addLayout(progress_layout, stretch=4)

        # Right: Speed
        self.lbl_speed = QLabel("-- MB/s")
        self.lbl_speed.setStyleSheet("color: #58A6FF; font-size: 14px; font-weight: bold;")
        self.lbl_speed.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        main_layout.addWidget(self.lbl_speed, stretch=1)

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

        # Try to parse speed (e.g. 1.2 MB/s, 500 KB/s)
        speed_match = re.search(r'(\d+(?:\.\d+)?\s*[KMG]B/s)', line, re.IGNORECASE)
        if speed_match:
            self.lbl_speed.setText(speed_match.group(1))

        # Optionally update status with raw line if it doesn't look like a pure progress bar frame
        # to show what is happening (e.g., "Logging into Steam...", "Downloading depot...")
        # DepotDownloader prints a lot of percentage lines. If there's no percentage, it might be a status line.
        if not pct_match and not speed_match and line.strip():
            # filter out very long lines or debug noise if necessary
            if len(line) < 100:
                self.lbl_status.setText(line.strip())

    def mark_complete(self):
        self.progress_bar.setValue(100)
        self.lbl_status.setText("Download Complete!")
        self.lbl_speed.setText("")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 6px;
                background-color: #21262D;
            }
            QProgressBar::chunk {
                background-color: #1F6FEB; /* Blue on completion */
                border-radius: 6px;
            }
        """)

    def mark_error(self, err_msg: str):
        self.lbl_status.setText(f"Error: {err_msg}")
        self.lbl_status.setStyleSheet("color: #F85149; font-size: 12px;") # Red error text
        self.lbl_speed.setText("")
