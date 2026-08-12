import re
from src.config.settings import SettingsManager
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                               QScrollArea, QLabel, QPushButton, QCheckBox, 
                               QComboBox, QSpinBox, QFrame)
from PySide6.QtCore import Qt, QTimer, Signal
from src.api.hubcap import hubcap_api
from src.ui.game_card import GameCard
from src.ui.flow_layout import FlowLayout
from src.utils.async_utils import get_async_loop


def _has_image(game: dict) -> bool:
    return bool(game.get("header_image") or game.get("image_url"))


def _rank_search_results(query: str, games: list) -> list:
    q = query.strip().lower()
    if not q:
        return games

    def tier(game: dict) -> tuple:
        name = (game.get("game_name") or "").lower()
        if name == q:
            return (0, 0)
        if name.startswith(q):
            return (1, 0)
        m = re.search(rf"(?<![a-z0-9]){re.escape(q)}(?![a-z0-9])", name)
        if m:
            return (2, m.start())
        if q in name:
            return (3, 0)
        return (4, 0)

    return sorted(
        games,
        key=lambda g: (
            tier(g),
            0 if _has_image(g) else 1,
            (g.get("game_name") or "").lower(),
        ),
    )


class SearchWidget(QWidget):
    """
    Redesigned Hubcap Store & Search view featuring debounced searching,
    relevance ranking, rich pagination, and modern card grid.
    """
    download_requested = Signal(int, str)

    def __init__(self) -> None:
        super().__init__()
        self.current_page = 1
        self.total_pages = 1
        self.limit = 50
        self.list_mode = False
        self.select_mode = False
        self.current_results: list = []
        self._list_checkboxes = {}

        self.init_ui()
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)

        if SettingsManager.get("hubcap_api_key", ""):
            QTimer.singleShot(100, self._load_library)

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        # =====================================================================
        # HEADER & SEARCH BAR
        # =====================================================================
        header_box = QVBoxLayout()
        header_box.setSpacing(3)

        title = QLabel("Hubcap Game Store")
        title.setProperty("cssClass", "HeaderTitle")
        sub = QLabel("Browse thousands of manifests, search by AppID, or discover new games")
        sub.setProperty("cssClass", "SubHeader")
        header_box.addWidget(title)
        header_box.addWidget(sub)
        layout.addLayout(header_box)

        # Search Bar Row
        search_bar = QHBoxLayout()
        search_bar.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search by game title or keyword...")
        self.search_input.setMinimumHeight(42)
        self.search_input.textChanged.connect(self._on_text_changed)

        self.cb_appid = QCheckBox("AppID Search")
        self.cb_appid.setStyleSheet("font-weight: 600;")
        self.cb_appid.toggled.connect(lambda: self._perform_search() if self.search_input.text().strip() else None)

        self.btn_search = QPushButton("Search")
        self.btn_search.setProperty("cssClass", "PrimaryAction")
        self.btn_search.setMinimumHeight(42)
        self.btn_search.clicked.connect(self._perform_search)

        search_bar.addWidget(self.search_input, 1)
        search_bar.addWidget(self.cb_appid)
        search_bar.addWidget(self.btn_search)
        layout.addLayout(search_bar)

        # =====================================================================
        # FILTERS & CONTROLS TOOLBAR
        # =====================================================================
        filters_bar = QHBoxLayout()
        filters_bar.setSpacing(12)

        self.combo_sort = QComboBox()
        self.combo_sort.addItems(["Sort: Newest First", "Sort: Name (A-Z)"])
        self.combo_sort.currentIndexChanged.connect(self._load_library)

        filters_bar.addWidget(self.combo_sort)
        filters_bar.addStretch()

        self.btn_load = QPushButton("🔄  Reload Store")
        self.btn_load.setProperty("cssClass", "SecondaryAction")
        self.btn_load.clicked.connect(self._load_library)

        filters_bar.addWidget(self.btn_load)
        layout.addLayout(filters_bar)

        # =====================================================================
        # RESULTS GRID AREA
        # =====================================================================
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("StoreScroll")

        self.results_container = QWidget()
        self.results_layout = FlowLayout(self.results_container, spacing=20)

        # Status Banner
        self.status_card = QFrame()
        self.status_card.setObjectName("SurfaceCard")
        status_layout = QVBoxLayout(self.status_card)
        status_layout.setContentsMargins(30, 30, 30, 30)

        self.status_label = QLabel("Type at least 3 characters to search, or browse the store catalog.")
        self.status_label.setStyleSheet("color: #94A3B8; font-size: 14px; font-weight: 600;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.status_label)

        self.results_layout.addWidget(self.status_card)

        self.scroll_area.setWidget(self.results_container)
        layout.addWidget(self.scroll_area)

        # =====================================================================
        # PAGINATION BAR
        # =====================================================================
        pagination_bar = QHBoxLayout()
        pagination_bar.setSpacing(10)

        self.btn_prev = QPushButton("◀  Prev")
        self.btn_prev.setProperty("cssClass", "SecondaryAction")
        self.btn_prev.clicked.connect(self._prev_page)

        self.lbl_page = QLabel("Page 1 of 1")
        self.lbl_page.setStyleSheet("color: #818CF8; font-weight: 700; padding: 0 10px;")

        self.btn_next = QPushButton("Next  ▶")
        self.btn_next.setProperty("cssClass", "SecondaryAction")
        self.btn_next.clicked.connect(self._next_page)

        self.goto_input = QSpinBox()
        self.goto_input.setMinimum(1)
        self.goto_input.setMaximum(9999)
        self.goto_input.setFixedWidth(80)

        self.btn_go = QPushButton("Go")
        self.btn_go.setProperty("cssClass", "SecondaryAction")
        self.btn_go.clicked.connect(self._goto_page)

        pagination_bar.addStretch()
        pagination_bar.addWidget(self.btn_prev)
        pagination_bar.addWidget(self.lbl_page)
        pagination_bar.addWidget(self.btn_next)
        pagination_bar.addSpacing(15)
        pagination_bar.addWidget(QLabel("Jump to:"))
        pagination_bar.addWidget(self.goto_input)
        pagination_bar.addWidget(self.btn_go)
        pagination_bar.addStretch()

        layout.addLayout(pagination_bar)

    def _on_text_changed(self, text: str) -> None:
        if len(text) >= 3:
            self.status_label.setText("⏳  Searching Hubcap API...")
            self.status_card.show()
            self.search_timer.start(500)
        else:
            self.search_timer.stop()
            self._clear_results()
            self._load_library()

    def _clear_results(self) -> None:
        for i in reversed(range(self.results_layout.count())):
            item = self.results_layout.itemAt(i)
            if item.widget() and item.widget() != self.status_card:
                item.widget().deleteLater()

    def _perform_search(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            return

        is_appid = self.cb_appid.isChecked()
        loop = get_async_loop()
        loop.create_task(self._fetch_search(query, is_appid))

    async def _fetch_search(self, query: str, is_appid: bool) -> None:
        try:
            results = await hubcap_api.search_game(query, limit=100, appid=is_appid)
            data = results.get("results", []) if isinstance(results, dict) else results
            self._display_results(data)
        except Exception as e:
            self._clear_results()
            self.status_label.setText(f"❌  Error: {e}")
            self.status_card.show()

    def _load_library(self) -> None:
        loop = get_async_loop()
        loop.create_task(self._fetch_library())

    async def _fetch_library(self) -> None:
        if not SettingsManager.get("hubcap_api_key", ""):
            self.status_label.setText("⚠️  No API key set. Go to Settings to configure your Hubcap API key.")
            self.status_card.show()
            return
        try:
            offset = (self.current_page - 1) * self.limit
            sort_by = "name" if "Name" in self.combo_sort.currentText() else "updated"
            search_term = self.search_input.text().strip()

            results = await hubcap_api.get_library(limit=self.limit, offset=offset, search=search_term, sort_by=sort_by)

            if isinstance(results, dict):
                data = results.get("games", [])
                total = results.get("total_count", len(data))
                self.total_pages = max(1, (total + self.limit - 1) // self.limit)
            else:
                data = results if isinstance(results, list) else []
                self.total_pages = max(1, self.current_page + (1 if len(data) == self.limit else 0))

            self.lbl_page.setText(f"Page {self.current_page} of {self.total_pages}")
            self.goto_input.setMaximum(self.total_pages)
            self._display_results(data)
        except Exception as e:
            self._clear_results()
            self.status_label.setText(f"❌  Error: {e}")
            self.status_card.show()

    def _prev_page(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self._load_library()

    def _next_page(self) -> None:
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._load_library()

    def _goto_page(self) -> None:
        target = self.goto_input.value()
        if 1 <= target <= self.total_pages:
            self.current_page = target
            self._load_library()

    def _display_results(self, results: list) -> None:
        self._clear_results()

        if not results:
            self.status_label.setText("No games found matching your search.")
            self.status_card.show()
            return

        self.status_card.hide()

        query = self.search_input.text().strip()
        ranked = _rank_search_results(query, results)

        for game in ranked:
            app_id = game.get("game_id", 0)
            title = game.get("game_name", "Unknown Game")
            image_url = game.get("header_image", "")

            card = GameCard(app_id, title, image_url, mode="store")
            card.download_requested.connect(self.download_requested.emit)
            self.results_layout.addWidget(card)
