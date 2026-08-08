from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                                 QPushButton, QStackedWidget, QLabel, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Qt, QSize
from src.ui.search_widget import SearchWidget
from src.ui.library_widget import LibraryWidget
from src.ui.downloads_widget import DownloadsWidget
from src.ui.settings_dialog import SettingsDialog

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
        self.btn_library = self._create_nav_button("Library")
        self.btn_search = self._create_nav_button("Search Games")
        self.btn_downloads = self._create_nav_button("Downloads")
        self.btn_settings = self._create_nav_button("Settings")

        self.btn_library.setChecked(True) # Default active

        sidebar_layout.addWidget(self.btn_library)
        sidebar_layout.addWidget(self.btn_search)
        sidebar_layout.addWidget(self.btn_downloads)

        sidebar_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        sidebar_layout.addWidget(self.btn_settings)

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

        self.stack.addWidget(self.library_view)
        self.stack.addWidget(self.search_view)
        self.stack.addWidget(self.downloads_view)

        content_layout.addWidget(self.stack)

        # Add to main layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_wrapper)

        # Connections
        self.btn_library.clicked.connect(lambda: self._switch_view(0, self.btn_library))
        self.btn_search.clicked.connect(lambda: self._switch_view(1, self.btn_search))
        self.btn_downloads.clicked.connect(lambda: self._switch_view(2, self.btn_downloads))
        self.btn_settings.clicked.connect(self._open_settings)

    def _create_nav_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _switch_view(self, index: int, active_btn: QPushButton) -> None:
        self.stack.setCurrentIndex(index)

        # Refresh specific views when switched to
        if index == 0:
            self.library_view.load_library()
        elif index == 2:
            self.downloads_view.load_queue()

        # Manage active state styling (toggling checks)
        for btn in [self.btn_library, self.btn_search, self.btn_downloads]:
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
        import time
        try:
            self.btn_restart_steam.setText("Restarting...")
            self.btn_restart_steam.setEnabled(False)

            # 1. Gracefully tell Steam to shut down
            subprocess.run(["steam", "-shutdown"], check=False)

            # Wait a few seconds for Steam to fully write its configs and exit
            # We use a QTimer to avoid blocking the UI thread
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, self._start_steam_again)
        except Exception as e:
            print(f"Failed to shutdown steam: {e}")
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
