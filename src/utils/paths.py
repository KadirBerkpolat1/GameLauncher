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
        # Ubuntu snap Steam (classic confinement keeps data under ~/snap/steam)
        home / "snap" / "steam" / "common" / ".steam" / "steam",
        home / "snap" / "steam" / "common" / ".local" / "share" / "Steam",
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

# Steam system tools that are installed like games but must not appear in the
# launcher library: runtimes, Proton, redistributables, Spacewar.
STEAM_TOOL_APPIDS = {
    480,     # Spacewar
    228980,  # Steamworks Common Redistributables
    1070560, # Steam Linux Runtime 1.0 (scout)
    1391110, # Steam Linux Runtime 2.0 (soldier)
    1628350, # Steam Linux Runtime 3.0 (sniper)
    4183110, # Steam Linux Runtime 4.0
    3658110, # Proton 10.0
}
STEAM_TOOL_NAME_PREFIXES = ("steam linux runtime", "proton ")


def get_installed_apps() -> dict:
    """
    Returns {app_id: name} for games currently installed in any Steam library
    by reading steamapps/appmanifest_*.acf files. System tools (runtimes,
    Proton, redistributables, Spacewar) are filtered out.

    This reflects the real on-disk state and is independent of the SLSsteam
    config, so games stay visible even after re-cloning or updating the app.
    """
    apps: dict = {}
    for lib in get_steam_libraries():
        steamapps = Path(lib) / "steamapps"
        if not steamapps.is_dir():
            continue
        for acf in steamapps.glob("appmanifest_*.acf"):
            try:
                content = acf.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            m_id = re.search(r'"appid"\s+"(\d+)"', content, re.IGNORECASE)
            if not m_id:
                continue
            app_id = int(m_id.group(1))
            if app_id in STEAM_TOOL_APPIDS:
                continue
            m_name = re.search(r'"name"\s+"(.+?)"', content, re.IGNORECASE)
            name = m_name.group(1) if m_name else ""
            if name.strip().lower().startswith(STEAM_TOOL_NAME_PREFIXES):
                continue
            apps[app_id] = name
    return apps
