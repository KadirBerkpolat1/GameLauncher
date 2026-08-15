import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import httpx

from src.config.settings import SettingsManager
from src.config.slssteam import SLSsteamConfigManager
from src.utils.paths import get_steam_path
from src.utils.vdf_parser import LocalConfigManager

logger = logging.getLogger(__name__)

CR_DIR = Path.home() / ".local" / "share" / "CloudRedirect"
CR_SO_PATH = CR_DIR / "cloud_redirect.so"
CR_CONFIG_FILE = CR_DIR / "config.json"
CR_SO_URL = "https://raw.githubusercontent.com/swwayps/cloudredirect-moon/master/cloud_redirect.so"


class CloudRedirectManager:
    """
    Official Selectively11/CloudRedirect implementation manager for Linux:
    1. Manages the 32-bit cloud_redirect.so hook.
    2. Syncs SLSsteam config (sets DisableCloud: False and adds AppID to AdditionalApps).
    3. Handles provider configurations (Google Drive, OneDrive, Cloudflare R2, S3, Local).
    4. Injects LD_PRELOAD into Steam's localconfig.vdf.
    """

    @staticmethod
    def is_installed() -> bool:
        return CR_SO_PATH.exists() and CR_SO_PATH.stat().st_size > 0

    @classmethod
    async def ensure_installed(cls) -> str:
        """Downloads the cloud_redirect.so binary if not already present."""
        if cls.is_installed():
            return str(CR_SO_PATH)

        CR_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Downloading CloudRedirect hook to {CR_SO_PATH}...")

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(CR_SO_URL)
                resp.raise_for_status()
                CR_SO_PATH.write_bytes(resp.content)
                CR_SO_PATH.chmod(0o755)
                logger.info("CloudRedirect hook downloaded successfully.")
                return str(CR_SO_PATH)
        except Exception as e:
            logger.error(f"Failed to download CloudRedirect hook: {e}")
            raise RuntimeError(f"CloudRedirect hook could not be downloaded: {e}") from e

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Reads CloudRedirect configuration."""
        if not CR_CONFIG_FILE.exists():
            default_cfg = {
                "enabled": SettingsManager.get("cloud_redirect_enabled", False),
                "provider": SettingsManager.get("cloud_redirect_provider", "local"),
                "local_path": SettingsManager.get("cloud_redirect_path", str(CR_DIR / "saves")),
                "s3_endpoint": "",
                "s3_bucket": "",
                "s3_access_key": "",
                "s3_secret_key": ""
            }
            CR_DIR.mkdir(parents=True, exist_ok=True)
            CR_CONFIG_FILE.write_text(json.dumps(default_cfg, indent=2), encoding="utf-8")
            return default_cfg

        try:
            return json.loads(CR_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    @classmethod
    def save_config(cls, config: Dict[str, Any]) -> None:
        """Saves CloudRedirect configuration and updates SLSsteam DisableCloud."""
        CR_DIR.mkdir(parents=True, exist_ok=True)
        CR_CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")

        if "enabled" in config:
            SettingsManager.set("cloud_redirect_enabled", config["enabled"])
            # Set SLSsteam DisableCloud to False when CloudRedirect is enabled
            try:
                sls = SLSsteamConfigManager()
                sls.set_disable_cloud(not config["enabled"])
            except Exception as e:
                logger.warning(f"Could not update SLSsteam DisableCloud: {e}")

        if "provider" in config:
            SettingsManager.set("cloud_redirect_provider", config["provider"])
        if "local_path" in config:
            SettingsManager.set("cloud_redirect_path", config["local_path"])

    @classmethod
    def apply_game_hook(cls, app_id: int) -> bool:
        """
        Applies Selectively11/CloudRedirect to a game:
        1. Adds AppID to SLSsteam AdditionalApps & enables Cloud in SLS.
        2. Injects LD_PRELOAD into Steam's localconfig.vdf.
        """
        # 1. SLSsteam AdditionalApps sync
        try:
            sls = SLSsteamConfigManager()
            sls.set_disable_cloud(False)
            sls.add_additional_app(int(app_id))
        except Exception as e:
            logger.warning(f"Failed to update SLSsteam config for app {app_id}: {e}")

        # 2. LD_PRELOAD injection
        if not cls.is_installed():
            return False

        so_path = str(CR_SO_PATH.resolve())
        steam_path = get_steam_path()
        if not steam_path:
            return False

        manager = LocalConfigManager(steam_path)
        hook_cmd = f"LD_PRELOAD=\"{so_path}\""

        current_opts = manager.get_launch_options(str(app_id)) or ""
        if hook_cmd in current_opts:
            return True

        if current_opts.strip():
            new_opts = f"{hook_cmd} {current_opts}"
        else:
            new_opts = f"{hook_cmd} %command%"

        return manager.update_launch_options(str(app_id), new_opts)

    @classmethod
    def remove_game_hook(cls, app_id: int) -> bool:
        """Removes the game from CloudRedirect and SLSsteam AdditionalApps."""
        # 1. SLSsteam AdditionalApps cleanup
        try:
            sls = SLSsteamConfigManager()
            sls.remove_additional_app(int(app_id))
        except Exception as e:
            logger.warning(f"Failed to remove app {app_id} from SLSsteam AdditionalApps: {e}")

        # 2. LD_PRELOAD removal
        steam_path = get_steam_path()
        if not steam_path:
            return False

        manager = LocalConfigManager(steam_path)
        so_path = str(CR_SO_PATH.resolve())
        current_opts = manager.get_launch_options(str(app_id)) or ""

        if not current_opts:
            return True

        cleaned = current_opts.replace(f"LD_PRELOAD=\"{so_path}\"", "").replace(f"LD_PRELOAD={so_path}", "").strip()
        if cleaned == "%command%":
            cleaned = ""

        return manager.update_launch_options(str(app_id), cleaned)
