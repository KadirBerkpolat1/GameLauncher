import asyncio
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PySide6.QtCore import Qt
from src.config.slssteam import SLSsteamConfigManager
from src.ui.game_card import GameCard
from src.api.hubcap import hubcap_api
from src.ui.flow_layout import FlowLayout

class LibraryWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        header = QLabel("My Library")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(header)

        # Grid Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background-color: transparent;")

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background-color: transparent;")
        self.grid_layout = FlowLayout(self.grid_container, spacing=20)

        # Empty state label
        self.empty_label = QLabel("Your library is empty. Go to Search to add games.")
        self.empty_label.setStyleSheet("color: #777777; font-size: 16px;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.grid_layout.addWidget(self.empty_label)

        self.scroll_area.setWidget(self.grid_container)
        layout.addWidget(self.scroll_area)

    def _clear_grid(self) -> None:
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item.widget() and item.widget() != self.empty_label:
                item.widget().deleteLater()

    def load_library(self) -> None:
        """Reads the SLSsteam config and populates the library view."""
        self._clear_grid()
        try:
            manager = SLSsteamConfigManager()
            # Combine AppIds and AdditionalApps to show everything in the launcher library
            app_ids = set(manager.config_data.get("AppIds", []) or [])
            app_ids.update(manager.config_data.get("AdditionalApps", []) or [])

            if not app_ids:
                self.empty_label.show()
                return

            self.empty_label.hide()

            # Fetch game details asynchronously
            loop = asyncio.get_event_loop()
            loop.create_task(self._fetch_and_display_library(list(app_ids)))

        except Exception as e:
            self.empty_label.setText(f"Error loading library: {e}")
            self.empty_label.show()

    async def _fetch_and_display_library(self, app_ids: list) -> None:
        import httpx

        async with httpx.AsyncClient() as client:
            for app_id in app_ids:
                title = f"App {app_id}"
                image_url = ""
                try:
                    steam_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
                    response = await client.get(steam_url, timeout=5.0)
                    if response.status_code == 200:
                        data = response.json()
                        app_data = data.get(str(app_id), {})
                        if app_data.get("success"):
                            title = app_data.get("data", {}).get("name", title)
                except Exception as e:
                    print(f"Error fetching name for {app_id}: {e}")

                card = GameCard(app_id, title, image_url, mode="library")
                self.grid_layout.addWidget(card)
