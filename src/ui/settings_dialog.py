import os
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                               QPushButton, QLabel, QHBoxLayout, QCheckBox, 
                               QListWidget, QStackedWidget, QWidget, QComboBox, 
                               QGroupBox, QRadioButton, QMessageBox, QFileDialog)
from PySide6.QtCore import Qt
from src.config.settings import SettingsManager
from src.utils.paths import get_steam_path
from src.api.hubcap import hubcap_api
from src.services.installer import SLSsteamInstaller, DDModInstaller
from src.utils.async_utils import get_async_loop
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
        self._setup_advanced_page()
        
        # Placeholders
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
        save_btn.setDefault(True)

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
        validate_btn.setAutoDefault(False)
        
        api_input_layout.addWidget(self.api_key_input)
        api_input_layout.addWidget(validate_btn)
        api_layout.addLayout(api_input_layout)
        # SteamGridDB API Key
        sgdb_group = QGroupBox("SteamGridDB API Key")
        sgdb_layout = QVBoxLayout()
        sgdb_desc = QLabel("Optional: Enter your API key to fetch high-quality vertical covers from SteamGridDB instead of Steam.")
        sgdb_desc.setWordWrap(True)
        sgdb_layout.addWidget(sgdb_desc)
        
        self.sgdb_key_input = QLineEdit()
        self.sgdb_key_input.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.sgdb_key_input.setText(SettingsManager.get("steamgriddb_api_key", ""))
        self.sgdb_key_input.setPlaceholderText("SteamGridDB API Key...")
        sgdb_layout.addWidget(self.sgdb_key_input)
        sgdb_group.setLayout(sgdb_layout)
        layout.addWidget(sgdb_group)
        
        
        self.auto_upload_cb = QCheckBox("Automatically upload new config keys to Hubcap")
        self.auto_upload_cb.setChecked(SettingsManager.get("auto_upload_keys", True))
        api_layout.addWidget(self.auto_upload_cb)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # Tool Mode
        mode_group = QGroupBox("Tool Mode")
        mode_layout = QVBoxLayout()
        self.radio_std = QRadioButton("Standard download mode - lua goes to stplug-in")
        self.radio_st = QRadioButton("SteamTools mode - downloads only .lua files")
        self.radio_dd = QRadioButton("DepotDownloader mode")
        
        dl_method = SettingsManager.get("download_method", "steam")
        st_mode = SettingsManager.get("steamtools_mode", False)
        
        if dl_method == "ddmod":
            self.radio_dd.setChecked(True)
        elif st_mode:
            self.radio_st.setChecked(True)
        else:
            self.radio_std.setChecked(True)
        
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

        steam_path_layout = QHBoxLayout()
        self.steam_path_input = QLineEdit()
        self.steam_path_input.setText(steam_path)
        
        self.btn_auto_detect = QPushButton("Auto Detect")
        self.btn_auto_detect.clicked.connect(self._auto_detect_steam)
        
        self.btn_browse_steam = QPushButton("Browse")
        self.btn_browse_steam.clicked.connect(self._browse_steam_path)
        
        steam_path_layout.addWidget(self.steam_path_input)
        steam_path_layout.addWidget(self.btn_auto_detect)
        steam_path_layout.addWidget(self.btn_browse_steam)
        
        sd_layout.addRow(QLabel("Steam Installation Path:"), steam_path_layout)
        
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

        # Steam credentials for DDMod (ücretli oyunlar için)
        creds_group = QGroupBox("Steam Hesabı (DDMod için gerekli)")
        creds_group.setStyleSheet("QGroupBox { border: 1px solid #333; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        creds_layout = QFormLayout(creds_group)

        self.steam_username_input = QLineEdit()
        self.steam_username_input.setText(SettingsManager.get("steam_username", ""))
        self.steam_username_input.setPlaceholderText("Steam kullanıcı adınız")
        creds_layout.addRow(QLabel("Kullanıcı Adı:"), self.steam_username_input)

        self.steam_password_input = QLineEdit()
        self.steam_password_input.setText(SettingsManager.get("steam_password", ""))
        self.steam_password_input.setPlaceholderText("Steam şifreniz")
        self.steam_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        creds_layout.addRow(QLabel("Şifre:"), self.steam_password_input)

        note = QLabel("⚠ Şifre yerel olarak şifresiz saklanır. Sadece ücretli oyunlar için gereklidir.")
        note.setStyleSheet("color: #8B949E; font-size: 11px;")
        note.setWordWrap(True)
        creds_layout.addRow(note)

        sd_layout.addRow(creds_group)
    def _browse_steam_path(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(self, "Select Steam Directory")
        if dir_path:
            self.steam_path_input.setText(dir_path)

    def _auto_detect_steam(self) -> None:
        from src.utils.paths import get_steam_path
        path = get_steam_path()
        if path:
            self.steam_path_input.setText(str(path))
            QMessageBox.information(self, "Success", f"Steam path detected:\n{path}")
        else:
            QMessageBox.warning(self, "Not Found", "Could not automatically detect Steam installation (Native or Flatpak).")

    def _setup_advanced_page(self) -> None:
        layout = QVBoxLayout(self.page_advanced)
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(20)
        
        title = QLabel("Advanced Tools")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(title)

        # 2. SLSsteam / Headcrab Installer
        group_sls = QGroupBox("SLSsteam (Headcrab) Installer")
        group_sls.setStyleSheet("QGroupBox { border: 1px solid #333; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        sls_layout = QVBoxLayout(group_sls)
        sls_layout.setSpacing(10)

        self.lbl_sls_status = QLabel("Status: Checking...")
        self.lbl_sls_status.setStyleSheet("font-weight: bold;")
        sls_layout.addWidget(self.lbl_sls_status)

        sls_btn_layout = QHBoxLayout()
        self.btn_install_sls = QPushButton("Install / Update SLSsteam")
        self.btn_install_sls.setProperty("cssClass", "PrimaryAction")
        self.btn_install_sls.clicked.connect(self._install_slssteam)
        
        self.btn_uninstall_sls = QPushButton("Uninstall")
        self.btn_uninstall_sls.setStyleSheet("background-color: #F44336; color: white;")
        self.btn_uninstall_sls.clicked.connect(self._uninstall_slssteam)
        
        sls_btn_layout.addWidget(self.btn_install_sls)
        sls_btn_layout.addWidget(self.btn_uninstall_sls)
        sls_layout.addLayout(sls_btn_layout)

        layout.addWidget(group_sls)

        # 3. DDMod Installer
        group_ddmod = QGroupBox("DDMod (DepotDownloaderMod) Installer")
        group_ddmod.setStyleSheet("QGroupBox { border: 1px solid #333; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        ddmod_layout = QVBoxLayout(group_ddmod)
        ddmod_layout.setSpacing(10)

        self.lbl_ddmod_status = QLabel("Status: Checking...")
        self.lbl_ddmod_status.setStyleSheet("font-weight: bold;")
        ddmod_layout.addWidget(self.lbl_ddmod_status)

        ddmod_btn_layout = QHBoxLayout()
        self.btn_install_ddmod = QPushButton("Install / Update DDMod")
        self.btn_install_ddmod.setProperty("cssClass", "PrimaryAction")
        self.btn_install_ddmod.clicked.connect(self._install_ddmod)
        
        self.btn_uninstall_ddmod = QPushButton("Uninstall")
        self.btn_uninstall_ddmod.setStyleSheet("background-color: #F44336; color: white;")
        self.btn_uninstall_ddmod.clicked.connect(self._uninstall_ddmod)
        
        ddmod_btn_layout.addWidget(self.btn_install_ddmod)
        ddmod_btn_layout.addWidget(self.btn_uninstall_ddmod)
        ddmod_layout.addLayout(ddmod_btn_layout)

        layout.addWidget(group_ddmod)
        
        self._check_advanced_status()

    def _check_advanced_status(self) -> None:
        sls_dir = Path.home() / ".local" / "share" / "SLSsteam"
        has_sls = sls_dir.exists() and any(sls_dir.glob("*.so"))
        if has_sls:
            self.lbl_sls_status.setText("SLSsteam Status: Installed")
            self.lbl_sls_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.lbl_sls_status.setText("SLSsteam Status: Not Installed")
            self.lbl_sls_status.setStyleSheet("color: #F44336; font-weight: bold;")

        ddmod_path = SettingsManager.get("depotdownloadermod_path", "")
        if ddmod_path and Path(ddmod_path).exists():
            self.lbl_ddmod_status.setText("DDMod Status: Installed")
            self.lbl_ddmod_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.lbl_ddmod_status.setText("DDMod Status: Not Installed")
            self.lbl_ddmod_status.setStyleSheet("color: #F44336; font-weight: bold;")

    def _install_slssteam(self) -> None:
        self.btn_install_sls.setText("Installing...")
        self.btn_install_sls.setEnabled(False)
        loop = get_async_loop()
        loop.create_task(self._run_sls_installer())

    async def _run_sls_installer(self) -> None:
        try:
            await SLSsteamInstaller.update_slssteam()
            self._check_advanced_status()
        except Exception as e:
            print(f"SLSsteam Installer error: {e}")
        finally:
            self.btn_install_sls.setText("Install / Update SLSsteam")
            self.btn_install_sls.setEnabled(True)

    def _uninstall_slssteam(self) -> None:
        self.btn_uninstall_sls.setText("Uninstalling...")
        self.btn_uninstall_sls.setEnabled(False)
        loop = get_async_loop()
        loop.create_task(self._run_sls_uninstaller())

    async def _run_sls_uninstaller(self) -> None:
        try:
            await SLSsteamInstaller.uninstall_slssteam()
            self._check_advanced_status()
        except Exception as e:
            print(f"SLSsteam Uninstaller error: {e}")
        finally:
            self.btn_uninstall_sls.setText("Uninstall")
            self.btn_uninstall_sls.setEnabled(True)

    def _install_ddmod(self) -> None:
        self.btn_install_ddmod.setText("Installing...")
        self.btn_install_ddmod.setEnabled(False)
        loop = get_async_loop()
        loop.create_task(self._run_ddmod_installer())

    async def _run_ddmod_installer(self) -> None:
        try:
            await DDModInstaller.update_ddmod()
            self._check_advanced_status()
        except Exception as e:
            print(f"DDMod Installer error: {e}")
        finally:
            self.btn_install_ddmod.setText("Install / Update DDMod")
            self.btn_install_ddmod.setEnabled(True)

    def _uninstall_ddmod(self) -> None:
        self.btn_uninstall_ddmod.setText("Uninstalling...")
        self.btn_uninstall_ddmod.setEnabled(False)
        loop = get_async_loop()
        loop.create_task(self._run_ddmod_uninstaller())

    async def _run_ddmod_uninstaller(self) -> None:
        try:
            await DDModInstaller.uninstall_ddmod()
            self._check_advanced_status()
        except Exception as e:
            print(f"DDMod Uninstaller error: {e}")
        finally:
            self.btn_uninstall_ddmod.setText("Uninstall")
            self.btn_uninstall_ddmod.setEnabled(True)

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

        get_async_loop().create_task(run_validation())

    def _save_settings(self) -> None:
        SettingsManager.set("hubcap_api_key", self.api_key_input.text().strip())
        SettingsManager.set("steamgriddb_api_key", self.sgdb_key_input.text().strip())
        SettingsManager.set("auto_upload_keys", self.auto_upload_cb.isChecked())
        SettingsManager.set("steamtools_mode", self.radio_st.isChecked())
        SettingsManager.set("steam_path", self.steam_path_input.text())
        SettingsManager.set("downloads_folder", self.downloads_folder_input.text())
        SettingsManager.set("auto_install", self.cb_auto_install.isChecked())
        SettingsManager.set("delete_zip", self.cb_delete_zip.isChecked())
        SettingsManager.set("disable_os_filter", self.cb_os_filter.isChecked())
        SettingsManager.set("steam_username", self.steam_username_input.text().strip())
        SettingsManager.set("steam_password", self.steam_password_input.text())
        
        # DepotDownloader mode check
        if self.radio_dd.isChecked():
            SettingsManager.set("download_method", "ddmod")
        else:
            SettingsManager.set("download_method", "steam")
            
        self.accept()
