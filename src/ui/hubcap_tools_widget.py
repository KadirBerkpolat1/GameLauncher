from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                               QHBoxLayout, QFrame, QFileDialog, QMessageBox,
                               QScrollArea)
from PySide6.QtCore import Qt
from src.config.settings import SettingsManager


class HubcapToolsWidget(QWidget):
    """
    Redesigned Manual Game Installer featuring card-based package choices,
    direct file selection, and intuitive instructions.
    """
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 28, 28, 28)
        main_layout.setSpacing(20)

        # =====================================================================
        # HEADER
        # =====================================================================
        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        header = QLabel("Manual Game Installer")
        header.setProperty("cssClass", "HeaderTitle")

        sub = QLabel("Install pre-downloaded game manifest ZIPs or standalone SLSsteam Lua key files directly into your Steam directory.")
        sub.setProperty("cssClass", "SubHeader")

        title_box.addWidget(header)
        title_box.addWidget(sub)
        main_layout.addLayout(title_box)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.setSpacing(20)

        # =====================================================================
        # INSTALLATION ACTION CARDS
        # =====================================================================
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        # 1. ZIP Card
        card_zip = QFrame()
        card_zip.setObjectName("SurfaceCard")
        zip_layout = QVBoxLayout(card_zip)
        zip_layout.setContentsMargins(24, 24, 24, 24)
        zip_layout.setSpacing(14)

        zip_icon = QLabel("📦")
        zip_icon.setStyleSheet("font-size: 36px;")

        zip_title = QLabel("ZIP Manifest Package")
        zip_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #FFFFFF;")

        zip_desc = QLabel(
            "Install full game manifest bundles (.zip). Automatically extracts depot keys, "
            "manifest files, and registers the app in your SLSsteam configuration."
        )
        zip_desc.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 1.4;")
        zip_desc.setWordWrap(True)

        self.btn_install_zip = QPushButton("📂   Browse & Install .ZIP")
        self.btn_install_zip.setProperty("cssClass", "PrimaryAction")
        self.btn_install_zip.setMinimumHeight(44)
        self.btn_install_zip.clicked.connect(self._install_local_zip_dialog)

        zip_layout.addWidget(zip_icon)
        zip_layout.addWidget(zip_title)
        zip_layout.addWidget(zip_desc)
        zip_layout.addStretch()
        zip_layout.addWidget(self.btn_install_zip)

        # 2. LUA Card
        card_lua = QFrame()
        card_lua.setObjectName("SurfaceCard")
        lua_layout = QVBoxLayout(card_lua)
        lua_layout.setContentsMargins(24, 24, 24, 24)
        lua_layout.setSpacing(14)

        lua_icon = QLabel("📜")
        lua_icon.setStyleSheet("font-size: 36px;")

        lua_title = QLabel("Lua Plugin Script")
        lua_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #FFFFFF;")

        lua_desc = QLabel(
            "Install standalone SLSsteam .lua scripts. Directly copies the configuration "
            "into your Steam stplug-in directory and registers the AppID."
        )
        lua_desc.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 1.4;")
        lua_desc.setWordWrap(True)

        self.btn_install_lua = QPushButton("📂   Browse & Install .LUA")
        self.btn_install_lua.setProperty("cssClass", "PrimaryAction")
        self.btn_install_lua.setMinimumHeight(44)
        self.btn_install_lua.clicked.connect(self._install_local_lua_dialog)

        lua_layout.addWidget(lua_icon)
        lua_layout.addWidget(lua_title)
        lua_layout.addWidget(lua_desc)
        lua_layout.addStretch()
        lua_layout.addWidget(self.btn_install_lua)

        cards_layout.addWidget(card_zip)
        cards_layout.addWidget(card_lua)
        layout.addLayout(cards_layout)

        # =====================================================================
        # INFORMATION / TIPS CARD
        # =====================================================================
        info_card = QFrame()
        info_card.setObjectName("SurfaceCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 18, 20, 18)
        info_layout.setSpacing(10)

        info_header = QLabel("💡   How Manual Installation Works")
        info_header.setStyleSheet("font-size: 14px; font-weight: 800; color: #818CF8;")

        info_text = QLabel(
            "• <b>Automatic Detection:</b> Files are automatically parsed to extract AppIDs, manifests, and depot encryption keys.<br>"
            "• <b>Steam Sync:</b> After installation, click <b>Restart Steam</b> on the sidebar to make newly installed games appear in your Steam client.<br>"
            "• <b>API Keys:</b> To download directly from the Store without manual files, configure your Hubcap API key in <b>Settings</b>."
        )
        info_text.setTextFormat(Qt.TextFormat.RichText)
        info_text.setStyleSheet("color: #94A3B8; font-size: 12px; line-height: 1.5;")

        info_layout.addWidget(info_header)
        info_layout.addWidget(info_text)
        layout.addWidget(info_card)

        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _install_local_zip_dialog(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select ZIP file", "", "ZIP Files (*.zip)")
        if file_path:
            from src.services.download import DownloadManager
            try:
                DownloadManager.install_local_zip(file_path)
                QMessageBox.information(self, "Success", f"Successfully installed from {Path(file_path).name}\n\nPlease restart Steam to view your game.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to install: {e}")

    def _install_local_lua_dialog(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select LUA file", "", "LUA Files (*.lua)")
        if file_path:
            from src.services.download import DownloadManager
            try:
                DownloadManager.install_local_lua(file_path)
                QMessageBox.information(self, "Success", f"Successfully installed from {Path(file_path).name}\n\nPlease restart Steam to view your game.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to install: {e}")
