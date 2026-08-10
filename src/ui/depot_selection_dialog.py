from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QLabel, QPushButton, QCheckBox,
                               QGroupBox, QScrollArea, QWidget)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtGui import QPixmap, QImage

CHECKBOX_STYLE = """
    QCheckBox {
        font-size: 14px;
        color: #E6EDF3;
        spacing: 10px;
    }
    QCheckBox::indicator {
        width: 22px;
        height: 22px;
        border-radius: 5px;
        border: 2px solid #444C56;
        background-color: #161B22;
    }
    QCheckBox::indicator:unchecked:hover {
        border: 2px solid #8B949E;
        background-color: #21262D;
    }
    QCheckBox::indicator:checked {
        background-color: #1F6FEB;
        border: 2px solid #388BFD;
    }
    QCheckBox::indicator:checked:disabled {
        background-color: #1A5CBA;
        border: 2px solid #2D6FBF;
    }
    QCheckBox::indicator:unchecked:disabled {
        background-color: #21262D;
        border: 2px solid #30363D;
    }
"""


class DepotSelectionDialog(QDialog):
    def __init__(self, app_name: str, metadata: dict, parent=None):
        super().__init__(parent)
        self.metadata = metadata
        self.app_name = app_name
        self.checkboxes = {}
        self.image_labels = {}

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Select Content - {self.app_name}")
        self.setMinimumWidth(560)
        self.setMinimumHeight(520)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QLabel(f"<b style='font-size:16px;'>{self.app_name}</b>"
                        f"<p style='color:#8B949E;margin:4px 0 0 0;'>İndirmek istediğiniz içerikleri seçin:</p>")
        layout.addWidget(header)

        # --- Base Game ---
        base_group = QGroupBox("Temel Oyun")
        base_group.setStyleSheet("QGroupBox { font-weight: bold; color: #E6EDF3; border: 1px solid #30363D; border-radius: 6px; margin-top: 8px; padding: 8px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; }")
        base_layout = QVBoxLayout(base_group)

        base_label_text = f"{self.metadata['base']['name']} (Zorunlu)"
        size_str = self._format_size(self.metadata["base"]["size"])
        if size_str:
            base_label_text += f"  —  {size_str}"

        self.base_checkbox = QCheckBox(base_label_text)
        self.base_checkbox.setStyleSheet(CHECKBOX_STYLE)
        self.base_checkbox.setChecked(True)
        self.base_checkbox.setEnabled(False)
        base_layout.addWidget(self.base_checkbox)
        layout.addWidget(base_group)

        # --- DLCs ---
        if self.metadata["dlcs"]:
            dlc_group = QGroupBox(f"İndirilebilir İçerikler (DLC)  —  {len(self.metadata['dlcs'])} adet")
            dlc_group.setStyleSheet("QGroupBox { font-weight: bold; color: #E6EDF3; border: 1px solid #30363D; border-radius: 6px; margin-top: 8px; padding: 8px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; }")
            dlc_layout = QVBoxLayout(dlc_group)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            scroll_widget = QWidget()
            scroll_widget.setStyleSheet("background: transparent;")
            scroll_layout = QVBoxLayout(scroll_widget)
            scroll_layout.setSpacing(6)

            self.network_manager = QNetworkAccessManager(self)
            self.network_manager.finished.connect(self._on_image_loaded)

            for dlc_id, dlc_info in self.metadata["dlcs"].items():
                row_widget = QWidget()
                row_widget.setStyleSheet("""
                    QWidget { background-color: #21262D; border-radius: 8px; }
                    QWidget:hover { background-color: #2D333B; }
                """)
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(8, 8, 8, 8)
                row_layout.setSpacing(12)

                # Cover image
                img_label = QLabel()
                img_label.setFixedSize(107, 50)
                img_label.setStyleSheet("background-color: #161B22; border-radius: 4px; color: #8B949E; font-size: 10px;")
                img_label.setAlignment(Qt.AlignCenter)
                img_label.setText("...")

                image_url = dlc_info.get("image")
                if image_url:
                    req = QNetworkRequest(QUrl(image_url))
                    reply = self.network_manager.get(req)
                    self.image_labels[reply] = img_label

                # Checkbox with name + size
                cb_text = dlc_info["name"]
                size_str = self._format_size(dlc_info["size"])
                if size_str:
                    cb_text += f"\n{size_str}"

                cb = QCheckBox(cb_text)
                cb.setStyleSheet(CHECKBOX_STYLE)
                cb.setChecked(False)
                self.checkboxes[dlc_id] = cb

                row_layout.addWidget(img_label)
                row_layout.addWidget(cb, 1)

                scroll_layout.addWidget(row_widget)

            scroll_layout.addStretch()
            scroll.setWidget(scroll_widget)
            dlc_layout.addWidget(scroll)
            layout.addWidget(dlc_group)
        else:
            no_dlc = QLabel("Bu oyun için DLC bulunamadı.")
            no_dlc.setStyleSheet("color: #8B949E; padding: 8px;")
            layout.addWidget(no_dlc)

        # --- Extra Options ---
        extra_group = QGroupBox("Ek Seçenekler")
        extra_group.setStyleSheet("QGroupBox { font-weight: bold; color: #E6EDF3; border: 1px solid #30363D; border-radius: 6px; margin-top: 8px; padding: 8px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; }")
        extra_layout = QVBoxLayout(extra_group)
        self.onlinefix_checkbox = QCheckBox("OnlineFix Yamasını Uygula (Sadece Multiplayer Oyunlar İçin Seçin)")
        self.onlinefix_checkbox.setStyleSheet(CHECKBOX_STYLE)
        self.onlinefix_checkbox.setChecked(False)
        extra_layout.addWidget(self.onlinefix_checkbox)
        layout.addWidget(extra_group)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("İptal")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("padding: 8px 16px; border-radius: 6px;")

        confirm_btn = QPushButton("İndir")
        confirm_btn.clicked.connect(self.accept)
        confirm_btn.setStyleSheet(
            "background-color: #1F6FEB; color: white; font-weight: bold;"
            "padding: 8px 20px; border-radius: 6px; border: none;"
        )

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

    def _on_image_loaded(self, reply):
        label = self.image_labels.get(reply)
        if label and reply.error() == reply.NetworkError.NoError:
            img_data = reply.readAll()
            img = QImage()
            img.loadFromData(img_data)
            pixmap = QPixmap(img).scaled(
                107, 50,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            label.setPixmap(pixmap)
            label.setText("")
        elif label:
            label.setText("Yok")
        reply.deleteLater()

    def _format_size(self, size_bytes: int) -> str:
        if not size_bytes:
            return ""
        gb = size_bytes / (1024 ** 3)
        if gb >= 1:
            return f"{gb:.2f} GB"
        mb = size_bytes / (1024 ** 2)
        return f"{mb:.1f} MB"

    def get_selected_depots(self) -> list:
        selected = list(self.metadata["base"]["depots"])
        for dlc_id, cb in self.checkboxes.items():
            if cb.isChecked():
                selected.extend(self.metadata["dlcs"][dlc_id]["depots"])
        return selected


    def wants_onlinefix(self) -> bool:
        return self.onlinefix_checkbox.isChecked()