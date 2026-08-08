import sys
import os
import asyncio

# Ensure the project root is in the Python path when running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.app import run_app

def main() -> None:
    """
    Main entry point for GameLauncher.
    Sets up the asyncio event loop for PySide6 integration and runs the application.
    """
    # Create the asyncio event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Run the Qt application
    sys.exit(run_app(loop))

if __name__ == "__main__":
    main()
