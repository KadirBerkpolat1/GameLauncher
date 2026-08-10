import os
import re
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
    Prefers the user-configured path from settings, then falls back to the
    Flatpak path if a Flatpak Steam installation is detected, otherwise the
    native install path.
    """
    from src.config.settings import SettingsManager
    configured = SettingsManager.get("slssteam_config_path", "")
    if configured:
        return Path(configured)

    home = Path.home()
    flatpak_steam = home / ".var" / "app" / "com.valvesoftware.Steam" / ".steam" / "steam"
    if flatpak_steam.exists() and flatpak_steam.is_dir():
        return home / ".var" / "app" / "com.valvesoftware.Steam" / ".config" / "SLSsteam" / "config.yaml"

    return home / ".config" / "SLSsteam" / "config.yaml"


def get_steam_libraries() -> list:
    """
    Returns a list of Steam library root paths (the directory that contains
    the steamapps/ folder). Includes the main install path and any additional
    libraries from libraryfolders.vdf.
    """
    steam_path = get_steam_path()
    if not steam_path:
        return []

    all_libraries = {str(steam_path.resolve())}
    vdf_path = steam_path / "steamapps" / "libraryfolders.vdf"

    if vdf_path.exists():
        try:
            content = vdf_path.read_text(encoding="utf-8")
            matches = re.findall(r'^\s*"path"\s*"(.*?)"', content, re.MULTILINE)
            for path in matches:
                normalized = path.replace("\\\\", "\\")
                lib_path = Path(normalized)
                if (lib_path / "steamapps").is_dir():
                    all_libraries.add(str(lib_path.resolve()))
        except OSError:
            pass

    return list(all_libraries)
