import asyncio
from pathlib import Path
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel, QHBoxLayout, QCheckBox, QGroupBox, QComboBox
from src.config.settings import SettingsManager
from src.config.slssteam import SLSsteamConfigManager
from src.utils.paths import get_steam_path
from src.services.installer import SLSsteamInstaller, DDModInstaller

class SettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(600, 800)
        self.setStyleSheet("background-color: #1A1A1A; color: #FFFFFF;")
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # 1. General Settings Group
        group_general = QGroupBox("General Settings")
        group_general.setStyleSheet("QGroupBox { border: 1px solid #333; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        form_general = QFormLayout(group_general)
        form_general.setSpacing(15)

        steam_path = SettingsManager.get("steam_path", "")
        if not steam_path:
            detected = get_steam_path()
            if detected:
                steam_path = str(detected)
                SettingsManager.set("steam_path", steam_path)

        self.steam_path_input = QLineEdit()
        self.steam_path_input.setText(steam_path)
        form_general.addRow(QLabel("Steam Path:"), self.steam_path_input)

        # Download Engine Settings
        self.download_method_combo = QComboBox()
        self.download_method_combo.addItems(["steam", "ddmod"])
        current_method = SettingsManager.get("download_method", "steam")
        self.download_method_combo.setCurrentText(current_method)
        self.download_method_combo.setStyleSheet("background-color: #2A475E; color: white; padding: 5px; border-radius: 4px;")
        form_general.addRow(QLabel("Download Engine:"), self.download_method_combo)

        self.ddmod_path_input = QLineEdit()
        self.ddmod_path_input.setText(SettingsManager.get("depotdownloadermod_path", ""))
        self.ddmod_path_input.setPlaceholderText("/path/to/DepotDownloader.dll")
        form_general.addRow(QLabel("DDMod Path:"), self.ddmod_path_input)

        # DDMod Status Checker
        self.lbl_ddmod_status = QLabel("DDMod Status: Checking...")
        self.lbl_ddmod_status.setStyleSheet("font-weight: bold;")
        form_general.addRow(QLabel(""), self.lbl_ddmod_status)

        # DDMod Installer & Uninstaller
        ddmod_action_layout = QHBoxLayout()
        self.btn_install_ddmod = QPushButton("Install / Update DDMod")
        self.btn_install_ddmod.setProperty("cssClass", "PrimaryAction")
        self.btn_install_ddmod.clicked.connect(self._install_ddmod)

        self.btn_uninstall_ddmod = QPushButton("Uninstall")
        self.btn_uninstall_ddmod.setProperty("cssClass", "SecondaryAction")
        self.btn_uninstall_ddmod.setStyleSheet("background-color: #F44336; color: white;")
        self.btn_uninstall_ddmod.clicked.connect(self._uninstall_ddmod)

        ddmod_action_layout.addWidget(self.btn_install_ddmod)
        ddmod_action_layout.addWidget(self.btn_uninstall_ddmod)
        form_general.addRow(QLabel(""), ddmod_action_layout)

        layout.addWidget(group_general)

        # 2. SLSsteam Config Group
        group_sls = QGroupBox("SLSsteam Advanced Settings")
        group_sls.setStyleSheet("QGroupBox { border: 1px solid #333; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        form_sls = QVBoxLayout(group_sls)
        form_sls.setSpacing(10)

        try:
            self.sls_manager = SLSsteamConfigManager()
            self.cb_family = QCheckBox("Disable Family Share Lock (Recommended)")
            self.cb_family.setChecked(self.sls_manager.config_data.get("DisableFamilyShareLock", True))

            self.cb_cloud = QCheckBox("Disable Cloud Saves")
            self.cb_cloud.setChecked(self.sls_manager.config_data.get("DisableCloud", False))

            self.cb_updates = QCheckBox("Disable Game Updates")
            self.cb_updates.setChecked(self.sls_manager.config_data.get("DisableUpdates", False))

            form_sls.addWidget(self.cb_family)
            form_sls.addWidget(self.cb_cloud)
            form_sls.addWidget(self.cb_updates)
        except Exception as e:
            form_sls.addWidget(QLabel(f"Failed to load SLSsteam config: {e}"))

        # SLSsteam Status Checker
        self.lbl_status = QLabel("SLSsteam Status: Checking...")
        self.lbl_status.setStyleSheet("font-weight: bold;")
        form_sls.addWidget(self.lbl_status)
        self._check_status()

        # Installer & Uninstaller Buttons
        sls_action_layout = QHBoxLayout()
        self.btn_install_slssteam = QPushButton("Install / Update")
        self.btn_install_slssteam.setProperty("cssClass", "PrimaryAction")
        self.btn_install_slssteam.clicked.connect(self._install_slssteam)

        self.btn_uninstall_slssteam = QPushButton("Uninstall")
        self.btn_uninstall_slssteam.setProperty("cssClass", "SecondaryAction")
        self.btn_uninstall_slssteam.setStyleSheet("background-color: #F44336; color: white;")
        self.btn_uninstall_slssteam.clicked.connect(self._uninstall_slssteam)

        sls_action_layout.addWidget(self.btn_install_slssteam)
        sls_action_layout.addWidget(self.btn_uninstall_slssteam)
        form_sls.addLayout(sls_action_layout)

        layout.addWidget(group_sls)

        # 3. Ryuu API Group (Hubcap Alternative)
        group_ryuu = QGroupBox("Ryuu API Integration")
        group_ryuu.setStyleSheet("QGroupBox { border: 1px solid #333; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; color: #58A6FF; font-weight: bold; }")
        form_ryuu = QFormLayout(group_ryuu)
        form_ryuu.setSpacing(15)

        self.ryuu_api_key_input = QLineEdit()
        self.ryuu_api_key_input.setText(SettingsManager.get("ryuu_api_key", ""))
        self.ryuu_api_key_input.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.ryuu_api_key_input.setPlaceholderText("X-Auth-Key (Ryuu platformundan aldığınız anahtar)")
        form_ryuu.addRow(QLabel("Ryuu API Key:"), self.ryuu_api_key_input)

        layout.addWidget(group_ryuu)

        # 3. Action Buttons
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

        layout.addLayout(btn_layout)

    def _save_settings(self) -> None:
        # Save App Settings
        SettingsManager.set("ryuu_api_key", self.ryuu_api_key_input.text())
        SettingsManager.set("steam_path", self.steam_path_input.text())
        SettingsManager.set("download_method", self.download_method_combo.currentText())
        SettingsManager.set("depotdownloadermod_path", self.ddmod_path_input.text())

        # Save SLSsteam Settings
        if hasattr(self, 'sls_manager'):
            self.sls_manager.config_data["DisableFamilyShareLock"] = self.cb_family.isChecked()
            self.sls_manager.config_data["DisableCloud"] = self.cb_cloud.isChecked()
            self.sls_manager.config_data["DisableUpdates"] = self.cb_updates.isChecked()
            self.sls_manager.save()

        self.accept()

    def _check_status(self) -> None:
        """Checks if SLSsteam and DDMod are installed."""
        from pathlib import Path
        sls_lib_path = Path.home() / ".local/share/SLSsteam/SLSsteam.so"
        if sls_lib_path.exists():
            self.lbl_status.setText("SLSsteam Durumu: ✅ Kurulu ve Tespit Edildi")
            self.lbl_status.setStyleSheet("color: #4CAF50; font-weight: bold; padding-bottom: 5px;")
        else:
            self.lbl_status.setText("SLSsteam Durumu: ❌ Sistemde Bulunamadı")
            self.lbl_status.setStyleSheet("color: #F44336; font-weight: bold; padding-bottom: 5px;")

        ddmod_path = SettingsManager.get("depotdownloadermod_path", "")
        if ddmod_path and Path(ddmod_path).exists():
            self.lbl_ddmod_status.setText("DDMod Status: ✅ Installed")
            self.lbl_ddmod_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.lbl_ddmod_status.setText("DDMod Status: ❌ Not Found")
            self.lbl_ddmod_status.setStyleSheet("color: #F44336; font-weight: bold;")

    def _install_ddmod(self) -> None:
        self.btn_install_ddmod.setText("Downloading...")
        self.btn_install_ddmod.setEnabled(False)
        loop = asyncio.get_event_loop()
        loop.create_task(self._run_ddmod_installer())

    async def _run_ddmod_installer(self) -> None:
        try:
            tag = await DDModInstaller.update_ddmod()
            self.btn_install_ddmod.setText(f"Installed: {tag}")
            self.btn_install_ddmod.setStyleSheet("color: #4CAF50;")
            self.ddmod_path_input.setText(SettingsManager.get("depotdownloadermod_path", ""))
            self._check_status()
        except Exception as e:
            self.btn_install_ddmod.setText("Error")
            self.btn_install_ddmod.setStyleSheet("color: #F44336;")
            print(f"DDMod Installer error: {e}")

    def _uninstall_ddmod(self) -> None:
        self.btn_uninstall_ddmod.setText("Uninstalling...")
        self.btn_uninstall_ddmod.setEnabled(False)
        loop = asyncio.get_event_loop()
        loop.create_task(self._run_ddmod_uninstaller())

    async def _run_ddmod_uninstaller(self) -> None:
        try:
            await DDModInstaller.uninstall_ddmod()
            self.btn_uninstall_ddmod.setText("Uninstalled")
            self.ddmod_path_input.setText("")
            self._check_status()
        except Exception as e:
            self.btn_uninstall_ddmod.setText("Error")
            print(f"DDMod Uninstaller error: {e}")

    def _install_slssteam(self) -> None:
        self.btn_install_slssteam.setText("Kuruluyor (Lütfen bekleyin)...")
        self.btn_install_slssteam.setEnabled(False)
        loop = asyncio.get_event_loop()
        loop.create_task(self._run_installer())

    async def _run_installer(self) -> None:
        try:
            tag = await SLSsteamInstaller.update_slssteam()
            self.btn_install_slssteam.setText(f"Başarıyla Kuruldu: {tag}")
            self.btn_install_slssteam.setStyleSheet("color: #4CAF50;") # Green text
            self._check_status()
        except Exception as e:
            self.btn_install_slssteam.setText("Kurulum Hatalı")
            self.btn_install_slssteam.setStyleSheet("color: #F44336;") # Red text
            print(f"Installer error: {e}")

    def _uninstall_slssteam(self) -> None:
        self.btn_uninstall_slssteam.setText("Kaldırılıyor...")
        self.btn_uninstall_slssteam.setEnabled(False)
        loop = asyncio.get_event_loop()
        loop.create_task(self._run_uninstaller())

    async def _run_uninstaller(self) -> None:
        try:
            await SLSsteamInstaller.uninstall_slssteam()
            self.btn_uninstall_slssteam.setText("Başarıyla Kaldırıldı")
            self._check_status()
        except Exception as e:
            self.btn_uninstall_slssteam.setText("Hata Oluştu")
            print(f"Uninstaller error: {e}")
