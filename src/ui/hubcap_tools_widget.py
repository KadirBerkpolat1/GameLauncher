import asyncio
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
                               QPushButton, QLabel, QHBoxLayout, QGroupBox, QScrollArea)
from PySide6.QtCore import Qt
from src.config.settings import SettingsManager
from src.services.installer import SLSsteamInstaller, DDModInstaller

class HubcapToolsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self._check_status()

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

        # 1. API Key Group
        group_api = QGroupBox("API Key Configuration")
        group_api.setStyleSheet("QGroupBox { border: 1px solid #333; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; color: #58A6FF; font-weight: bold; }")
        form_api = QFormLayout(group_api)
        form_api.setSpacing(15)

        api_desc = QLabel('API Key is required to fetch game manifests. <a href="https://hubcapmanifest.com/api-keys" style="color: #66C0F4;">Nasıl API Key Alınır?</a>')
        api_desc.setOpenExternalLinks(True)
        form_api.addRow(api_desc)

        self.api_key_input = QLineEdit()
        self.api_key_input.setText(SettingsManager.get("hubcap_api_key", ""))
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.api_key_input.setPlaceholderText("Enter your API Key")
        
        self.btn_save_api = QPushButton("Save API Key")
        self.btn_save_api.setProperty("cssClass", "PrimaryAction")
        self.btn_save_api.clicked.connect(self._save_api_key)
        
        api_layout = QHBoxLayout()
        api_layout.addWidget(self.api_key_input)
        api_layout.addWidget(self.btn_save_api)
        form_api.addRow(QLabel("API Key:"), api_layout)

        layout.addWidget(group_api)

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
        layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _save_api_key(self):
        SettingsManager.set("hubcap_api_key", self.api_key_input.text())
        self.btn_save_api.setText("Saved!")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(2000, lambda: self.btn_save_api.setText("Save API Key"))

    def _check_status(self) -> None:
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
        loop = asyncio.get_event_loop()
        loop.create_task(self._run_sls_installer())

    async def _run_sls_installer(self) -> None:
        try:
            await SLSsteamInstaller.update_slssteam()
            self._check_status()
        except Exception as e:
            print(f"SLSsteam Installer error: {e}")
        finally:
            self.btn_install_sls.setText("Install / Update SLSsteam")
            self.btn_install_sls.setEnabled(True)

    def _uninstall_slssteam(self) -> None:
        self.btn_uninstall_sls.setText("Uninstalling...")
        self.btn_uninstall_sls.setEnabled(False)
        loop = asyncio.get_event_loop()
        loop.create_task(self._run_sls_uninstaller())

    async def _run_sls_uninstaller(self) -> None:
        try:
            await SLSsteamInstaller.uninstall_slssteam()
            self._check_status()
        except Exception as e:
            print(f"SLSsteam Uninstaller error: {e}")
        finally:
            self.btn_uninstall_sls.setText("Uninstall")
            self.btn_uninstall_sls.setEnabled(True)

    def _install_ddmod(self) -> None:
        self.btn_install_ddmod.setText("Installing...")
        self.btn_install_ddmod.setEnabled(False)
        loop = asyncio.get_event_loop()
        loop.create_task(self._run_ddmod_installer())

    async def _run_ddmod_installer(self) -> None:
        try:
            await DDModInstaller.update_ddmod()
            self._check_status()
        except Exception as e:
            print(f"DDMod Installer error: {e}")
        finally:
            self.btn_install_ddmod.setText("Install / Update DDMod")
            self.btn_install_ddmod.setEnabled(True)

    def _uninstall_ddmod(self) -> None:
        self.btn_uninstall_ddmod.setText("Uninstalling...")
        self.btn_uninstall_ddmod.setEnabled(False)
        loop = asyncio.get_event_loop()
        loop.create_task(self._run_ddmod_uninstaller())

    async def _run_ddmod_uninstaller(self) -> None:
        try:
            await DDModInstaller.uninstall_ddmod()
            self._check_status()
        except Exception as e:
            print(f"DDMod Uninstaller error: {e}")
        finally:
            self.btn_uninstall_ddmod.setText("Uninstall")
            self.btn_uninstall_ddmod.setEnabled(True)
