from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                                 QPushButton, QStackedWidget, QLabel, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Qt, QSize
from src.ui.search_widget import SearchWidget
from src.ui.library_widget import LibraryWidget
from src.ui.downloads_widget import DownloadsWidget
from src.ui.settings_dialog import SettingsDialog
from src.ui.hubcap_tools_widget import HubcapToolsWidget
from src.ui.leaderboard_widget import LeaderboardWidget

class MainWindow(QMainWindow):
    """
    The main application window, featuring a sidebar and a main content area.
    """
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GameLauncher")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

        self.init_ui()

    def init_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Sidebar ---
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(5)

        # Profile / Logo area placeholder
        logo_label = QLabel("GAMELAUNCHER")
        logo_label.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold; padding-left: 20px; padding-bottom: 20px;")
        sidebar_layout.addWidget(logo_label)

        # Navigation Buttons
        self.btn_home = self._create_nav_button("Home")
        self.btn_installer = self._create_nav_button("Installer")
        self.btn_library = self._create_nav_button("Library")
        self.btn_store = self._create_nav_button("Store")
        self.btn_leaderboard = self._create_nav_button("Leaderboard")
        self.btn_downloads = self._create_nav_button("Downloads")
        self.btn_workshop = self._create_nav_button("Workshop")
        self.btn_cloud = self._create_nav_button("Cloud Saves")
        self.btn_tools = self._create_nav_button("Tools")
        self.btn_hubcap_tools = self._create_nav_button("SLSsteam")
        
        self.btn_settings = self._create_nav_button("Settings")
        self.btn_support = self._create_nav_button("Support")

        self.btn_library.setChecked(True) # Default active

        sidebar_layout.addWidget(self.btn_home)
        sidebar_layout.addWidget(self.btn_installer)
        sidebar_layout.addWidget(self.btn_library)
        sidebar_layout.addWidget(self.btn_store)
        sidebar_layout.addWidget(self.btn_leaderboard)
        sidebar_layout.addWidget(self.btn_downloads)
        sidebar_layout.addWidget(self.btn_workshop)
        sidebar_layout.addWidget(self.btn_cloud)
        sidebar_layout.addWidget(self.btn_tools)
        sidebar_layout.addWidget(self.btn_hubcap_tools)

        sidebar_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        sidebar_layout.addWidget(self.btn_settings)
        sidebar_layout.addWidget(self.btn_support)


        # Restart Steam Button (Pinned to bottom)
        self.btn_restart_steam = QPushButton("Restart Steam")
        self.btn_restart_steam.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restart_steam.setStyleSheet("""
            QPushButton {
                background-color: #2A475E;
                color: #FFFFFF;
                border: 1px solid #3B6B8E;
                border-radius: 6px;
                padding: 10px 15px;
                margin: 4px 10px;
                font-weight: bold;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #3B6B8E;
                border: 1px solid #66C0F4;
            }
        """)
        self.btn_restart_steam.clicked.connect(self._restart_steam)
        sidebar_layout.addWidget(self.btn_restart_steam)

        # --- Main Content Area ---
        content_wrapper = QWidget()
        content_wrapper.setObjectName("MainContent")
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()

        # Add Views
        self.library_view = LibraryWidget()
        self.search_view = SearchWidget()
        self.downloads_view = DownloadsWidget()
        self.hubcap_tools_view = HubcapToolsWidget()
        self.leaderboard_view = LeaderboardWidget()
        
        self.home_view = self._create_placeholder("Home")
        self.workshop_view = self._create_placeholder("Workshop")
        self.cloud_view = self._create_placeholder("Cloud Saves")
        self.tools_view = self._create_placeholder("Tools")
        self.support_view = self._create_placeholder("Support")

        # Add widgets in a specific index order:
        # 0: Home, 1: Installer (Hubcap), 2: Library, 3: Store, 4: Leaderboard, 
        # 5: Downloads, 6: Workshop, 7: Cloud, 8: Tools, 9: HubcapTools, 10: Support
        self.stack.addWidget(self.home_view)          # 0
        self.stack.addWidget(self.hubcap_tools_view)  # 1 (Installer goes to HubcapTools for now)
        self.stack.addWidget(self.library_view)       # 2
        self.stack.addWidget(self.search_view)        # 3
        self.stack.addWidget(self.leaderboard_view)   # 4
        self.stack.addWidget(self.downloads_view)     # 5
        self.stack.addWidget(self.workshop_view)      # 6
        self.stack.addWidget(self.cloud_view)         # 7
        self.stack.addWidget(self.tools_view)         # 8
        self.stack.addWidget(self.hubcap_tools_view)  # 9 (Same view as Installer)
        self.stack.addWidget(self.support_view)       # 10


        content_layout.addWidget(self.stack)

        # Add to main layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_wrapper)

        # Connections
        self.btn_home.clicked.connect(lambda: self._switch_view(0, self.btn_home))
        self.btn_installer.clicked.connect(lambda: self._switch_view(1, self.btn_installer))
        self.btn_library.clicked.connect(lambda: self._switch_view(2, self.btn_library))
        self.btn_store.clicked.connect(lambda: self._switch_view(3, self.btn_store))
        self.btn_leaderboard.clicked.connect(lambda: self._switch_view(4, self.btn_leaderboard))
        self.btn_downloads.clicked.connect(lambda: self._switch_view(5, self.btn_downloads))
        self.btn_workshop.clicked.connect(lambda: self._switch_view(6, self.btn_workshop))
        self.btn_cloud.clicked.connect(lambda: self._switch_view(7, self.btn_cloud))
        self.btn_tools.clicked.connect(lambda: self._switch_view(8, self.btn_tools))
        self.btn_hubcap_tools.clicked.connect(lambda: self._switch_view(9, self.btn_hubcap_tools))
        self.btn_support.clicked.connect(lambda: self._switch_view(10, self.btn_support))
        
        self.btn_settings.clicked.connect(self._open_settings)

    def _create_placeholder(self, text: str) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        lbl = QLabel(f"{text} - Coming Soon")
        lbl.setStyleSheet("color: #777777; font-size: 24px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(lbl)
        return w


    def _create_nav_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _switch_view(self, index: int, active_btn: QPushButton) -> None:
        self.stack.setCurrentIndex(index)

        # Refresh specific views when switched to
        if index == 2:
            self.library_view.load_library()
        elif index == 5:
            self.downloads_view.load_queue()

        # Manage active state styling (toggling checks)
        all_btns = [
            self.btn_home, self.btn_installer, self.btn_library, 
            self.btn_store, self.btn_leaderboard, self.btn_downloads, 
            self.btn_workshop, self.btn_cloud, self.btn_tools, 
            self.btn_hubcap_tools, self.btn_support
        ]
        for btn in all_btns:
            if btn != active_btn:
                btn.setChecked(False)
        active_btn.setChecked(True)


    def _open_settings(self) -> None:
        # Settings is a dialog, so we don't switch the stack, we pop it open
        self.btn_settings.setChecked(False) # Don't keep it checked
        dialog = SettingsDialog(self)
        dialog.exec()

    def _restart_steam(self) -> None:
        """Gracefully shuts down Steam and restarts it so VDF changes take effect."""
        import subprocess
        from PySide6.QtCore import QTimer
        try:
            self.btn_restart_steam.setText("Restarting...")
            self.btn_restart_steam.setEnabled(False)

            # Check if Steam is running
            res = subprocess.run(["pgrep", "-x", "steam"], capture_output=True)
            if res.returncode == 0:
                # Steam is running, shut it down gracefully
                subprocess.run(["steam", "-shutdown"], check=False)
                QTimer.singleShot(3000, self._start_steam_again)
            else:
                # Steam is not running, just start it
                self._start_steam_again()
        except Exception as e:
            print(f"Failed to check/shutdown steam: {e}")
            self.btn_restart_steam.setText("Restart Steam")
            self.btn_restart_steam.setEnabled(True)

    def _start_steam_again(self) -> None:
        import subprocess
        try:
            # 2. Start Steam in the background
            subprocess.Popen(["steam"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.btn_restart_steam.setText("Restart Steam")
            self.btn_restart_steam.setEnabled(True)
        except Exception as e:
            print(f"Failed to start steam: {e}")
            self.btn_restart_steam.setText("Restart Steam")
            self.btn_restart_steam.setEnabled(True)
