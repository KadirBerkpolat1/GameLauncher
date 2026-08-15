import os
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                               QPushButton, QLabel, QHBoxLayout, QCheckBox, 
                               QListWidget, QStackedWidget, QWidget, QComboBox, 
                               QGroupBox, QRadioButton, QMessageBox, QFileDialog,
                               QFrame, QScrollArea, QProgressBar)
from PySide6.QtCore import Qt
from src.config.settings import SettingsManager
from src.utils.paths import get_steam_path
from src.api.hubcap import hubcap_api
from src.services.installer import SLSsteamInstaller, DDModInstaller
from src.utils.async_utils import get_async_loop


class SettingsDialog(QDialog):
    """
    Redesigned Settings Modal featuring 3 clean, fully-functional categories:
    1. API Keys & Integrations (Hubcap, SteamGridDB with step-by-step guides)
    2. Steam & Download Engine (Paths, Engine method, Auto-Goldberg)
    3. Advanced Tools (SLSsteam, DDMod, Logs)
    """
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(840)
        self.setMinimumHeight(620)
        self.init_ui()

    def init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # =====================================================================
        # SIDEBAR
        # =====================================================================
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(220)
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setStyleSheet("""
            QListWidget {
                background-color: #0E111B;
                border: none;
                border-right: 1px solid #1E243A;
                color: #94A3B8;
                font-size: 13px;
                font-weight: 600;
                padding-top: 15px;
            }
            QListWidget::item {
                padding: 14px 18px;
                border-radius: 8px;
                margin: 3px 10px;
            }
            QListWidget::item:selected {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(99, 102, 241, 0.25), stop:1 rgba(139, 92, 246, 0.10));
                color: #A5B4FC;
                border-left: 3px solid #6366F1;
                font-weight: 700;
            }
            QListWidget::item:hover:!selected {
                background-color: #151928;
                color: #F1F5F9;
            }
        """)
        self.sidebar.addItem("🔑   API Keys")
        self.sidebar.addItem("📁   Steam & Engine")
        self.sidebar.addItem("🛠️   Advanced Tools")
        self.sidebar.currentRowChanged.connect(self._change_page)

        # =====================================================================
        # STACKED PAGES
        # =====================================================================
        self.stack = QStackedWidget()
        self.stack.setObjectName("MainContent")

        self.page_api = QWidget()
        self.page_steam = QWidget()
        self.page_tools = QWidget()

        self._setup_api_page()
        self._setup_steam_page()
        self._setup_tools_page()

        self.stack.addWidget(self.page_api)
        self.stack.addWidget(self.page_steam)
        self.stack.addWidget(self.page_tools)

        main_layout.addWidget(self.sidebar)

        # Right side layout (Stack + Bottom Bar)
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(24, 24, 24, 20)
        right_layout.setSpacing(16)
        right_layout.addWidget(self.stack)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("cssClass", "SecondaryAction")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save Settings")
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

    # =========================================================================
    # 1. API KEYS PAGE & INSTRUCTION GUIDES
    # =========================================================================
    def _setup_api_page(self) -> None:
        scroll = QScrollArea(self.page_api)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.setSpacing(16)

        title = QLabel("API Keys & Integrations")
        title.setProperty("cssClass", "HeaderTitle")
        sub = QLabel("Configure your external API tokens for store catalog search and high-resolution posters.")
        sub.setProperty("cssClass", "SubHeader")
        layout.addWidget(title)
        layout.addWidget(sub)

        # Hubcap API Group
        group_hubcap = QGroupBox("Hubcap Manifest API (Required for Store && Auto-Download)")
        hubcap_layout = QVBoxLayout(group_hubcap)
        hubcap_layout.setSpacing(10)

        self.input_hubcap_key = QLineEdit()
        self.input_hubcap_key.setPlaceholderText("Paste your Hubcap Bearer API key here...")
        self.input_hubcap_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_hubcap_key.setText(SettingsManager.get("hubcap_api_key", ""))

        btn_row = QHBoxLayout()
        self.btn_show_key = QPushButton("Show Key")
        self.btn_show_key.setProperty("cssClass", "SecondaryAction")
        self.btn_show_key.clicked.connect(self._toggle_key_visibility)

        self.btn_test_key = QPushButton("Test Connection")
        self.btn_test_key.setProperty("cssClass", "SecondaryAction")
        self.btn_test_key.clicked.connect(self._test_hubcap_key)

        btn_row.addWidget(self.btn_show_key)
        btn_row.addWidget(self.btn_test_key)
        btn_row.addStretch()

        self.lbl_hubcap_status = QLabel("")
        self.lbl_hubcap_status.setStyleSheet("font-size: 12px; font-weight: 600;")

        hubcap_layout.addWidget(self.input_hubcap_key)
        hubcap_layout.addLayout(btn_row)
        hubcap_layout.addWidget(self.lbl_hubcap_status)
        layout.addWidget(group_hubcap)

        # Ryuu Manifest API Group
        group_ryuu = QGroupBox("Ryuu Manifest API (Direct .lua Generator)")
        ryuu_layout = QVBoxLayout(group_ryuu)
        ryuu_layout.setSpacing(10)

        self.input_ryuu_key = QLineEdit()
        self.input_ryuu_key.setPlaceholderText("Paste your Ryuu API key (generator.ryuu.lol)...")
        self.input_ryuu_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_ryuu_key.setText(SettingsManager.get("ryuu_api_key", ""))
        ryuu_layout.addWidget(self.input_ryuu_key)

        # Manifest Provider Selector
        provider_row = QHBoxLayout()
        p_lbl = QLabel("Preferred Manifest Provider:")
        p_lbl.setStyleSheet("color: #94A3B8; font-weight: 600;")
        self.combo_manifest_provider = QComboBox()
        self.combo_manifest_provider.addItems(["Auto (Hubcap + Ryuu Fallback)", "Hubcap Only", "Ryuu Only"])
        cur_p = SettingsManager.get("manifest_provider", "auto")
        if cur_p == "hubcap":
            self.combo_manifest_provider.setCurrentIndex(1)
        elif cur_p == "ryuu":
            self.combo_manifest_provider.setCurrentIndex(2)
        else:
            self.combo_manifest_provider.setCurrentIndex(0)

        provider_row.addWidget(p_lbl)
        provider_row.addWidget(self.combo_manifest_provider)
        provider_row.addStretch()
        ryuu_layout.addLayout(provider_row)
        layout.addWidget(group_ryuu)
        # Hubcap Account & Quota Status Card
        self.card_account = QFrame()
        self.card_account.setObjectName("SurfaceCard")
        self.card_account.setStyleSheet("""
            QFrame#SurfaceCard {
                background-color: #121522;
                border: 1px solid #232A44;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        acct_layout = QVBoxLayout(self.card_account)
        acct_layout.setSpacing(10)

        acct_header_row = QHBoxLayout()
        acct_title = QLabel("👤   Hubcap Account & Daily Quota Status")
        acct_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        
        self.btn_acct_refresh = QPushButton("🔄  Refresh Stats")
        self.btn_acct_refresh.setProperty("cssClass", "SecondaryAction")
        self.btn_acct_refresh.clicked.connect(self._fetch_account_stats)

        acct_header_row.addWidget(acct_title)
        acct_header_row.addStretch()
        acct_header_row.addWidget(self.btn_acct_refresh)

        # Metrics Row
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(20)

        self.lbl_user_name = QLabel("<b>Username:</b> —")
        self.lbl_user_name.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_user_name.setStyleSheet("color: #E2E8F0; font-size: 13px;")

        self.lbl_user_quota = QLabel("<b>Daily Quota:</b> —")
        self.lbl_user_quota.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_user_quota.setStyleSheet("color: #E2E8F0; font-size: 13px;")

        self.lbl_user_expires = QLabel("<b>Key Expires:</b> —")
        self.lbl_user_expires.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_user_expires.setStyleSheet("color: #E2E8F0; font-size: 13px;")

        metrics_row.addWidget(self.lbl_user_name)
        metrics_row.addWidget(self.lbl_user_quota)
        metrics_row.addWidget(self.lbl_user_expires)
        metrics_row.addStretch()

        # Quota Progress Bar
        self.quota_bar = QProgressBar()
        self.quota_bar.setRange(0, 100)
        self.quota_bar.setValue(0)
        self.quota_bar.setFixedHeight(8)
        self.quota_bar.setTextVisible(False)

        acct_layout.addLayout(acct_header_row)
        acct_layout.addLayout(metrics_row)
        acct_layout.addWidget(self.quota_bar)

        layout.addWidget(self.card_account)

        # Initial fetch if key exists
        if SettingsManager.get("hubcap_api_key", ""):
            self._fetch_account_stats()
        # SteamGridDB Group
        group_sgdb = QGroupBox("SteamGridDB (High-Res 600x900 Covers — Optional)")
        sgdb_layout = QVBoxLayout(group_sgdb)
        sgdb_layout.setSpacing(8)

        self.input_sgdb_key = QLineEdit()
        self.input_sgdb_key.setPlaceholderText("Paste your SteamGridDB API key here (Optional)...")
        self.input_sgdb_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_sgdb_key.setText(SettingsManager.get("steamgriddb_api_key", ""))

        sgdb_row = QHBoxLayout()
        sgdb_row.addWidget(self.input_sgdb_key)

        self.btn_test_sgdb = QPushButton("Test Key")
        self.btn_test_sgdb.setProperty("cssClass", "SecondaryAction")
        self.btn_test_sgdb.setFixedWidth(100)
        self.btn_test_sgdb.clicked.connect(self._on_test_sgdb_key)
        sgdb_row.addWidget(self.btn_test_sgdb)

        sgdb_desc = QLabel("Automatically downloads high-resolution vertical grid posters instead of generic Steam banners.")
        sgdb_desc.setStyleSheet("color: #64748B; font-size: 12px;")

        sgdb_layout.addLayout(sgdb_row)
        sgdb_layout.addWidget(sgdb_desc)
        layout.addWidget(group_sgdb)

        # =====================================================================
        # STEP-BY-STEP INSTRUCTIONS GUIDE CARD
        # =====================================================================
        guide_card = QFrame()
        guide_card.setObjectName("SurfaceCard")
        guide_card.setStyleSheet("""
            QFrame#SurfaceCard {
                background-color: #111420;
                border: 1px solid #1F253C;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        guide_layout = QVBoxLayout(guide_card)
        guide_layout.setSpacing(12)

        guide_header = QLabel("📖   How to Get Your API Keys (Step-by-Step Guide)")
        guide_header.setStyleSheet("font-size: 14px; font-weight: 800; color: #818CF8;")
        guide_layout.addWidget(guide_header)

        guide_text = QLabel(
            "<b>1. How to get Hubcap API Key (Required for downloading games):</b><br>"
            "&nbsp;&nbsp;• <b>Step 1:</b> Visit <b>https://hubcapmanifest.com/</b> in your web browser.<br>"
            "&nbsp;&nbsp;• <b>Step 2:</b> Click the <b>Login</b> button in the top-right corner to sign in with Discord or GitHub.<br>"
            "&nbsp;&nbsp;• <b>Step 3:</b> Click your profile avatar in the top-right and select <b>API Keys</b>.<br>"
            "&nbsp;&nbsp;• <b>Step 4:</b> Click <b>'Generate New Key'</b>, copy the generated token, and paste it into the <b>Hubcap Manifest API</b> field above.<br><br>"
            "<b>2. How to get SteamGridDB API Key (For high-resolution cover artwork — Optional):</b><br>"
            "&nbsp;&nbsp;• <b>Step 1:</b> Visit <b>https://www.steamgriddb.com/</b> in your web browser.<br>"
            "&nbsp;&nbsp;• <b>Step 2:</b> Log in using your Steam account.<br>"
            "&nbsp;&nbsp;• <b>Step 3:</b> Open your profile dropdown and navigate to <b>Preferences → API</b>.<br>"
            "&nbsp;&nbsp;• <b>Step 4:</b> Click <b>'Generate API Key'</b>, copy your personal key, and paste it into the <b>SteamGridDB</b> field above."
        )
        guide_text.setTextFormat(Qt.TextFormat.RichText)
        guide_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        guide_text.setStyleSheet("color: #94A3B8; font-size: 12px; line-height: 1.6;")
        guide_text.setWordWrap(True)
        guide_layout.addWidget(guide_text)

        layout.addWidget(guide_card)
        layout.addStretch()

        scroll.setWidget(container)
        
        main_page_layout = QVBoxLayout(self.page_api)
        main_page_layout.setContentsMargins(0, 0, 0, 0)
        main_page_layout.addWidget(scroll)

    def _toggle_key_visibility(self) -> None:
        if self.input_hubcap_key.echoMode() == QLineEdit.EchoMode.Password:
            self.input_hubcap_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_show_key.setText("Hide Key")
        else:
            self.input_hubcap_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_show_key.setText("Show Key")

    def _test_hubcap_key(self) -> None:
        key = self.input_hubcap_key.text().strip()
        if not key:
            self.lbl_hubcap_status.setText("❌  Please enter a key first.")
            self.lbl_hubcap_status.setStyleSheet("color: #F87171;")
            return

        self.lbl_hubcap_status.setText("⏳  Testing connection...")
        self.lbl_hubcap_status.setStyleSheet("color: #818CF8;")
        self.btn_test_key.setEnabled(False)

        loop = get_async_loop()
        loop.create_task(self._async_test_hubcap(key))

    async def _async_test_hubcap(self, key: str) -> None:
        try:
            valid = await hubcap_api.validate_key(key)
            if valid:
                self.lbl_hubcap_status.setText("✓  API Key is valid and active!")
                self.lbl_hubcap_status.setStyleSheet("color: #34D399;")
                await self._async_fetch_account_stats()
            else:
                self.lbl_hubcap_status.setText("❌  Invalid API key.")
                self.lbl_hubcap_status.setStyleSheet("color: #F87171;")
        except Exception as e:
            self.lbl_hubcap_status.setText(f"❌  Connection Error: {e}")
            self.lbl_hubcap_status.setStyleSheet("color: #F87171;")
        finally:
            self.btn_test_key.setEnabled(True)

    def _fetch_account_stats(self) -> None:
        loop = get_async_loop()
        loop.create_task(self._async_fetch_account_stats())

    async def _async_fetch_account_stats(self) -> None:
        try:
            stats = await hubcap_api.get_user_stats()
            username = stats.get("username", "Unknown")
            used = stats.get("daily_usage", 0)
            limit = stats.get("daily_limit", 25)
            expires = stats.get("api_key_expires_at", "")
            if expires:
                expires = expires.split("T")[0]
            else:
                expires = "Never"

            self.lbl_user_name.setText(f"<b>Username:</b> <span style='color: #818CF8;'>{username}</span>")
            self.lbl_user_quota.setText(f"<b>Daily Quota:</b> <span style='color: #34D399;'>{used} / {limit} Used</span>")
            self.lbl_user_expires.setText(f"<b>Key Expires:</b> <span style='color: #94A3B8;'>{expires}</span>")

            if limit > 0:
                pct = int((used / limit) * 100)
                self.quota_bar.setValue(pct)
        except Exception as e:
            self.lbl_user_name.setText(f"<b>Account:</b> Error ({e})")
    # =========================================================================
    def _setup_steam_page(self) -> None:
        layout = QVBoxLayout(self.page_steam)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        title = QLabel("Steam & Download Engine")
        title.setProperty("cssClass", "HeaderTitle")
        sub = QLabel("Configure your Steam directory and high-speed depot downloader.")
        sub.setProperty("cssClass", "SubHeader")
        layout.addWidget(title)
        layout.addWidget(sub)

        # Steam Path Group
        group_path = QGroupBox("Steam Installation Directory")
        path_layout = QVBoxLayout(group_path)
        path_layout.setSpacing(10)

        self.input_steam_path = QLineEdit()
        self.input_steam_path.setPlaceholderText("Path to Steam directory...")
        current_path = SettingsManager.get("steam_path", "") or (str(get_steam_path()) if get_steam_path() else "")
        self.input_steam_path.setText(current_path)

        path_btn_row = QHBoxLayout()
        self.btn_browse_steam = QPushButton("Browse...")
        self.btn_browse_steam.setProperty("cssClass", "SecondaryAction")
        self.btn_browse_steam.clicked.connect(self._browse_steam_path)
        path_btn_row.addWidget(self.btn_browse_steam)
        path_btn_row.addStretch()

        # Steam Library Selector
        lib_row = QHBoxLayout()
        lib_lbl = QLabel("Default Install Library:")
        lib_lbl.setStyleSheet("color: #94A3B8; font-weight: 600;")
        self.combo_steam_lib = QComboBox()
        from src.utils.paths import get_steam_libraries
        available_libs = get_steam_libraries()
        if not available_libs:
            available_libs = [current_path] if current_path else []
        self.combo_steam_lib.addItems(available_libs)
        pref_lib = SettingsManager.get("preferred_steam_library", "")
        if pref_lib in available_libs:
            self.combo_steam_lib.setCurrentText(pref_lib)

        lib_row.addWidget(lib_lbl)
        lib_row.addWidget(self.combo_steam_lib)
        lib_row.addStretch()

        path_layout.addWidget(self.input_steam_path)
        path_layout.addLayout(path_btn_row)
        path_layout.addLayout(lib_row)
        layout.addWidget(group_path)

        # Steam Integration Mode (Classic vs Moon)
        group_mode = QGroupBox("Steam Integration Mode")
        mode_layout = QVBoxLayout(group_mode)
        mode_layout.setSpacing(10)

        self.radio_classic = QRadioButton("Classic Mode (DepotDownloaderMod)")
        self.radio_classic.setToolTip("Downloads games safely and independently via DepotDownloader. Uses stable Headcrab SLSsteam.")
        self.radio_moon = QRadioButton("Native Steam Mode (slsteam-moon)")
        self.radio_moon.setToolTip("Steam itself downloads games natively. Requires slsteam-moon and can break with Steam updates.")

        cur_mode = SettingsManager.get("steam_integration_mode", "classic")
        if cur_mode == "moon":
            self.radio_moon.setChecked(True)
        else:
            self.radio_classic.setChecked(True)

        mode_layout.addWidget(self.radio_classic)
        mode_layout.addWidget(self.radio_moon)
        
        mode_desc = QLabel(
            "<b>Classic Mode</b> ensures stable independent downloads. <b>Native Mode</b> lets Steam handle downloads "
            "but is highly experimental and breaks on Steam updates."
        )
        mode_desc.setStyleSheet("color: #94A3B8; font-size: 11px;")
        mode_desc.setWordWrap(True)
        mode_layout.addWidget(mode_desc)

        layout.addWidget(group_mode)

        layout.addStretch()

    def _browse_steam_path(self) -> None:
        current = self.input_steam_path.text().strip() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "Select Steam Directory", current)
        if chosen:
            self.input_steam_path.setText(chosen)

    def _autodetect_steam_path(self) -> None:
        from src.utils.paths import get_steam_path
        detected = get_steam_path()
        if detected:
            self.input_steam_path.setText(str(detected))
            QMessageBox.information(self, "Auto-Detect", f"Found Steam at:\n{detected}")
        else:
            QMessageBox.warning(self, "Auto-Detect", "Could not automatically find Steam directory.")

    # =========================================================================
    # 3. ADVANCED TOOLS PAGE
    # =========================================================================
    def _setup_tools_page(self) -> None:
        layout = QVBoxLayout(self.page_tools)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        title = QLabel("Advanced Tools & Helpers")
        title.setProperty("cssClass", "HeaderTitle")
        sub = QLabel("Install required runtime components and management tools.")
        sub.setProperty("cssClass", "SubHeader")
        layout.addWidget(title)
        layout.addWidget(sub)
        # SLSsteam Card
        card_sls = QFrame()
        card_sls.setObjectName("SurfaceCard")
        sls_layout = QVBoxLayout(card_sls)
        sls_layout.setSpacing(10)

        sls_header_row = QHBoxLayout()
        sls_title = QLabel("⚡   SLSsteam (h3adcr-b tool)")
        sls_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #FFFFFF;")
        
        self.lbl_sls_status = QLabel("●  Checking...")
        self.lbl_sls_status.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700;")
        
        sls_header_row.addWidget(sls_title)
        sls_header_row.addStretch()
        sls_header_row.addWidget(self.lbl_sls_status)

        sls_desc = QLabel("Required for Steam to recognize manifest unlocks and apply DLL proxying.")
        sls_desc.setStyleSheet("color: #94A3B8; font-size: 12px;")

        sls_btn_row = QHBoxLayout()
        btn_install_sls = QPushButton("Install / Update SLSsteam")
        btn_install_sls.setProperty("cssClass", "PrimaryAction")
        btn_install_sls.clicked.connect(self._install_slssteam)

        btn_uninstall_sls = QPushButton("Uninstall SLSsteam")
        btn_uninstall_sls.setProperty("cssClass", "DangerAction")
        btn_uninstall_sls.clicked.connect(self._uninstall_slssteam)

        sls_btn_row.addWidget(btn_install_sls)
        sls_btn_row.addWidget(btn_uninstall_sls)
        sls_btn_row.addStretch()

        sls_layout.addLayout(sls_header_row)
        sls_layout.addWidget(sls_desc)
        sls_layout.addLayout(sls_btn_row)
        layout.addWidget(card_sls)

        # DDMod Card
        card_ddm = QFrame()
        card_ddm.setObjectName("SurfaceCard")
        ddm_layout = QVBoxLayout(card_ddm)
        ddm_layout.setSpacing(10)

        ddm_header_row = QHBoxLayout()
        ddm_title = QLabel("📥   DepotDownloaderMod (Standalone Linux-x64)")
        ddm_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #FFFFFF;")

        self.lbl_ddm_status = QLabel("●  Checking...")
        self.lbl_ddm_status.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700;")

        ddm_header_row.addWidget(ddm_title)
        ddm_header_row.addStretch()
        ddm_header_row.addWidget(self.lbl_ddm_status)

        ddm_desc = QLabel("Self-contained Linux executable. Does not require .NET installed on your system.")
        ddm_desc.setStyleSheet("color: #94A3B8; font-size: 12px;")

        ddm_btn_row = QHBoxLayout()
        btn_install_ddm = QPushButton("Install / Update DDMod")
        btn_install_ddm.setProperty("cssClass", "PrimaryAction")
        btn_install_ddm.clicked.connect(self._install_ddmod)

        btn_uninstall_ddm = QPushButton("Uninstall DDMod")
        btn_uninstall_ddm.setProperty("cssClass", "DangerAction")
        btn_uninstall_ddm.clicked.connect(self._uninstall_ddmod)

        ddm_btn_row.addWidget(btn_install_ddm)
        ddm_btn_row.addWidget(btn_uninstall_ddm)
        ddm_btn_row.addStretch()

        ddm_layout.addLayout(ddm_header_row)
        ddm_layout.addWidget(ddm_desc)
        ddm_layout.addLayout(ddm_btn_row)
        layout.addWidget(card_ddm)

        layout.addStretch()
        self._update_tools_status()

    def _update_tools_status(self) -> None:
        # 1. Check SLSsteam status
        sls_paths = [
            Path.home() / ".local" / "share" / "SLSsteam",
            Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "SLSsteam",
            Path.home() / ".config" / "SLSsteam",
        ]
        if any(p.exists() for p in sls_paths):
            self.lbl_sls_status.setText("●  Installed")
            self.lbl_sls_status.setStyleSheet("color: #34D399; font-size: 11px; font-weight: 700;")
        else:
            self.lbl_sls_status.setText("○  Not Installed")
            self.lbl_sls_status.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700;")

        # 2. Check DDMod status
        ddm_path = SettingsManager.get("depotdownloadermod_path", "")
        if ddm_path and Path(ddm_path).exists():
            self.lbl_ddm_status.setText("●  Installed")
            self.lbl_ddm_status.setStyleSheet("color: #34D399; font-size: 11px; font-weight: 700;")
        else:
            self.lbl_ddm_status.setText("○  Not Installed")
            self.lbl_ddm_status.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 700;")

    def _install_slssteam(self) -> None:
        steam_path = self.input_steam_path.text().strip() or str(get_steam_path() or "")
        if not steam_path:
            QMessageBox.warning(self, "Error", "Please set your Steam path first.")
            return

        def _on_log(msg):
            pass

        def _on_done(success):
            self._update_tools_status()
            if success:
                QMessageBox.information(self, "Success", "SLSsteam installed successfully!\nPlease restart Steam.")
            else:
                QMessageBox.critical(self, "Error", "Failed to install SLSsteam. Check console output.")

        SLSsteamInstaller.run_installer_async(Path(steam_path), _on_log, _on_done)

    def _uninstall_slssteam(self) -> None:
        reply = QMessageBox.question(
            self, "Uninstall SLSsteam",
            "Are you sure you want to completely remove SLSsteam and its configurations?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        loop = get_async_loop()
        async def _async_uninstall():
            try:
                await SLSsteamInstaller.uninstall_slssteam()
                self._update_tools_status()
                QMessageBox.information(self, "Success", "SLSsteam has been uninstalled successfully.\nPlease restart Steam.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to uninstall SLSsteam: {e}")
        loop.create_task(_async_uninstall())

    def _install_ddmod(self) -> None:
        def _on_log(msg):
            pass

        def _on_done(success, err):
            self._update_tools_status()
            if success:
                QMessageBox.information(self, "Success", "DDMod installed successfully!\nDepotDownloader is ready to use.")
            else:
                QMessageBox.critical(self, "Error", f"Failed to install DDMod: {err}")

        DDModInstaller.run_installer_async(_on_log, _on_done)

    def _uninstall_ddmod(self) -> None:
        reply = QMessageBox.question(
            self, "Uninstall DDMod",
            "Are you sure you want to remove the standalone DepotDownloaderMod binary?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        loop = get_async_loop()
        async def _async_uninstall():
            try:
                await DDModInstaller.uninstall_ddmod()
                self._update_tools_status()
                QMessageBox.information(self, "Success", "DepotDownloaderMod has been removed.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to uninstall DDMod: {e}")
        loop.create_task(_async_uninstall())
    # =========================================================================
    def _on_test_sgdb_key(self) -> None:
        key = self.input_sgdb_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Test Key", "Please enter an API key first.")
            return

        self.btn_test_sgdb.setEnabled(False)
        self.btn_test_sgdb.setText("Testing...")

        import asyncio
        from src.utils.async_utils import get_async_loop
        import httpx

        async def _test():
            try:
                url = "https://www.steamgriddb.com/api/v2/profile"
                headers = {"Authorization": f"Bearer {key}"}
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("success"):
                            username = data.get("data", {}).get("username", "Unknown")
                            QMessageBox.information(self, "Test Key", f"✅ Valid key!\nLogged in as: {username}")
                        else:
                            QMessageBox.warning(self, "Test Key", f"❌ Invalid key: {data.get('errors', ['Unknown error'])}")
                    elif resp.status_code == 401:
                        QMessageBox.warning(self, "Test Key", "❌ Unauthorized: Invalid or expired API key")
                    else:
                        QMessageBox.warning(self, "Test Key", f"❌ Error: HTTP {resp.status_code}")
            except Exception as e:
                QMessageBox.critical(self, "Test Key", f"❌ Network error: {e}")
            finally:
                self.btn_test_sgdb.setEnabled(True)
                self.btn_test_sgdb.setText("Test Key")

        asyncio.run_coroutine_threadsafe(_test(), get_async_loop())

    # =========================================================================
    # SAVE SETTINGS
    # =========================================================================
    def _save_settings(self) -> None:
        SettingsManager.set("hubcap_api_key", self.input_hubcap_key.text().strip())
        SettingsManager.set("ryuu_api_key", self.input_ryuu_key.text().strip())
        
        p_idx = self.combo_manifest_provider.currentIndex()
        p_val = "auto" if p_idx == 0 else ("hubcap" if p_idx == 1 else "ryuu")
        SettingsManager.set("manifest_provider", p_val)

        SettingsManager.set("steamgriddb_api_key", self.input_sgdb_key.text().strip())
        
        steam_p = self.input_steam_path.text().strip()
        if steam_p:
            SettingsManager.set("steam_path", steam_p)

        pref_lib = self.combo_steam_lib.currentText().strip()
        if pref_lib:
            SettingsManager.set("preferred_steam_library", pref_lib)

        new_mode = "moon" if self.radio_moon.isChecked() else "classic"
        SettingsManager.set("steam_integration_mode", new_mode)
        SettingsManager.set("download_method", "ddmod")
        hubcap_api.clear_cache()
        self.accept()
