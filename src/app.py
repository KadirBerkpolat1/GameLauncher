import asyncio
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from src.ui.main_window import MainWindow
from src.ui.styles import DARK_THEME

def run_app(loop: asyncio.AbstractEventLoop) -> int:
    """
    Initializes the QApplication, applies the stylesheet, and manages the async loop.
    """
    app = QApplication(sys.argv)
    app.setApplicationName("Nebula Launcher")
    app.setStyleSheet(DARK_THEME)

    window = MainWindow()
    window.show()

    # Integration between asyncio and Qt event loops
    # A timer runs the asyncio loop periodically
    def process_events() -> None:
        loop.call_soon(loop.stop)
        loop.run_forever()

    timer = QTimer()
    timer.timeout.connect(process_events)
    timer.start(10) # 10ms interval

    exit_code = app.exec()

    # Cleanup async loop on exit
    timer.stop()
    loop.close()

    return exit_code
