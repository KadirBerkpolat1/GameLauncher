import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                               QPushButton, QLabel, QHBoxLayout, QCheckBox, 
                               QTabWidget, QWidget, QComboBox)
from PySide6.QtCore import Qt
from src.config.settings import SettingsManager
from src.utils.paths import get_steam_path

class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.init_ui()

    def init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        
        # --- Tabs ---
        self.tab_general = QWidget()
        self.tab_steam_downloads = QWidget()
        self.tab_advanced = QWidget()
        self.tab_fix_game = QWidget()
        self.tab_system = QWidget()
        
        self.tabs.addTab(self.tab_general, "General")
        self.tabs.addTab(self.tab_steam_downloads, "Steam & Downloads")
        self.tabs.addTab(self.tab_advanced, "Advanced Tools")
        self.tabs.addTab(self.tab_fix_game, "Fix Game")
        self.tabs.addTab(self.tab_system, "System")
        
        # --- Steam & Downloads Tab ---
        sd_layout = QFormLayout(self.tab_steam_downloads)
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
        
        self.download_method_combo = QComboBox()
        self.download_method_combo.addItems(["steam", "ddmod"])
        current_method = SettingsManager.get("download_method", "steam")
        self.download_method_combo.setCurrentText(current_method)
        sd_layout.addRow(QLabel("Download Engine:"), self.download_method_combo)
        
        self.cb_auto_install = QCheckBox("Auto-install after download completes")
        self.cb_auto_install.setChecked(SettingsManager.get("auto_install", True))
        
        self.cb_delete_zip = QCheckBox("Delete ZIP file after installation")
        self.cb_delete_zip.setChecked(SettingsManager.get("delete_zip", False))
        
        self.cb_steamtools = QCheckBox("SteamTools mode: download .lua only")
        self.cb_steamtools.setChecked(SettingsManager.get("steamtools_mode", False))
        
        self.cb_os_filter = QCheckBox("Disable depot OS filtering")
        self.cb_os_filter.setChecked(SettingsManager.get("disable_os_filter", False))
        
        sd_layout.addRow(self.cb_auto_install)
        sd_layout.addRow(self.cb_delete_zip)
        sd_layout.addRow(self.cb_steamtools)
        sd_layout.addRow(self.cb_os_filter)

        # Placeholders for other tabs
        gen_layout = QVBoxLayout(self.tab_general)
        gen_layout.addWidget(QLabel("General settings placeholder"))
        
        adv_layout = QVBoxLayout(self.tab_advanced)
        adv_layout.addWidget(QLabel("Advanced tools placeholder"))

        fix_layout = QVBoxLayout(self.tab_fix_game)
        fix_layout.addWidget(QLabel("Fix Game placeholder"))

        sys_layout = QVBoxLayout(self.tab_system)
        sys_layout.addWidget(QLabel("System placeholder"))

        main_layout.addWidget(self.tabs)

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

        main_layout.addLayout(btn_layout)

    def _save_settings(self) -> None:
        SettingsManager.set("steam_path", self.steam_path_input.text())
        SettingsManager.set("downloads_folder", self.downloads_folder_input.text())
        SettingsManager.set("download_method", self.download_method_combo.currentText())
        SettingsManager.set("auto_install", self.cb_auto_install.isChecked())
        SettingsManager.set("delete_zip", self.cb_delete_zip.isChecked())
        SettingsManager.set("steamtools_mode", self.cb_steamtools.isChecked())
        SettingsManager.set("disable_os_filter", self.cb_os_filter.isChecked())
        
        self.accept()
