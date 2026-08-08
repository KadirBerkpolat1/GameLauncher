import asyncio
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QScrollArea, QLabel
from PySide6.QtCore import Qt, QTimer
from src.api.hubcap import hubcap_api
from src.ui.game_card import GameCard
from src.ui.flow_layout import FlowLayout

class SearchWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.init_ui()
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Top Bar (Search Input)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for games to add...")
        self.search_input.setMinimumHeight(45)
        self.search_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.search_input)

        # Results Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background-color: transparent;")

        self.results_container = QWidget()
        self.results_container.setStyleSheet("background-color: transparent;")
        self.results_layout = FlowLayout(self.results_container, spacing=20)

        # Status Label
        self.status_label = QLabel("Type at least 3 characters to search.")
        self.status_label.setStyleSheet("color: #777777; font-size: 16px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_layout.addWidget(self.status_label)

        self.scroll_area.setWidget(self.results_container)
        layout.addWidget(self.scroll_area)

    def _on_text_changed(self, text: str) -> None:
        if len(text) >= 3:
            self.status_label.setText("Searching API...")
            self.status_label.show()
            self.search_timer.start(500) # 500ms debounce
        else:
            self.search_timer.stop()
            self._clear_results()
            self.status_label.setText("Type at least 3 characters to search.")
            self.status_label.show()

    def _clear_results(self) -> None:
        # Remove all widgets except the status label
        for i in reversed(range(self.results_layout.count())):
            item = self.results_layout.itemAt(i)
            if item.widget() and item.widget() != self.status_label:
                item.widget().deleteLater()

    def _perform_search(self) -> None:
        query = self.search_input.text()
        # Fire and forget the async task using the global loop
        loop = asyncio.get_event_loop()
        loop.create_task(self._fetch_from_api(query))

    async def _fetch_from_api(self, query: str) -> None:
        import httpx
        try:
            # 1. Fetch from HubcapManifest API
            results = await hubcap_api.search_game(query)

            # 2. Inject results directly from Steam Store API to guarantee exact matches
            try:
                async with httpx.AsyncClient() as client:
                    steam_resp = await client.get(f"https://store.steampowered.com/api/storesearch/?term={query}&l=english&cc=US", timeout=5.0)
                    if steam_resp.status_code == 200:
                        steam_data = steam_resp.json().get("items", [])
                        for item in steam_data:
                            # If it's a very close match, inject it at the very top of our results
                            if query.lower() in item.get("name", "").lower():
                                # Check if it's already in the results list to avoid duplicates
                                if not any(str(g.get("game_id", "")) == str(item["id"]) for g in results):
                                    results.insert(0, {
                                        "game_id": str(item["id"]),
                                        "game_name": item["name"],
                                        "header_image": item.get("tiny_image", "")
                                    })
            except Exception as steam_err:
                print(f"Steam API Search Fallback failed: {steam_err}")

            self._display_results(results)
        except Exception as e:
            self._clear_results()
            self.status_label.setText(f"Error: {e}")
            self.status_label.show()

    def _display_results(self, results: list) -> None:
        self._clear_results()

        if not results:
            self.status_label.setText("No games found.")
            self.status_label.show()
            return

        self.status_label.hide()

        # Sort exact match to the top
        query = self.search_input.text().strip().lower()
        results = sorted(results, key=lambda g: 0 if g.get("game_name", "").lower() == query else 1)

        for game in results:
            # Parse the exact keys provided by HubcapManifest API
            raw_id = game.get("game_id", "0")
            app_id = int(raw_id) if str(raw_id).isdigit() else 0
            title = game.get("game_name", "Unknown Game")

            # Müzikleri (Soundtrack) ve eklentileri ana arama listesinden filtrele
            if "soundtrack" in title.lower() or "artbook" in title.lower():
                continue

            image_url = game.get("header_image", "")

            card = GameCard(app_id, title, image_url)
            self.results_layout.addWidget(card)
