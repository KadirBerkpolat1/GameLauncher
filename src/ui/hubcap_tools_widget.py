import asyncio
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, 
                               QPushButton, QLabel, QHBoxLayout, QGroupBox, QScrollArea,
                               QFileDialog, QMessageBox)
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

        # API key info label
        api_info = QLabel("🔑 API key is configured in Settings → General.")
        api_info.setStyleSheet("color: #8B949E; font-size: 13px;")
        layout.addWidget(api_info)

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