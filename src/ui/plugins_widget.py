import asyncio
import webbrowser
import secrets
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QComboBox, QLineEdit, QFileDialog,
    QTextEdit, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer

from src.services.plugin_manager import PluginManager
from src.services.cloud_redirect import CloudRedirectManager, CR_TOKENS_DIR
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

        # Status row
        status_row = QHBoxLayout()
        self.lbl_cr_status = QLabel("Checking hook status...")
        self.lbl_cr_status.setStyleSheet("color: #38BDF8; font-weight: 700; font-size: 13px;")
        self.lbl_cr_auth = QLabel("")
        self.lbl_cr_auth.setStyleSheet("color: #10B981; font-weight: 600; font-size: 12px;")
        status_row.addWidget(self.lbl_cr_status)
        status_row.addWidget(self.lbl_cr_auth)
        status_row.addStretch()
        cloud_layout.addLayout(status_row)

        # Provider selection
        provider_layout = QHBoxLayout()
        provider_lbl = QLabel("Provider:")
        provider_lbl.setStyleSheet("color: #94A3B8; font-weight: 600;")
        self.combo_provider = QComboBox()
        self.combo_provider.addItems(["Local Directory", "Google Drive", "OneDrive"])
        self.combo_provider.currentIndexChanged.connect(self._on_provider_changed)

        provider_layout.addWidget(provider_lbl)
        provider_layout.addWidget(self.combo_provider)
        provider_layout.addStretch()
        cloud_layout.addLayout(provider_layout)

        # Cloud root path (for local) or OAuth button (for gdrive/onedrive)
        self.cloud_config_stack = QVBoxLayout()
        self.cloud_config_stack.setSpacing(8)

        # --- Local Directory page ---
        self.page_local = QWidget()
        local_layout = QHBoxLayout(self.page_local)
        local_layout.setContentsMargins(0, 0, 0, 0)
        path_lbl = QLabel("Cloud Root:")
        path_lbl.setStyleSheet("color: #94A3B8; font-weight: 600;")
        self.txt_save_path = QLineEdit()
        self.txt_save_path.setText(str(Path.home() / ".local" / "share" / "CloudRedirect" / "cloud_storage"))
        self.btn_browse_path = QPushButton("Browse...")
        self.btn_browse_path.setProperty("cssClass", "SecondaryAction")
        self.btn_browse_path.clicked.connect(self._on_browse_save_path)
        local_layout.addWidget(path_lbl)
        local_layout.addWidget(self.txt_save_path)
        local_layout.addWidget(self.btn_browse_path)
        self.cloud_config_stack.addWidget(self.page_local)

        # --- Google Drive / OneDrive page ---
        self.page_oauth = QWidget()
        oauth_layout = QVBoxLayout(self.page_oauth)
        oauth_layout.setContentsMargins(0, 0, 0, 0)
        oauth_layout.setSpacing(8)

        oauth_info = QLabel("Click 'Authorize' to sign in and grant access to your cloud storage.\nYour credentials are stored locally in ~/.local/share/CloudRedirect/tokens/")
        oauth_info.setWordWrap(True)
        oauth_info.setStyleSheet("color: #818CF8; font-size: 12px;")
        oauth_layout.addWidget(oauth_info)

        oauth_btn_row = QHBoxLayout()
        self.btn_oauth_authorize = QPushButton("🔐  Authorize")
        self.btn_oauth_authorize.setProperty("cssClass", "PrimaryAction")
        self.btn_oauth_authorize.clicked.connect(self._on_oauth_authorize)
        self.btn_oauth_revoke = QPushButton("🚫  Revoke Access")
        self.btn_oauth_revoke.setProperty("cssClass", "DangerAction")
        self.btn_oauth_revoke.clicked.connect(self._on_oauth_revoke)
        self.lbl_oauth_status = QLabel("Not authenticated")
        self.lbl_oauth_status.setStyleSheet("color: #F87171; font-weight: 600; font-size: 12px;")
        oauth_btn_row.addWidget(self.btn_oauth_authorize)
        oauth_btn_row.addWidget(self.btn_oauth_revoke)
        oauth_btn_row.addWidget(self.lbl_oauth_status)
        oauth_btn_row.addStretch()
        oauth_layout.addLayout(oauth_btn_row)
        self.cloud_config_stack.addWidget(self.page_oauth)

        cloud_layout.addLayout(self.cloud_config_stack)

        # Game list with checkboxes
        games_label = QLabel("Apply CloudRedirect to games:")
        games_label.setStyleSheet("color: #94A3B8; font-weight: 600; margin-top: 8px;")
        cloud_layout.addWidget(games_label)

        self.games_list = QTextEdit()
        self.games_list.setReadOnly(True)
        self.games_list.setFixedHeight(150)
        self.games_list.setStyleSheet("""
            background-color: #06080E;
            color: #A5B4FC;
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 11px;
            border: 1px solid #1E2337;
            border-radius: 8px;
            padding: 8px;
        """)
        cloud_layout.addWidget(self.games_list)

        games_btn_row = QHBoxLayout()
        self.btn_apply_to_selected = QPushButton("✅  Apply to Selected")
        self.btn_apply_to_selected.setProperty("cssClass", "PrimaryAction")
        self.btn_apply_to_selected.clicked.connect(self._on_apply_hook)
        self.btn_remove_from_selected = QPushButton("❌  Remove from Selected")
        self.btn_remove_from_selected.setProperty("cssClass", "DangerAction")
        self.btn_remove_from_selected.clicked.connect(self._on_remove_hook)
        games_btn_row.addWidget(self.btn_apply_to_selected)
        games_btn_row.addWidget(self.btn_remove_from_selected)
        games_btn_row.addStretch()
        cloud_layout.addLayout(games_btn_row)

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

        cr_installed = CloudRedirectManager.is_installed()
        if cr_installed:
            self.lbl_cr_status.setText("●  CloudRedirect: Hook Installed")
            self.lbl_cr_status.setStyleSheet("color: #10B981; font-weight: 700; font-size: 13px;")
        else:
            self.lbl_cr_status.setText("○  CloudRedirect: Hook Not Installed")
            self.lbl_cr_status.setStyleSheet("color: #64748B; font-weight: 700; font-size: 13px;")

        cr_cfg = CloudRedirectManager.get_config()
        active_provider = cr_cfg.get("provider", "local")
        self.txt_save_path.setText(cr_cfg.get("cloud_root", str(Path.home() / ".local" / "share" / "CloudRedirect" / "cloud_storage")))

        p_indices = {"local": 0, "gdrive": 1, "onedrive": 2}
        self.combo_provider.setCurrentIndex(p_indices.get(active_provider, 0))
        self._on_provider_changed(p_indices.get(active_provider, 0))

        # Update OAuth status label
        if active_provider != "local":
            authed = CloudRedirectManager.is_authenticated(active_provider)
            self.lbl_oauth_status.setText("✅ Authenticated" if authed else "❌ Not authenticated")
            self.lbl_oauth_status.setStyleSheet(
                "color: #10B981; font-weight: 600; font-size: 12px;"
                if authed else
                "color: #F87171; font-weight: 600; font-size: 12px;"
            )
        else:
            self.lbl_oauth_status.setText("")

        # Update games list
        self._refresh_games_list()

    def _on_provider_changed(self, index: int) -> None:
        p_map = {0: "local", 1: "gdrive", 2: "onedrive"}
        provider = p_map.get(index, "local")

        if provider == "local":
            self.page_local.setVisible(True)
            self.page_oauth.setVisible(False)
        else:
            self.page_local.setVisible(False)
            self.page_oauth.setVisible(True)
            # Update auth status for this provider
            authed = CloudRedirectManager.is_authenticated(provider)
            self.lbl_oauth_status.setText("✅ Authenticated" if authed else "❌ Not authenticated")
            self.lbl_oauth_status.setStyleSheet(
                "color: #10B981; font-weight: 600; font-size: 12px;"
                if authed else
                "color: #F87171; font-weight: 600; font-size: 12px;"
            )

    def _on_browse_save_path(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Cloud Root Folder", self.txt_save_path.text())
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
                ok = await CloudRedirectManager.install_binary(progress_callback=self.log)
                if ok:
                    self.log("✓ CloudRedirect hook ready.")
                else:
                    self.log("✗ CloudRedirect installation failed.")
            except Exception as e:
                self.log(f"✗ CloudRedirect error: {e}")
            finally:
                self.btn_install_cr.setEnabled(True)
                self.refresh_status()

        asyncio.run_coroutine_threadsafe(_task(), get_async_loop())

    def _on_save_cloud_settings(self) -> None:
        p_map = {0: "local", 1: "gdrive", 2: "onedrive"}
        provider = p_map.get(self.combo_provider.currentIndex(), "local")

        cfg = {
            "enabled": True,
            "provider": provider,
            "cloud_root": self.txt_save_path.text().strip()
        }
        CloudRedirectManager.save_config(cfg)

        if provider == "local":
            CloudRedirectManager.set_cloud_root(cfg["cloud_root"])
            self.log(f"✓ Cloud settings saved: Provider=Local, Cloud Root={cfg['cloud_root']}")
        else:
            self.log(f"✓ Cloud settings saved: Provider={provider} (use Authorize to authenticate)")

        self.refresh_status()

    def _on_oauth_authorize(self) -> None:
        p_map = {0: "local", 1: "gdrive", 2: "onedrive"}
        provider = p_map.get(self.combo_provider.currentIndex(), "local")

        if provider == "local":
            return

        self.btn_oauth_authorize.setEnabled(False)
        self.lbl_oauth_status.setText("🔄 Opening browser...")
        self.lbl_oauth_status.setStyleSheet("color: #FBBF24; font-weight: 600; font-size: 12px;")

        import secrets
        state = secrets.token_urlsafe(16)
        auth_url = CloudRedirectManager.build_auth_url(provider, state)

        if not auth_url:
            self.log(f"✗ OAuth not configured for {provider}")
            self.btn_oauth_authorize.setEnabled(True)
            return

        self.log(f"Opening {provider} authorization URL...")
        webbrowser.open(auth_url)

        # Start local server to catch callback
        self._start_oauth_callback_server(provider, state)

    def _start_oauth_callback_server(self, provider: str, state: str) -> None:
        from aiohttp import web
        import asyncio

        async def handle_callback(request):
            query = request.query
            code = query.get("code")
            returned_state = query.get("state")
            error = query.get("error")

            if error:
                self.log(f"✗ OAuth error: {error}")
                return web.Response(text=f"<h2>Authorization failed: {error}</h2>", content_type="text/html")

            if not code or returned_state != state:
                self.log("✗ Invalid OAuth callback")
                return web.Response(text="<h2>Invalid callback</h2>", content_type="text/html")

            # Exchange code for tokens
            tokens = await CloudRedirectManager.exchange_code_for_token(provider, code)
            if tokens:
                CloudRedirectManager.save_tokens(provider, tokens)
                self.log(f"✓ {provider} authenticated successfully!")
                # Schedule UI update on main thread
                QTimer.singleShot(0, self.refresh_status)
                return web.Response(text="<h2>Success! You can close this window.</h2>", content_type="text/html")
            else:
                self.log(f"✗ Token exchange failed for {provider}")
                return web.Response(text="<h2>Token exchange failed</h2>", content_type="text/html")

        app = web.Application()
        app.router.add_get("/oauth2callback", handle_callback)

        async def run_server():
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "localhost", 8080)
            await site.start()
            self._oauth_runner = runner
            self.log("OAuth callback server started on http://localhost:8080")

        asyncio.run_coroutine_threadsafe(run_server(), get_async_loop())

    def _on_oauth_revoke(self) -> None:
        p_map = {0: "local", 1: "gdrive", 2: "onedrive"}
        provider = p_map.get(self.combo_provider.currentIndex(), "local")

        if provider == "local":
            return

        # Delete token file
        from src.services.cloud_redirect import CR_TOKENS_DIR
        token_file = CR_TOKENS_DIR / f"tokens_{provider}.json"
        if token_file.exists():
            token_file.unlink()

        # Clear from config
        prov_cfg = CloudRedirectManager.get_provider_config(provider)
        prov_cfg.pop("token_path", None)
        CloudRedirectManager.set_provider_config(provider, prov_cfg)

        self.log(f"✓ {provider} access revoked")
        self.refresh_status()

    def _refresh_games_list(self) -> None:
        try:
            from src.services.acf import get_installed_games
            games = get_installed_games()
            hooked = CloudRedirectManager.get_hooked_games()
            hooked_set = set(hooked)

            lines = []
            for game in games:
                app_id = game.get("appid", 0)
                name = game.get("name", "Unknown")
                is_hooked = app_id in hooked_set
                status = "✅" if is_hooked else "⬜"
                lines.append(f"{status}  {app_id:>8}  {name}")

            self.games_list.setPlainText("\n".join(lines))
        except Exception as e:
            self.games_list.setPlainText(f"Error loading games: {e}")

    def _on_apply_hook(self) -> None:
        self._apply_hook_to_selected(apply=True)

    def _on_remove_hook(self) -> None:
        self._apply_hook_to_selected(apply=False)

    def _apply_hook_to_selected(self, apply: bool) -> None:
        # Simple: parse selected lines from games_list (in a real app, use a proper QListWidget with checkboxes)
        # For now, apply to all games shown
        try:
            from src.services.acf import get_installed_games
            games = get_installed_games()
            count = 0
            for game in games:
                app_id = game.get("appid", 0)
                if apply:
                    if CloudRedirectManager.apply_game_hook(app_id):
                        count += 1
                else:
                    if CloudRedirectManager.remove_game_hook(app_id):
                        count += 1

            action = "Applied" if apply else "Removed"
            self.log(f"✓ {action} CloudRedirect hook to {count} games")
            self.refresh_status()
        except Exception as e:
            self.log(f"✗ Error: {e}")
