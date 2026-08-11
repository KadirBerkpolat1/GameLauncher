from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                                 QPushButton, QStackedWidget, QLabel, QSpacerItem, QSizePolicy, QButtonGroup)
from PySide6.QtCore import Qt, QSize
from src.ui.search_widget import SearchWidget
from src.ui.library_widget import LibraryWidget
from src.ui.downloads_widget import DownloadsWidget
from src.ui.settings_dialog import SettingsDialog
from src.ui.hubcap_tools_widget import HubcapToolsWidget

class MainWindow(QMainWindow):
    """
    The main application window, featuring a sidebar and a main content area.
    """
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Nebula Launcher")
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
        logo_label = QLabel("<h2><span style='color: #818CF8;'>✦</span> NEBULA</h2>")
        logo_label.setStyleSheet("color: #F8FAFC; font-weight: 900; padding-left: 12px; padding-bottom: 24px; padding-top: 10px; letter-spacing: 3px; font-size: 16px;")
        logo_label.setTextFormat(Qt.TextFormat.RichText)
        sidebar_layout.addWidget(logo_label)

        # Navigation Buttons
        self.btn_installer = self._create_nav_button("Installer")
        self.btn_library = self._create_nav_button("Library")
        self.btn_store = self._create_nav_button("Store")
        self.btn_downloads = self._create_nav_button("Downloads")
        self.btn_settings = self._create_nav_button("Settings")
        self.btn_support = self._create_nav_button("Support")
        
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_group.addButton(self.btn_installer)
        self.nav_group.addButton(self.btn_library)
        self.nav_group.addButton(self.btn_store)
        self.nav_group.addButton(self.btn_downloads)
        self.nav_group.addButton(self.btn_settings)
        self.nav_group.addButton(self.btn_support)

        sidebar_layout.addWidget(self.btn_installer)
        sidebar_layout.addWidget(self.btn_library)
        sidebar_layout.addWidget(self.btn_store)
        sidebar_layout.addWidget(self.btn_downloads)

        sidebar_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        sidebar_layout.addWidget(self.btn_settings)
        sidebar_layout.addWidget(self.btn_support)


        # Restart Steam Button (Pinned to bottom)
        self.btn_restart_steam = QPushButton("Restart Steam")
        self.btn_restart_steam.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restart_steam.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E293B, stop:1 #334155);
                color: #F8FAFC;
                border: 1px solid #475569;
                border-radius: 8px;
                padding: 12px 15px;
                margin: 4px 12px;
                font-weight: bold;
                text-align: center;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #334155, stop:1 #475569);
                border: 1px solid #94A3B8;
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
        
        self.support_view = self._create_placeholder("Support")

        # Stack index map: 0:Installer 1:Library 2:Store 3:Downloads 4:Support
        self.stack.addWidget(self.hubcap_tools_view)  # 0
        self.stack.addWidget(self.library_view)       # 1
        self.stack.addWidget(self.search_view)        # 2
        self.stack.addWidget(self.downloads_view)     # 3
        self.stack.addWidget(self.support_view)       # 4


        # Default to Installer
        self.btn_installer.setChecked(True)
        self.stack.setCurrentIndex(0)

        content_layout.addWidget(self.stack)

        # Add to main layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_wrapper)

        # Connections
        self.btn_installer.clicked.connect(lambda: self._switch_view(0, self.btn_installer))
        self.btn_library.clicked.connect(lambda: self._switch_view(1, self.btn_library))
        self.btn_store.clicked.connect(lambda: self._switch_view(2, self.btn_store))
        self.btn_downloads.clicked.connect(lambda: self._switch_view(3, self.btn_downloads))
        self.btn_support.clicked.connect(lambda: self._switch_view(4, self.btn_support))
        self.btn_settings.clicked.connect(self._open_settings)
        self.library_view.download_requested.connect(self._handle_download_request)
        self.library_view.restart_steam_requested.connect(self._restart_steam)

    def _handle_download_request(self, app_id: int, title: str) -> None:
        self._switch_view(3, self.btn_downloads)
        self.downloads_view.start_download(app_id, title)
    def _create_placeholder(self, text: str) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        lbl = QLabel(f"{text} view is under construction.")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
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
        elif index == 3:
            self.search_view._load_library()
        elif index == 4:
            pass # active downloads don't need reload
            
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
