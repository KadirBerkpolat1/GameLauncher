from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QScrollArea, QFrame, QPushButton
from PySide6.QtCore import Qt

class LeaderboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # Header
        header = QLabel("Leaderboard")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFFFFF;")
        main_layout.addWidget(header)

        # Stats Summary
        stats_lbl = QLabel("Your stats: Rank #4450, 65 Generations, 38 Unique games")
        stats_lbl.setStyleSheet("font-size: 16px; color: #58A6FF; font-weight: bold; background-color: #1B2027; padding: 15px; border-radius: 8px;")
        main_layout.addWidget(stats_lbl)
        
        main_layout.addSpacing(10)
        
        # Subheader
        sub_header = QLabel("Top Generated Games")
        sub_header.setStyleSheet("font-size: 18px; font-weight: bold; color: #DDDDDD;")
        main_layout.addWidget(sub_header)

        # Scroll Area for List
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setSpacing(10)

        # Mock Data List
        mock_games = [
            ("Cyberpunk 2077", "98,421 Generations"),
            ("Elden Ring", "85,120 Generations"),
            ("Baldur's Gate 3", "79,300 Generations"),
            ("Red Dead Redemption 2", "64,215 Generations"),
            ("Hogwarts Legacy", "51,102 Generations")
        ]
        
        for rank, (name, gens) in enumerate(mock_games, start=1):
            row = QFrame()
            row.setStyleSheet("background-color: #242933; border-radius: 8px;")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(15, 10, 15, 10)
            
            lbl_rank = QLabel(f"#{rank}")
            lbl_rank.setStyleSheet("font-size: 18px; font-weight: bold; color: #888888; width: 40px;")
            
            lbl_name = QLabel(name)
            lbl_name.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF;")
            
            lbl_gens = QLabel(gens)
            lbl_gens.setStyleSheet("font-size: 14px; color: #AAAAAA;")
            
            btn_dl = QPushButton("Download")
            btn_dl.setProperty("cssClass", "PrimaryAction")
            btn_dl.setFixedWidth(100)
            
            row_layout.addWidget(lbl_rank)
            row_layout.addWidget(lbl_name)
            row_layout.addStretch()
            row_layout.addWidget(lbl_gens)
            row_layout.addSpacing(20)
            row_layout.addWidget(btn_dl)
            
            list_layout.addWidget(row)
            
        list_layout.addStretch()
        scroll.setWidget(list_container)
        
        main_layout.addWidget(scroll)
