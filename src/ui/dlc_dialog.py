from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QScrollArea, 
                                 QWidget, QLabel, QCheckBox, QPushButton, QFrame)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

class DLCDialog(QDialog):
    """
    Oyunun sahip olduğu DLC'leri listeleyen, görsel ve isimleriyle gösteren
    modern karanlık temalı seçim penceresi.
    """
    def __init__(self, parent, dlc_list: list[dict]):
        super().__init__(parent)
        self.setWindowTitle("DLC Seçimi")
        self.resize(550, 700)
        self.setStyleSheet("background-color: #0D1117; color: #C9D1D9; font-family: 'Inter', sans-serif; font-size: 14px;")
        
        self.dlc_list = dlc_list
        self.checkboxes = {} # app_id -> QCheckBox
        self.image_labels = {} # url -> QLabel
        
        # Asenkron resim yükleyici
        self.network_manager = QNetworkAccessManager(self)
        self.network_manager.finished.connect(self._on_image_loaded)
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Üst Başlık
        header_lbl = QLabel("Kurmak İstediğiniz DLC'leri Seçin")
        header_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF; margin-bottom: 10px;")
        layout.addWidget(header_lbl)
        
        # Kaydırılabilir Alan (Scroll Area)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { background: transparent; width: 12px; margin: 0; }
            QScrollBar::handle:vertical { background: #30363D; border-radius: 6px; min-height: 40px; margin: 3px; }
            QScrollBar::handle:vertical:hover { background: #484F58; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        
        container = QWidget()
        container.setStyleSheet("background-color: #0D1117;")
        scroll_layout = QVBoxLayout(container)
        scroll_layout.setSpacing(12)
        
        # Her bir DLC için kart oluştur
        for dlc in self.dlc_list:
            card = QFrame()
            card.setStyleSheet("QFrame { background-color: #161B22; border-radius: 8px; border: 1px solid #30363D; }")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(15, 10, 15, 10)
            card_layout.setSpacing(15)
            
            # Checkbox
            cb = QCheckBox()
            # Varsayılan olarak tümünü seçili yapabiliriz, veya boş bırakabiliriz
            cb.setChecked(True) 
            cb.setStyleSheet("""
                QCheckBox::indicator { width: 22px; height: 22px; border-radius: 4px; border: 1px solid #58A6FF; background: #0D1117; }
                QCheckBox::indicator:checked { background-color: #1F6FEB; image: url(check.png); }
            """)
            self.checkboxes[dlc["app_id"]] = cb
            
            # Kapak Resmi (Asenkron yüklenecek)
            img_lbl = QLabel()
            img_lbl.setFixedSize(140, 65)
            img_lbl.setStyleSheet("background-color: #21262D; border-radius: 4px; border: none;")
            img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.image_labels[dlc["image_url"]] = img_lbl
            
            # Resim İsteğini Başlat
            req = QNetworkRequest(dlc["image_url"])
            self.network_manager.get(req)
            
            # İsim
            name_lbl = QLabel(dlc["name"])
            name_lbl.setWordWrap(True)
            name_lbl.setStyleSheet("font-weight: 600; border: none; background: transparent; font-size: 15px;")
            
            card_layout.addWidget(cb)
            card_layout.addWidget(img_lbl)
            card_layout.addWidget(name_lbl)
            card_layout.addStretch()
            
            scroll_layout.addWidget(card)
            
        scroll_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        # Alt Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("İptal")
        cancel_btn.setStyleSheet("background-color: #21262D; color: #C9D1D9; border: 1px solid #30363D; border-radius: 6px; padding: 10px 20px; font-weight: 600;")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Seçilenleri Kaydet")
        save_btn.setStyleSheet("background-color: #238636; color: #FFFFFF; border: none; border-radius: 6px; padding: 10px 20px; font-weight: 600;")
        save_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
    def _on_image_loaded(self, reply):
        """Asenkron resim indirmesi tamamlandığında UI'ı günceller."""
        url = reply.url().toString()
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            img = QImage()
            img.loadFromData(data)
            if url in self.image_labels:
                pixmap = QPixmap.fromImage(img).scaled(140, 65, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                self.image_labels[url].setPixmap(pixmap)
        reply.deleteLater()
        
    def get_selected_dlcs(self) -> list[dict]:
        """Kullanıcının tiklediği DLC'lerin listesini döndürür."""
        selected = []
        for dlc in self.dlc_list:
            if self.checkboxes[dlc["app_id"]].isChecked():
                selected.append(dlc)
        return selected
