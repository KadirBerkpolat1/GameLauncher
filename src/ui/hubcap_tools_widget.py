import asyncio
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, 
                               QPushButton, QLabel, QHBoxLayout, QGroupBox, QScrollArea,
                               QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
from src.config.settings import SettingsManager

class HubcapToolsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # Header
        header = QLabel("SLSsteam / Installer")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFFFFF;")
        main_layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(20)

        # API key info label
        api_info = QLabel("🔑 API key is configured in Settings → General.")
        api_info.setStyleSheet("color: #8B949E; font-size: 13px;")
        layout.addWidget(api_info)

        # 4. Manual Game Installation
        group_manual = QGroupBox("Manual Game Installation")
        group_manual.setStyleSheet("QGroupBox { border: 1px solid #333; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        manual_layout = QVBoxLayout(group_manual)
        manual_layout.setSpacing(10)
        
        manual_info = QLabel("Install game manifests and keys manually using downloaded files.")
        manual_info.setStyleSheet("color: #8B949E; font-size: 13px;")
        manual_layout.addWidget(manual_info)
        
        manual_btn_layout = QHBoxLayout()
        self.btn_install_zip = QPushButton("Install from .ZIP")
        self.btn_install_zip.setProperty("cssClass", "PrimaryAction")
        self.btn_install_zip.clicked.connect(self._install_local_zip_dialog)
        
        self.btn_install_lua = QPushButton("Install from .LUA")
        self.btn_install_lua.setProperty("cssClass", "PrimaryAction")
        self.btn_install_lua.clicked.connect(self._install_local_lua_dialog)
        
        manual_btn_layout.addWidget(self.btn_install_zip)
        manual_btn_layout.addWidget(self.btn_install_lua)
        manual_layout.addLayout(manual_btn_layout)
        
        layout.addWidget(group_manual)
        layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)



    def _install_local_zip_dialog(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select ZIP file", "", "ZIP Files (*.zip)")
        if file_path:
            from src.services.download import DownloadManager
            try:
                DownloadManager.install_local_zip(file_path)
                QMessageBox.information(self, "Success", f"Successfully installed from {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to install: {e}")

    def _install_local_lua_dialog(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select LUA file", "", "LUA Files (*.lua)")
        if file_path:
            from src.services.download import DownloadManager
            try:
                DownloadManager.install_local_lua(file_path)
                QMessageBox.information(self, "Success", f"Successfully installed from {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to install: {e}")