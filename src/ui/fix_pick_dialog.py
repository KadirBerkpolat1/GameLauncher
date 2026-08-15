from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
                                 QPushButton, QHBoxLayout, QTabWidget, QWidget, QScrollArea)
from PySide6.QtCore import Qt, QSize

class FixPickDialog(QDialog):
    def __init__(self, fixes: list, parent=None):
        super().__init__(parent)
        self.fixes = fixes
        self.setWindowTitle("Select Patch Source")
        self.resize(600, 400)
        self.setStyleSheet("""
            QDialog { background-color: #0D1117; color: #E6EDF3; }
            QTabWidget::pane { border: 1px solid #30363D; background: #161B22; border-radius: 6px; }
            QTabBar::tab { background: #0D1117; color: #8B949E; padding: 8px 16px; border: 1px solid #30363D; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; }
            QTabBar::tab:selected { background: #161B22; color: #58A6FF; }
            QTabBar::tab:hover { color: #E6EDF3; }
            QListWidget { background-color: #161B22; border: 1px solid #30363D; border-radius: 6px; color: #E6EDF3; }
            QListWidget::item { padding: 12px; border-bottom: 1px solid #21262D; }
            QListWidget::item:selected { background-color: #21262D; color: #FFFFFF; border-left: 3px solid #58A6FF; }
            QListWidget::item:hover { background-color: #21262D; }
            QPushButton { background-color: #238636; color: #FFFFFF; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; }
            QPushButton:hover { background-color: #2EA043; }
            QPushButton:disabled { background-color: #30363D; color: #8B949E; }
            QPushButton[cssClass="SecondaryAction"] { background-color: #21262D; border: 1px solid #30363D; }
            QPushButton[cssClass="SecondaryAction"]:hover { background-color: #30363D; }
            QLabel { color: #E6EDF3; }
        """)

        layout = QVBoxLayout(self)

        lbl = QLabel("Select Patch Version to Install:")
        lbl.setStyleSheet("color: #FFFFFF; font-weight: 700; font-size: 14px;")
        layout.addWidget(lbl)

        # Group fixes by source
        self.fixes_by_source = {}
        for fix in fixes:
            source = fix.get("source", "unknown")
            if source not in self.fixes_by_source:
                self.fixes_by_source[source] = []
            self.fixes_by_source[source].append(fix)

        # Provider display names and icons (external providers)
        self.provider_info = {
            "ryuu": {"name": "Ryuu", "icon": "🌙", "color": "#A371F7"},
            "crackbypass": {"name": "CrackBypass", "icon": "🔓", "color": "#F85149"},
            "onlinefix": {"name": "OnlineFix", "icon": "🌐", "color": "#3FB950"},
            "freetp": {"name": "FreeTP", "icon": "🆓", "color": "#D29922"},
        }
        
        # Fallback info (local, not a provider)
        self.fallback_info = {
            "goldberg": {"name": "Goldberg Steam Emulator", "icon": "🎮", "color": "#58A6FF", "description": "Offline DRM removal (local fallback)"},
        }

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        
        self.all_list_widgets = []
        
        # Add provider tabs (external sources)
        for source, source_fixes in self.fixes_by_source.items():
            if source == "goldberg":
                continue  # Handle Goldberg separately as fallback
            info = self.provider_info.get(source, {"name": source.capitalize(), "icon": "📦", "color": "#8B949E"})
            tab_name = f"{info['icon']}  {info['name']} ({len(source_fixes)})"
            
            tab_widget = QWidget()
            tab_layout = QVBoxLayout(tab_widget)
            tab_layout.setContentsMargins(8, 8, 8, 8)
            
            # Add info label
            if source_fixes:
                best = source_fixes[0]
                version = best.get("version", "1.0.0")
                badges = best.get("badges", [])
                badge_text = " ".join([f"[{b}]" for b in badges])
                if badge_text:
                    info_label = QLabel(f"Best: {version} {badge_text}")
                else:
                    info_label = QLabel(f"Best: {version}")
                info_label.setStyleSheet(f"color: {info['color']}; font-size: 11px; font-weight: 600;")
                tab_layout.addWidget(info_label)
            
            list_widget = QListWidget()
            list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
            for fix in source_fixes:
                item = self._create_fix_item(fix, source, info)
                list_widget.addItem(item)
            self.all_list_widgets.append((list_widget, source))
            tab_layout.addWidget(list_widget)
            
            self.tab_widget.addTab(tab_widget, tab_name)
        
        # Add Goldberg fallback as a special section at the end
        goldberg_fixes = self.fixes_by_source.get("goldberg", [])
        if goldberg_fixes:
            fallback_info = self.fallback_info["goldberg"]
            tab_name = f"{fallback_info['icon']}  {fallback_info['name']} (Fallback)"
            
            tab_widget = QWidget()
            tab_layout = QVBoxLayout(tab_widget)
            tab_layout.setContentsMargins(8, 8, 8, 8)
            
            # Description
            desc_label = QLabel(fallback_info["description"])
            desc_label.setStyleSheet(f"color: {fallback_info['color']}; font-size: 11px; font-weight: 600;")
            desc_label.setWordWrap(True)
            tab_layout.addWidget(desc_label)
            
            list_widget = QListWidget()
            list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
            for fix in goldberg_fixes:
                item = self._create_fix_item(fix, "goldberg", fallback_info)
                list_widget.addItem(item)
            self.all_list_widgets.append((list_widget, "goldberg"))
            tab_layout.addWidget(list_widget)
            
            self.tab_widget.addTab(tab_widget, tab_name)
        
        layout.addWidget(self.tab_widget)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_select = QPushButton("Install Selected")
        self.btn_select.setEnabled(False)
        self.btn_select.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("cssClass", "SecondaryAction")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_select)

        layout.addLayout(btn_layout)
        
        # Connect selection changed for all list widgets
        for list_widget, _ in self.all_list_widgets:
            list_widget.itemSelectionChanged.connect(self._on_selection_changed)

    def _create_fix_item(self, fix: dict, source: str, info: dict) -> QListWidgetItem:
        """Create a plain-text list item with fix details and badges."""
        title = fix.get("title", "Unknown Fix")
        version = fix.get("version", "1.0.0")
        badges = fix.get("badges", [])

        badge_str = " ".join([f"[{b}]" for b in badges]) if badges else ""
        text = f"{title}  {version}  {badge_str}".strip()

        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, fix)
        item.setSizeHint(QSize(0, 50))
        return item

    def _on_selection_changed(self):
        """Enable install button if any item is selected in any tab."""
        has_selection = False
        for list_widget, _ in self.all_list_widgets:
            if list_widget.selectedItems():
                has_selection = True
                break
        self.btn_select.setEnabled(has_selection)

    def get_selected_fix(self) -> dict:
        """Get the selected fix from any tab."""
        for list_widget, source in self.all_list_widgets:
            items = list_widget.selectedItems()
            if items:
                return items[0].data(Qt.ItemDataRole.UserRole)
        return None
