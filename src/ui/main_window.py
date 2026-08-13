import asyncio
import shutil
import subprocess
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QPushButton, QStackedWidget, QLabel, QSpacerItem, 
                               QSizePolicy, QButtonGroup, QFrame)
from PySide6.QtCore import Qt, QTimer
from src.utils.async_utils import get_async_loop
from src.ui.search_widget import SearchWidget
from src.ui.library_widget import LibraryWidget
from src.ui.downloads_widget import DownloadsWidget
from src.ui.settings_dialog import SettingsDialog
from src.ui.hubcap_tools_widget import HubcapToolsWidget


class MainWindow(QMainWindow):
    """
    The redesigned main application window featuring a sleek cyber-dark sidebar,
    live Steam status monitor, categorized views, and smooth view switching.
    """
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Nebula Game Launcher")
        self.resize(1280, 840)
        self.setMinimumSize(980, 660)

        self.init_ui()
        self._start_steam_monitor()

    def init_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # =====================================================================
        # SIDEBAR
        # =====================================================================
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 24, 0, 20)
        sidebar_layout.setSpacing(6)

        # App Brand & Logo - Clean modern typography
        brand_container = QWidget()
        brand_layout = QHBoxLayout(brand_container)
        brand_layout.setContentsMargins(20, 0, 20, 18)
        brand_layout.setSpacing(12)

        logo_box = QLabel("✦")
        logo_box.setFixedSize(34, 34)
        logo_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_box.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4F46E5, stop:1 #7C3AED);
            color: #FFFFFF;
            font-size: 16px;
            border-radius: 8px;
            border: 1px solid #818CF8;
        """)

        text_box = QVBoxLayout()
        text_box.setSpacing(1)
        text_box.setContentsMargins(0, 0, 0, 0)
        
        logo_title = QLabel("Nebula")
        logo_title.setStyleSheet("""
            color: #F8FAFC;
            font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
            font-size: 16px;
            font-weight: 700;
            letter-spacing: 0.5px;
        """)
        
        subtitle = QLabel("GAME LAUNCHER")
        subtitle.setStyleSheet("""
            color: #818CF8;
            font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 1px;
        """)

        text_box.addWidget(logo_title)
        text_box.addWidget(subtitle)

        brand_layout.addWidget(logo_box)
        brand_layout.addLayout(text_box)
        brand_layout.addStretch()

        sidebar_layout.addWidget(brand_container)

        # Navigation Section Label
        nav_lbl = QLabel("MENU")
        nav_lbl.setStyleSheet("color: #475569; font-size: 10px; font-weight: 800; padding: 6px 22px 2px 22px; letter-spacing: 1.2px;")
        sidebar_layout.addWidget(nav_lbl)

        # Nav Buttons with Icons
        self.btn_installer = self._create_nav_button("📥   Installer")
        self.btn_library = self._create_nav_button("🎮   My Library")
        self.btn_store = self._create_nav_button("🛍️   Hubcap Store")
        self.btn_downloads = self._create_nav_button("⚡   Downloads")
        
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_group.addButton(self.btn_installer)
        self.nav_group.addButton(self.btn_library)
        self.nav_group.addButton(self.btn_store)
        self.nav_group.addButton(self.btn_downloads)

        sidebar_layout.addWidget(self.btn_installer)
        sidebar_layout.addWidget(self.btn_library)
        sidebar_layout.addWidget(self.btn_store)
        sidebar_layout.addWidget(self.btn_downloads)

        sidebar_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Bottom System Controls
        sys_lbl = QLabel("SYSTEM")
        sys_lbl.setStyleSheet("color: #475569; font-size: 10px; font-weight: 800; padding: 6px 22px 2px 22px; letter-spacing: 1.2px;")
        sidebar_layout.addWidget(sys_lbl)

        self.btn_settings = self._create_nav_button("⚙️   Settings")
        self.btn_settings.clicked.connect(self._open_settings)
        sidebar_layout.addWidget(self.btn_settings)

        # Steam Status Unified Pill
        self.steam_status_frame = QFrame()
        self.steam_status_frame.setFixedHeight(40)
        self.steam_status_frame.setStyleSheet("""
            QFrame {
                background-color: #121522;
                border: 1px solid #1E243A;
                border-radius: 8px;
                margin: 4px 12px;
            }
        """)
        status_layout = QHBoxLayout(self.steam_status_frame)
        status_layout.setContentsMargins(12, 0, 12, 0)
        status_layout.setSpacing(8)

        self.steam_dot = QLabel("●")
        self.steam_dot.setStyleSheet("color: #94A3B8; font-size: 12px;")
        
        self.steam_text = QLabel("Steam Offline")
        self.steam_text.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")

        status_layout.addWidget(self.steam_dot)
        status_layout.addWidget(self.steam_text)
        status_layout.addStretch()

        sidebar_layout.addWidget(self.steam_status_frame)

        # Restart Steam Button
        self.btn_restart_steam = QPushButton("🔄   Restart Steam")
        self.btn_restart_steam.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restart_steam.setFixedHeight(42)
        self.btn_restart_steam.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E243A, stop:1 #283252);
                color: #F8FAFC;
                border: 1px solid #333F66;
                border-radius: 8px;
                padding: 6px 14px;
                margin: 4px 12px;
                font-weight: 700;
                font-size: 13px;
                text-align: center;
                letter-spacing: 0.3px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #283252, stop:1 #3B4A78);
                border: 1px solid #6366F1;
                color: #FFFFFF;
            }
        """)
        self.btn_restart_steam.clicked.connect(self._restart_steam)
        sidebar_layout.addWidget(self.btn_restart_steam)
        # =====================================================================
        # MAIN CONTENT AREA
        # =====================================================================
        content_wrapper = QWidget()
        content_wrapper.setObjectName("MainContent")
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()

        # Add Views
        self.hubcap_tools_view = HubcapToolsWidget()  # 0: Installer
        self.library_view = LibraryWidget()           # 1: Library
        self.search_view = SearchWidget()             # 2: Store / Search
        self.downloads_view = DownloadsWidget()       # 3: Downloads

        self.stack.addWidget(self.hubcap_tools_view)
        self.stack.addWidget(self.library_view)
        self.stack.addWidget(self.search_view)
        self.stack.addWidget(self.downloads_view)

        # Connect Navigation
        self.btn_installer.clicked.connect(lambda: self._switch_view(0))
        self.btn_library.clicked.connect(lambda: self._switch_view(1))
        self.btn_store.clicked.connect(lambda: self._switch_view(2))
        self.btn_downloads.clicked.connect(lambda: self._switch_view(3))

        # Default view: Library
        self.btn_library.setChecked(True)
        self.stack.setCurrentIndex(1)

        content_layout.addWidget(self.stack)

        # Add sidebar and content to main layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_wrapper)

        # Wire cross-widget signals
        self.search_view.download_requested.connect(self._handle_download_requested)
        self.library_view.download_requested.connect(self._handle_download_requested)
        self.library_view.restart_steam_requested.connect(self._restart_steam)

    def _create_nav_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _switch_view(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        if index == 1:
            self.library_view.refresh_library()
        elif index == 3:
            self.downloads_view._load_history()

    def _handle_download_requested(self, app_id: int, title: str) -> None:
        self.btn_downloads.setChecked(True)
        self.stack.setCurrentIndex(3)
        self.downloads_view.start_download(app_id, title)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self)
        dialog.exec()
        self.library_view.refresh_library()

    def _start_steam_monitor(self) -> None:
        """Polls Steam process status every 5 seconds to update the status pill."""
        self._steam_timer = QTimer(self)
        self._steam_timer.timeout.connect(self._update_steam_status)
        self._steam_timer.start(5000)
        self._update_steam_status()

    def _update_steam_status(self) -> None:
        try:
            res = subprocess.run(["pgrep", "-x", "steam"], capture_output=True)
            if res.returncode == 0:
                self.steam_dot.setText("●")
                self.steam_dot.setStyleSheet("color: #34D399; font-size: 12px;")
                self.steam_text.setText("Steam Running")
                self.steam_text.setStyleSheet("color: #34D399; font-size: 12px; font-weight: 600;")
            else:
                self.steam_dot.setText("●")
                self.steam_dot.setStyleSheet("color: #94A3B8; font-size: 12px;")
                self.steam_text.setText("Steam Offline")
                self.steam_text.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")
        except Exception:
            pass

    def _restart_steam(self) -> None:
        self.btn_restart_steam.setEnabled(False)
        self.btn_restart_steam.setText("⏳   Closing Steam...")
        get_async_loop().create_task(self._async_restart_steam())

    async def _async_restart_steam(self) -> None:
        try:
            # Check if Steam is running
            proc = await asyncio.create_subprocess_exec(
                "pgrep", "-x", "steam",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            is_running = (proc.returncode == 0)

            if is_running:
                # Graceful shutdown request
                try:
                    shutdown_proc = await asyncio.create_subprocess_exec(
                        "steam", "-shutdown",
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL
                    )
                    try:
                        await asyncio.wait_for(shutdown_proc.wait(), timeout=2.5)
                    except asyncio.TimeoutError:
                        pass
                except Exception:
                    pass

                await asyncio.sleep(1.0)

                # Check if still running; if so, kill it
                check_proc = await asyncio.create_subprocess_exec(
                    "pgrep", "-x", "steam",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await check_proc.wait()
                if check_proc.returncode == 0:
                    kill_proc = await asyncio.create_subprocess_exec(
                        "pkill", "-TERM", "-x", "steam",
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL
                    )
                    await kill_proc.wait()
                    await asyncio.sleep(1.0)

            self.btn_restart_steam.setText("🚀   Starting Steam...")
            await asyncio.sleep(0.5)

            if shutil.which("steam"):
                subprocess.Popen(
                    ["steam"],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            elif shutil.which("flatpak"):
                subprocess.Popen(
                    ["flatpak", "run", "com.valvesoftware.Steam"],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            await asyncio.sleep(3.0)
        except Exception as e:
            print(f"Error during Steam restart: {e}")
        finally:
            self.btn_restart_steam.setText("🔄   Restart Steam")
            self.btn_restart_steam.setEnabled(True)
            self._update_steam_status()
