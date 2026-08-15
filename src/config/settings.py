import json
import os
from pathlib import Path
from typing import Any, Dict

SETTINGS_DIR = Path.home() / ".config" / "GameLauncher"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "hubcap_api_key": "",
    "ryuu_api_key": "",
    "manifest_provider": "auto",
    "steamgriddb_api_key": "",
    "steam_path": "",
    "preferred_steam_library": "",
    "slssteam_config_path": str(Path.home() / ".config" / "SLSsteam" / "config.yaml"),
    "download_method": "ddmod",
    "depotdownloadermod_path": "",
    "downloads_folder": "",
    "auto_install": True,
    "delete_zip": False,
    "disable_os_filter": False,
    "steamtools_mode": False,
    "auto_upload_keys": True,
    "download_history": [],
    "theme": "dark",
    "steam_integration_mode": "classic",
    "lua_modding_mode": False,
    "cloud_redirect_enabled": False,
    "cloud_redirect_provider": "local",
    "cloud_redirect_path": str(Path.home() / ".local" / "share" / "CloudRedirect" / "saves"),
    "auto_restart_steam": True,
    "profiles": {
        "default": {
            "name": "Varsayılan",
            "app_ids": [],
            "additional_apps": [],
            "dlc_data": {}
        }
    }
}

class SettingsManager:
    """Manages reading and writing the application's JSON configuration."""

    _settings: Dict[str, Any] = {}

    @classmethod
    def load(cls) -> None:
        """Loads the settings from disk. Creates default if it doesn't exist."""
        if not SETTINGS_FILE.exists():
            SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            cls._settings = DEFAULT_SETTINGS.copy()
            cls.save()
        else:
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Merge with default settings to ensure new keys are present
                    cls._settings = {**DEFAULT_SETTINGS, **data}
            except json.JSONDecodeError:
                # If file is corrupted, fallback to defaults
                cls._settings = DEFAULT_SETTINGS.copy()

    @classmethod
    def save(cls) -> None:
        """Saves current settings to disk."""
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(cls._settings, f, indent=4, ensure_ascii=False)

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Gets a setting value."""
        if not cls._settings:
            cls.load()
        return cls._settings.get(key, default)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Sets a setting value and immediately saves."""
        if not cls._settings:
            cls.load()
        cls._settings[key] = value
        cls.save()
