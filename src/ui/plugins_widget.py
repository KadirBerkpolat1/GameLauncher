import asyncio
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QComboBox, QLineEdit, QFileDialog,
    QTextEdit, QSizePolicy
)
from PySide6.QtCore import Qt

from src.services.plugin_manager import PluginManager
from src.services.cloud_redirect import CloudRedirectManager
from src.utils.async_utils import get_async_loop


class PluginsWidget(QWidget):
    """
    UI View for managing Steam Tools & Cloud Saves:
    - Headcrab / SLSsteam (Client pinning & license bypass)
    - CloudRedirect (Custom cloud saves via LD_PRELOAD)
    - Goldberg Emulator status
    """

    def __init__(self) -> None:
        super().__init__()
        self.init_ui()
        self.refresh_status()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        header = QLabel("Steam Tools & Cloud Saves")
        header.setProperty("cssClass", "HeaderTitle")

        sub = QLabel("Manage Headcrab SLSsteam client pinning, CloudRedirect cloud saves, and DRM tools")
        sub.setProperty("cssClass", "SubHeader")

        title_box.addWidget(header)
        title_box.addWidget(sub)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.btn_refresh = QPushButton("🔄  Refresh Status")
        self.btn_refresh.setProperty("cssClass", "SecondaryAction")
        self.btn_refresh.clicked.connect(self.refresh_status)
        header_layout.addWidget(self.btn_refresh)

        layout.addLayout(header_layout)

        # Scroll Area for main content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(16)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        # =====================================================================
        # 1. HEADCRAB / SLSSTEAM CARD
        # =====================================================================
        self.headcrab_card = self._create_card(
            "🦀  Headcrab (SLSsteam Engine & Client Pinning)",
            "Automates Steam client pinning and SLSsteam injection to prevent Valve updates from breaking library integrations."
        )
        hc_layout = self.headcrab_card.layout()

        self.lbl_headcrab_status = QLabel("Checking SLSsteam status...")
        self.lbl_headcrab_status.setStyleSheet("color: #818CF8; font-weight: 700; font-size: 13px;")
        hc_layout.addWidget(self.lbl_headcrab_status)

        hc_btn_box = QHBoxLayout()
        self.btn_install_headcrab = QPushButton("🚀  Install / Update Headcrab Engine")
        self.btn_install_headcrab.setProperty("cssClass", "PrimaryAction")
        self.btn_install_headcrab.clicked.connect(self._on_install_headcrab)

        hc_btn_box.addWidget(self.btn_install_headcrab)
        hc_btn_box.addStretch()
        hc_layout.addLayout(hc_btn_box)

        scroll_layout.addWidget(self.headcrab_card)

        # =====================================================================
        # 2. CLOUDREDIRECT CARD
        # =====================================================================
        self.cloud_card = self._create_card(
            "☁  CloudRedirect (Custom Cloud Saves)",
            "Redirects Steam Cloud save operations to your own storage (Local Folder, Google Drive, OneDrive) via a lightweight LD_PRELOAD hook."
        )
        cloud_layout = self.cloud_card.layout()

        self.lbl_cr_status = QLabel("Checking hook status...")
        self.lbl_cr_status.setStyleSheet("color: #38BDF8; font-weight: 700; font-size: 13px;")
        cloud_layout.addWidget(self.lbl_cr_status)

        # Provider selection
        provider_layout = QHBoxLayout()
        provider_lbl = QLabel("Provider:")
        provider_lbl.setStyleSheet("color: #94A3B8; font-weight: 600;")
        self.combo_provider = QComboBox()
        self.combo_provider.addItems(["Local Directory", "Google Drive", "OneDrive", "Cloudflare R2", "S3-Compatible"])

        provider_layout.addWidget(provider_lbl)
        provider_layout.addWidget(self.combo_provider)
        provider_layout.addStretch()
        cloud_layout.addLayout(provider_layout)

        # Local save path
        path_layout = QHBoxLayout()
        path_lbl = QLabel("Save Path:")
        path_lbl.setStyleSheet("color: #94A3B8; font-weight: 600;")
        self.txt_save_path = QLineEdit()
        self.txt_save_path.setText(str(Path.home() / ".local" / "share" / "CloudRedirect" / "saves"))
        self.btn_browse_path = QPushButton("Browse...")
        self.btn_browse_path.setProperty("cssClass", "SecondaryAction")
        self.btn_browse_path.clicked.connect(self._on_browse_save_path)

        path_layout.addWidget(path_lbl)
        path_layout.addWidget(self.txt_save_path)
        path_layout.addWidget(self.btn_browse_path)
        cloud_layout.addLayout(path_layout)

        # Cloud actions
        cr_btn_box = QHBoxLayout()
        self.btn_install_cr = QPushButton("📥  Install CloudRedirect Hook")
        self.btn_install_cr.setProperty("cssClass", "PrimaryAction")
        self.btn_install_cr.clicked.connect(self._on_install_cloudredirect)

        self.btn_save_cr = QPushButton("💾  Save Cloud Settings")
        self.btn_save_cr.setProperty("cssClass", "SecondaryAction")
        self.btn_save_cr.clicked.connect(self._on_save_cloud_settings)

        cr_btn_box.addWidget(self.btn_install_cr)
        cr_btn_box.addWidget(self.btn_save_cr)
        cr_btn_box.addStretch()
        cloud_layout.addLayout(cr_btn_box)

        scroll_layout.addWidget(self.cloud_card)

        # =====================================================================
        # 3. CONSOLE & ACTIVITY LOG
        # =====================================================================
        log_card = self._create_card("📋  Activity & Status Log", "")
        log_layout = log_card.layout()

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(130)
        self.log_view.setStyleSheet("""
            background-color: #06080E;
            color: #A5B4FC;
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 11px;
            border: 1px solid #1E2337;
            border-radius: 8px;
            padding: 8px;
        """)
        log_layout.addWidget(self.log_view)
        scroll_layout.addWidget(log_card)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def _create_card(self, title: str, subtitle: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #0F121C;
                border: 1px solid #1E2337;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #F8FAFC; font-size: 15px; font-weight: 700;")
        layout.addWidget(t_lbl)

        if subtitle:
            s_lbl = QLabel(subtitle)
            s_lbl.setStyleSheet("color: #64748B; font-size: 12px;")
            s_lbl.setWordWrap(True)
            layout.addWidget(s_lbl)

        return card

    def log(self, text: str) -> None:
        self.log_view.append(text)

    def refresh_status(self) -> None:
        status = PluginManager.get_status()
        if status["slssteam"]:
            self.lbl_headcrab_status.setText("●  SLSsteam Engine: Installed & Active")
            self.lbl_headcrab_status.setStyleSheet("color: #10B981; font-weight: 700; font-size: 13px;")
        else:
            self.lbl_headcrab_status.setText("○  SLSsteam Engine: Not Installed")
            self.lbl_headcrab_status.setStyleSheet("color: #64748B; font-weight: 700; font-size: 13px;")

        if status["cloudredirect"]:
            self.lbl_cr_status.setText("●  CloudRedirect: Hook Installed")
            self.lbl_cr_status.setStyleSheet("color: #10B981; font-weight: 700; font-size: 13px;")
        else:
            self.lbl_cr_status.setText("○  CloudRedirect: Hook Not Installed")
            self.lbl_cr_status.setStyleSheet("color: #64748B; font-weight: 700; font-size: 13px;")

        cr_cfg = CloudRedirectManager.get_config()
        self.txt_save_path.setText(cr_cfg.get("local_path", ""))
        p = cr_cfg.get("provider", "local")
        p_indices = {"local": 0, "gdrive": 1, "onedrive": 2, "r2": 3, "s3": 4}
        self.combo_provider.setCurrentIndex(p_indices.get(p, 0))

    def _on_browse_save_path(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Cloud Saves Folder", self.txt_save_path.text())
        if path:
            self.txt_save_path.setText(path)

    def _on_install_headcrab(self) -> None:
        self.btn_install_headcrab.setEnabled(False)
        self.log("Starting Headcrab / SLSsteam setup...")

        async def _task():
            try:
                await PluginManager.install_headcrab(progress_callback=self.log)
                self.log("✓ Headcrab setup completed.")
            except Exception as e:
                self.log(f"✗ Headcrab error: {e}")
            finally:
                self.btn_install_headcrab.setEnabled(True)
                self.refresh_status()

        asyncio.run_coroutine_threadsafe(_task(), get_async_loop())

    def _on_install_cloudredirect(self) -> None:
        self.btn_install_cr.setEnabled(False)
        self.log("Installing CloudRedirect hook...")

        async def _task():
            try:
                await CloudRedirectManager.ensure_installed()
                self.log("✓ CloudRedirect hook ready.")
            except Exception as e:
                self.log(f"✗ CloudRedirect error: {e}")
            finally:
                self.btn_install_cr.setEnabled(True)
                self.refresh_status()

        asyncio.run_coroutine_threadsafe(_task(), get_async_loop())

    def _on_save_cloud_settings(self) -> None:
        p_map = {0: "local", 1: "gdrive", 2: "onedrive", 3: "r2", 4: "s3"}
        prov = p_map.get(self.combo_provider.currentIndex(), "local")
        cfg = {
            "enabled": True,
            "provider": prov,
            "local_path": self.txt_save_path.text().strip()
        }
        CloudRedirectManager.save_config(cfg)
        self.log(f"✓ Cloud settings saved: Provider={prov}, Path={cfg['local_path']}")
        self.refresh_status()
