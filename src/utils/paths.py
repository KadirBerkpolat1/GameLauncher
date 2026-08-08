import os
from pathlib import Path
from typing import Optional

def get_steam_path() -> Optional[Path]:
    """
    Attempts to auto-detect the Steam installation path on Linux.
    Checks common directories in order of likelihood.
    """
    home = Path.home()

    possible_paths = [
        home / ".local" / "share" / "Steam",
        home / ".steam" / "steam",
        home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
        Path("/usr/share/steam")
    ]

    for path in possible_paths:
        if path.exists() and path.is_dir():
            return path

    return None

def get_slssteam_config_path() -> Path:
    """
    Returns the path to the SLSsteam config.yaml file.
    """
    return Path.home() / ".config" / "SLSsteam" / "config.yaml"
