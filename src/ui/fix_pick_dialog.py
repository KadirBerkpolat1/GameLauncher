from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
                                 QPushButton, QHBoxLayout)
from PySide6.QtCore import Qt

class FixPickDialog(QDialog):
    def __init__(self, fixes: list, parent=None):
        super().__init__(parent)
        self.fixes = fixes
        self.setWindowTitle("Select Patch Source")
        self.resize(520, 260)
        self.setStyleSheet("""
            QDialog {
                background-color: #161B22;
                color: #C9D1D9;
            }
            QLabel {
                font-size: 14px;
                font-weight: bold;
            }
            QListWidget {
                background-color: #0D1117;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 5px;
                font-size: 13px;
                color: #C9D1D9;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #21262D;
            }
            QListWidget::item:selected {
                background-color: #1F6FEB;
                color: #ffffff;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2EA043;
            }
            QPushButton:disabled {
                background-color: #484F58;
                color: #8B949E;
            }
        """)

        layout = QVBoxLayout(self)

        lbl = QLabel("Select Patch Version to Install:")
        lbl.setStyleSheet("color: #FFFFFF; font-weight: 700; font-size: 14px;")
        layout.addWidget(lbl)

        self.list_widget = QListWidget()
        for i, fix in enumerate(self.fixes):
            if fix["source"] == "freetp":
                source = "FreeTP"
            elif fix["source"] == "onlinefix":
                source = "Online-Fix"
            else:
                source = "Goldberg"
            ver = fix.get("version", "Unknown")
            if ver == "0.0.0":
                ver = "Unknown"
            title = fix.get("title", "")
            
            # Mark the highest version as Recommended
            rec_text = " (Recommended)" if i == 0 else ""
            
            item_text = f"[{source}] Version: {ver}{rec_text}\n{title}"
            item = QListWidgetItem(item_text)
            # Seçimi tutmak için index kaydedelim
            item.setData(Qt.ItemDataRole.UserRole, fix)
            self.list_widget.addItem(item)
            
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_select = QPushButton("Install Selected")
        self.btn_select.setEnabled(False)
        self.btn_select.clicked.connect(self.accept)
        
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background-color: #21262D; color: #C9D1D9; border: 1px solid #30363D;")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_select)

        layout.addLayout(btn_layout)
        
        if self.fixes:
            self.list_widget.setCurrentRow(0)

    def _on_selection_changed(self):
        self.btn_select.setEnabled(bool(self.list_widget.selectedItems()))

    def get_selected_fix(self) -> dict:
        items = self.list_widget.selectedItems()
        if items:
            return items[0].data(Qt.ItemDataRole.UserRole)
        return None
