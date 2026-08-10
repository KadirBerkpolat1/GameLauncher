import os
import asyncio
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                               QPushButton, QLabel, QHBoxLayout, QCheckBox, 
                               QListWidget, QStackedWidget, QWidget, QComboBox, 
                               QGroupBox, QRadioButton, QMessageBox)
from PySide6.QtCore import Qt
from src.config.settings import SettingsManager
from src.utils.paths import get_steam_path
from src.api.hubcap import hubcap_api

class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(750)
        self.setMinimumHeight(550)
        self.init_ui()

    def init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Sidebar ---
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setStyleSheet("""
            QListWidget {
                background-color: #161B22;
                border: none;
                border-right: 1px solid #21262D;
                color: #8B949E;
                font-size: 14px;
                padding-top: 10px;
            }
            QListWidget::item {
                padding: 12px 20px;
                border-radius: 0px;
            }
            QListWidget::item:selected {
                background-color: #1F6FEB;
                color: #FFFFFF;
                font-weight: 600;
            }
            QListWidget::item:hover:!selected {
                background-color: #21262D;
                color: #C9D1D9;
            }
        """)
        self.sidebar.addItems(["General", "Steam & Downloads", "Advanced Tools", "Fix Game", "Developer", "About App"])
        self.sidebar.currentRowChanged.connect(self._change_page)
        
        # --- Stacked Widget ---
        self.stack = QStackedWidget()
        self.stack.setObjectName("MainContent")
        
        # Pages
        self.page_general = QWidget()
        self.page_steam_downloads = QWidget()
        self.page_advanced = QWidget()
        self.page_fix_game = QWidget()
        self.page_developer = QWidget()
        self.page_about = QWidget()
        
        self._setup_general_page()
        self._setup_steam_downloads_page()
        
        # Placeholders
        self.page_advanced.setLayout(QVBoxLayout())
        self.page_fix_game.setLayout(QVBoxLayout())
        self.page_developer.setLayout(QVBoxLayout())
        self.page_about.setLayout(QVBoxLayout())
        
        self.stack.addWidget(self.page_general)
        self.stack.addWidget(self.page_steam_downloads)
        self.stack.addWidget(self.page_advanced)
        self.stack.addWidget(self.page_fix_game)
        self.stack.addWidget(self.page_developer)
        self.stack.addWidget(self.page_about)
        
        main_layout.addWidget(self.sidebar)
        
        # Right side layout (Stack + Buttons)
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.addWidget(self.stack)
        
        # --- Action Buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("cssClass", "SecondaryAction")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save")
        save_btn.setProperty("cssClass", "PrimaryAction")
        save_btn.clicked.connect(self._save_settings)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        
        right_layout.addLayout(btn_layout)
        main_layout.addLayout(right_layout)
        
        self.sidebar.setCurrentRow(0)
        
    def _change_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        
    def _setup_general_page(self) -> None:
        layout = QVBoxLayout(self.page_general)
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(20)
        
        title = QLabel("General Settings")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(title)
        
        # Theme & Appearance
        theme_group = QGroupBox("Theme & Appearance")
        theme_layout = QVBoxLayout()
        theme_combo = QComboBox()
        theme_combo.addItems(["Default (Dark)", "Custom"])
        theme_layout.addWidget(QLabel("Application Theme:"))
        theme_layout.addWidget(theme_combo)
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Hubcap API Key
        api_group = QGroupBox("Hubcap API Key")
        api_layout = QVBoxLayout()
        
        desc = QLabel("To download games and DLCs, you need a Hubcap API Key. Keys must start with 'smm_'.")
        desc.setWordWrap(True)
        api_layout.addWidget(desc)
        
        api_input_layout = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setText(SettingsManager.get("hubcap_api_key", ""))
        self.api_key_input.setPlaceholderText("smm_...")
        
        validate_btn = QPushButton("Validate")
        validate_btn.setProperty("cssClass", "SecondaryAction")
        validate_btn.clicked.connect(self._validate_api_key)
        
        api_input_layout.addWidget(self.api_key_input)
        api_input_layout.addWidget(validate_btn)
        api_layout.addLayout(api_input_layout)
        
        self.auto_upload_cb = QCheckBox("Automatically upload new config keys to Hubcap")
        self.auto_upload_cb.setChecked(SettingsManager.get("auto_upload_keys", True))
        api_layout.addWidget(self.auto_upload_cb)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # Tool Mode
        mode_group = QGroupBox("Tool Mode")
        mode_layout = QVBoxLayout()
        self.radio_std = QRadioButton("Standard download mode - lua goes to stplug-in")
        self.radio_std.setChecked(not SettingsManager.get("steamtools_mode", False))
        self.radio_st = QRadioButton("SteamTools mode - downloads only .lua files")
        self.radio_st.setChecked(SettingsManager.get("steamtools_mode", False))
        self.radio_dd = QRadioButton("DepotDownloader mode")
        
        mode_layout.addWidget(self.radio_std)
        mode_layout.addWidget(self.radio_st)
        mode_layout.addWidget(self.radio_dd)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
    def _setup_steam_downloads_page(self) -> None:
        sd_layout = QFormLayout(self.page_steam_downloads)
        sd_layout.setSpacing(15)
        
        steam_path = SettingsManager.get("steam_path", "")
        if not steam_path:
            detected = get_steam_path()
            if detected:
                steam_path = str(detected)
                SettingsManager.set("steam_path", steam_path)

        self.steam_path_input = QLineEdit()
        self.steam_path_input.setText(steam_path)
        sd_layout.addRow(QLabel("Steam Installation Path:"), self.steam_path_input)
        
        self.downloads_folder_input = QLineEdit()
        self.downloads_folder_input.setText(SettingsManager.get("downloads_folder", ""))
        self.downloads_folder_input.setPlaceholderText("Default: ~/Downloads")
        sd_layout.addRow(QLabel("Downloads Folder:"), self.downloads_folder_input)
        
        self.cb_auto_install = QCheckBox("Auto-install after download completes")
        self.cb_auto_install.setChecked(SettingsManager.get("auto_install", True))
        
        self.cb_delete_zip = QCheckBox("Delete ZIP file after installation")
        self.cb_delete_zip.setChecked(SettingsManager.get("delete_zip", False))
        
        self.cb_os_filter = QCheckBox("Disable depot OS filtering")
        self.cb_os_filter.setChecked(SettingsManager.get("disable_os_filter", False))
        
        sd_layout.addRow(self.cb_auto_install)
        sd_layout.addRow(self.cb_delete_zip)
        sd_layout.addRow(self.cb_os_filter)
        
    def _validate_api_key(self) -> None:
        key = self.api_key_input.text().strip()
        if not key.startswith("smm_"):
            QMessageBox.warning(self, "Validation Failed", "API Key must start with 'smm_'")
            return

        old_key = SettingsManager.get("hubcap_api_key", "")
        SettingsManager.set("hubcap_api_key", key)
        hubcap_api._client = None  # force rebuild with new key

        async def run_validation():
            try:
                data = await hubcap_api.get_user_stats()
                QMessageBox.information(
                    self, "Success",
                    f"API Key is valid!\nPlan: {data.get('plan', 'N/A')}\nDaily limit: {data.get('daily_limit', 'N/A')}"
                )
            except Exception as e:
                SettingsManager.set("hubcap_api_key", old_key)
                hubcap_api._client = None
                QMessageBox.critical(self, "Validation Failed", f"Could not validate API Key:\n{e}")

        asyncio.get_event_loop().create_task(run_validation())

    def _save_settings(self) -> None:
        SettingsManager.set("hubcap_api_key", self.api_key_input.text().strip())
        SettingsManager.set("auto_upload_keys", self.auto_upload_cb.isChecked())
        SettingsManager.set("steamtools_mode", self.radio_st.isChecked())
        SettingsManager.set("steam_path", self.steam_path_input.text())
        SettingsManager.set("downloads_folder", self.downloads_folder_input.text())
        SettingsManager.set("auto_install", self.cb_auto_install.isChecked())
        SettingsManager.set("delete_zip", self.cb_delete_zip.isChecked())
        SettingsManager.set("disable_os_filter", self.cb_os_filter.isChecked())
        
        # DepotDownloader mode check
        if self.radio_dd.isChecked():
            SettingsManager.set("download_method", "ddmod")
        else:
            SettingsManager.set("download_method", "steam")
            
        self.accept()
