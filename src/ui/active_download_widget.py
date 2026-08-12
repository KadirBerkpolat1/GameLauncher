import re
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                               QProgressBar, QFrame, QPushButton)
from PySide6.QtCore import Qt, Signal


class ActiveDownloadWidget(QFrame):
    """
    Redesigned Active Download Card featuring cyber-dark container,
    animated speed badge, clean progress bar, and responsive controls.
    """
    closed = Signal()

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.app_id = task.app_id
        self.title = task.title
        self.setObjectName("ActiveDownloadCard")
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(20)

        # Left: Game Title & App ID Badge
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)

        self.lbl_title = QLabel(self.title)
        self.lbl_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #FFFFFF;")
        
        self.lbl_appid = QLabel(f"AppID: {self.app_id}")
        self.lbl_appid.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 600;")

        title_layout.addWidget(self.lbl_title)
        title_layout.addWidget(self.lbl_appid)
        title_layout.addStretch()

        main_layout.addLayout(title_layout, stretch=3)

        # Middle: Progress bar, percentage and status text
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(6)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(12)

        status_row = QHBoxLayout()
        self.lbl_status = QLabel("Initializing download...")
        self.lbl_status.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 500;")

        self.lbl_percent = QLabel("0%")
        self.lbl_percent.setStyleSheet("color: #818CF8; font-size: 12px; font-weight: 700;")

        status_row.addWidget(self.lbl_status)
        status_row.addStretch()
        status_row.addWidget(self.lbl_percent)

        progress_layout.addStretch()
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addLayout(status_row)
        progress_layout.addStretch()

        main_layout.addLayout(progress_layout, stretch=5)

        # Right: Speed & Action Buttons
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(8)

        self.lbl_speed = QLabel("⚡  0.0 MB/s")
        self.lbl_speed.setStyleSheet("color: #A5B4FC; font-size: 13px; font-weight: 800;")
        self.lbl_speed.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        btns_layout = QHBoxLayout()
        btns_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        btns_layout.setSpacing(8)

        self.btn_pause = QPushButton("Pause")
        self.btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pause.setProperty("cssClass", "SecondaryAction")
        self.btn_pause.clicked.connect(self._toggle_pause)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setProperty("cssClass", "DangerAction")
        self.btn_cancel.clicked.connect(self._cancel_download)

        self.btn_complete = QPushButton("Dismiss")
        self.btn_complete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_complete.setProperty("cssClass", "SuccessAction")
        self.btn_complete.hide()
        self.btn_complete.clicked.connect(self.closed)

        btns_layout.addWidget(self.btn_pause)
        btns_layout.addWidget(self.btn_cancel)
        btns_layout.addWidget(self.btn_complete)

        controls_layout.addWidget(self.lbl_speed)
        controls_layout.addLayout(btns_layout)

        main_layout.addLayout(controls_layout, stretch=3)

    def _toggle_pause(self):
        if self.task.is_paused:
            self.task.resume()
            self.btn_pause.setText("Pause")
            self.lbl_status.setText("Resuming download...")
            self.lbl_status.setStyleSheet("color: #94A3B8; font-size: 12px;")
        else:
            self.task.pause()
            self.btn_pause.setText("Resume")
            self.lbl_status.setText("Download Paused")
            self.lbl_status.setStyleSheet("color: #FBBF24; font-size: 12px; font-weight: 700;")
            self.lbl_speed.setText("⏸  Paused")

    def _show_close_button(self, text: str = "Dismiss"):
        self.btn_pause.hide()
        self.btn_cancel.hide()
        self.btn_complete.setText(text)
        self.btn_complete.show()

    def _cancel_download(self):
        self.task.cancel()
        self._show_close_button("Canceled")
        self.lbl_status.setText("Download Canceled")
        self.lbl_status.setStyleSheet("color: #F87171; font-size: 12px; font-weight: 700;")
        self.lbl_speed.setText("")

    def mark_complete(self):
        self.progress_bar.setValue(100)
        self.lbl_percent.setText("100%")
        self.lbl_status.setText("✓  Completed & Goldberg Applied")
        self.lbl_status.setStyleSheet("color: #34D399; font-size: 12px; font-weight: 700;")
        self.lbl_speed.setText("🎉 Done")
        self._show_close_button("Finish")

    def mark_error(self, err_msg: str):
        self.lbl_status.setText(f"❌ Error: {err_msg}")
        self.lbl_status.setStyleSheet("color: #F87171; font-size: 12px; font-weight: 700;")
        self.lbl_speed.setText("")
        self._show_close_button("Dismiss")

    def update_progress(self, line: str):
        # 1. Depot percentage parsing: " 45.20% "
        match_pct = re.search(r"(\d+(?:\.\d+)?)%", line)
        if match_pct:
            try:
                pct = float(match_pct.group(1))
                self.progress_bar.setValue(int(pct))
                self.lbl_percent.setText(f"{pct:.1f}%")
            except ValueError:
                pass

        # 2. Download speed parsing: "24.50 MB/s" or "1.20 GB/s"
        match_speed = re.search(r"(\d+(?:\.\d+)?\s*(?:KB|MB|GB)/s)", line, re.IGNORECASE)
        if match_speed:
            self.lbl_speed.setText(f"⚡  {match_speed.group(1)}")

        # 3. Status text extraction
        if "Pre-allocating" in line:
            self.lbl_status.setText("Pre-allocating disk space...")
        elif "Downloading depot" in line:
            self.lbl_status.setText("Downloading depot chunks...")
        elif "Validating" in line:
            self.lbl_status.setText("Validating downloaded files...")
