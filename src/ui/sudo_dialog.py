"""Dark-themed sudo password dialog matching the Nebula theme.

Used as SUDO_ASKPASS helper so privileged operations (slsteam-moon launcher
interception) can ask for the sudo password from a polished GUI prompt
instead of a terminal.
"""
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QVBoxLayout)

from src.ui.styles import DARK_THEME


class SudoPasswordDialog(QDialog):
    """A refined dark password prompt with indigo accent, matching the app."""

    def __init__(self, prompt: str = "Administrator privileges are required",
                 detail: str = "Enter your sudo password to continue.",
                 parent=None):
        super().__init__(parent)
        self.password = ""
        self.setWindowTitle("Authentication Required")
        self.setFixedSize(440, 260)
        self.setModal(True)
        self.setStyleSheet(DARK_THEME)
        self._build_ui(prompt, detail)

    def _build_ui(self, prompt: str, detail: str) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 18)
        root.setSpacing(12)

        card = QFrame()
        card.setObjectName("SudoCard")
        card.setStyleSheet("""
            #SudoCard {
                background-color: #0F121C;
                border: 1px solid #1E2337;
                border-radius: 14px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 20)
        card_layout.setSpacing(12)

        # --- Header: shield icon + title ---
        header = QHBoxLayout()
        header.setSpacing(14)

        icon_frame = QFrame()
        icon_frame.setFixedSize(46, 46)
        icon_frame.setStyleSheet("""
            background-color: #1B1F33;
            border: 1px solid #2A3050;
            border-radius: 23px;
        """)
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("🔒")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 22px; background: transparent;")
        icon_layout.addWidget(icon_lbl)
        header.addWidget(icon_frame)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title_lbl = QLabel(prompt)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #F1F5F9;")
        detail_lbl = QLabel(detail)
        detail_lbl.setWordWrap(True)
        detail_lbl.setStyleSheet("font-size: 12px; color: #94A3B8;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(detail_lbl)
        header.addLayout(title_box, 1)

        card_layout.addLayout(header)

        # --- Password field ---
        pass_label = QLabel("Password")
        pass_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; letter-spacing: 0.6px;")
        card_layout.addWidget(pass_label)

        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_password.setPlaceholderText("••••••••")
        self.input_password.setMinimumHeight(38)
        self.input_password.setStyleSheet("""
            QLineEdit {
                background-color: #090A0F;
                border: 1px solid #262D47;
                border-radius: 8px;
                padding: 0 12px;
                color: #F1F5F9;
                font-size: 13px;
                selection-background-color: #6366F1;
            }
            QLineEdit:focus {
                border: 1px solid #6366F1;
                background-color: #0D0F18;
            }
        """)
        self.input_password.returnPressed.connect(self._accept)
        card_layout.addWidget(self.input_password)

        # --- Buttons ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #262D47;
                border-radius: 8px;
                padding: 0 18px;
                color: #94A3B8;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover { border-color: #3B4267; color: #E2E8F0; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_ok = QPushButton("Authenticate")
        btn_ok.setFixedHeight(36)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setDefault(True)
        btn_ok.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366F1, stop:1 #4F46E5);
                border: none;
                border-radius: 8px;
                padding: 0 20px;
                color: #FFFFFF;
                font-weight: 800;
                font-size: 12px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #6D70FF, stop:1 #5850F8); }
            QPushButton:pressed { background: #4338CA; }
        """)
        btn_ok.clicked.connect(self._accept)
        btn_row.addWidget(btn_ok)

        card_layout.addLayout(btn_row)
        root.addWidget(card)

        self.input_password.setFocus()

    def _accept(self) -> None:
        pw = self.input_password.text()
        if not pw:
            return
        self.password = pw
        self.accept()


def main() -> int:
    """Entry point used by the SUDO_ASKPASS helper. Prints the password to
    stdout (sudo reads it) or exits 1 when cancelled."""
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME)
    dlg = SudoPasswordDialog(
        prompt="Administrator authentication",
        detail="slsteam-moon needs root access to install the Steam launcher "
               "shim. Enter your sudo password.",
    )
    if dlg.exec() == QDialog.DialogCode.Accepted:
        print(dlg.password)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
