import os
import json
import logging
import asyncio
import webbrowser
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, parse_qs, urlparse

import httpx

from src.config.settings import SettingsManager
from src.config.slssteam import SLSsteamConfigManager
from src.utils.paths import get_steam_path
from src.utils.vdf_parser import LocalConfigManager

logger = logging.getLogger(__name__)

# Paths
CR_DIR = Path.home() / ".local" / "share" / "CloudRedirect"
CR_SO_PATH = CR_DIR / "cloud_redirect.so"
CR_CONFIG_FILE = CR_DIR / "config.json"
CR_TOKENS_DIR = CR_DIR / "tokens"

# GitHub release info
CR_REPO = "swwayps/cloudredirect-moon"
CR_RELEASE_URL = f"https://api.github.com/repos/{CR_REPO}/releases/latest"

# OAuth endpoints (CloudRedirect uses these)
OAUTH_CONFIG = {
    "gdrive": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scope": "https://www.googleapis.com/auth/drive.file",
        "client_id": "551275385122-5cjv7k7c7j7k7c7j7k7c7j7k7c7j7k7c7.apps.googleusercontent.com",  # placeholder - use your own
        "redirect_uri": "http://localhost:8080/oauth2callback",
    },
    "onedrive": {
        "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "scope": "Files.ReadWrite offline_access",
        "client_id": "your-onedrive-client-id",  # placeholder
        "redirect_uri": "http://localhost:8080/oauth2callback",
    },
}

PROVIDERS = ["gdrive", "onedrive", "local"]


class CloudRedirectManager:
    """
    Manages CloudRedirect 32-bit hook: binary installation, provider configuration,
    OAuth authentication, and Steam launch option injection.
    """

    @staticmethod
    def is_installed() -> bool:
        return CR_SO_PATH.exists() and CR_SO_PATH.stat().st_size > 0

    @classmethod
    async def install_binary(cls, progress_callback: Optional[callable] = None) -> bool:
        """Downloads the latest cloud_redirect.so from GitHub releases."""
        def log(msg: str):
            logger.info(msg)
            if progress_callback:
                progress_callback(msg)

        log("Fetching latest CloudRedirect release...")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get latest release
                resp = await client.get(CR_RELEASE_URL)
                resp.raise_for_status()
                release = resp.json()

                # Find 32-bit Linux asset
                asset_url = None
                version = release.get("tag_name", "unknown")
                for asset in release.get("assets", []):
                    name = asset.get("name", "")
                    if name.startswith("cloud_redirect-linux-") and name.endswith(".so"):
                        asset_url = asset.get("browser_download_url")
                        break

                if not asset_url:
                    # Fallback: try to build from source or use a known URL
                    log("No prebuilt asset found, trying fallback URL...")
                    asset_url = f"https://github.com/{CR_REPO}/releases/download/{version}/cloud_redirect-linux-{version.lstrip('v')}.so"

                log(f"Downloading cloud_redirect.so (version: {version})...")
                CR_DIR.mkdir(parents=True, exist_ok=True)
                CR_TOKENS_DIR.mkdir(parents=True, exist_ok=True)

                async with client.stream("GET", asset_url, timeout=60.0) as resp:
                    resp.raise_for_status()
                    total = int(resp.headers.get("content-length", 0))
                    downloaded = 0
                    with open(CR_SO_PATH, "wb") as f:
                        async for chunk in resp.aiter_bytes(8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total:
                                progress_callback(f"Downloading: {downloaded}/{total} bytes")

                CR_SO_PATH.chmod(0o755)

                # Verify 32-bit ELF
                import subprocess
                result = subprocess.run(["file", str(CR_SO_PATH)], capture_output=True, text=True)
                if "ELF 32-bit" not in result.stdout:
                    log(f"WARNING: Binary may not be 32-bit: {result.stdout.strip()}")

                log(f"CloudRedirect installed to {CR_SO_PATH}")
                return True

        except Exception as e:
            log(f"Failed to install CloudRedirect: {e}")
            return False

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """Reads CloudRedirect configuration."""
        if CR_CONFIG_FILE.exists():
            try:
                with open(CR_CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @classmethod
    def save_config(cls, config: Dict[str, Any]) -> None:
        """Saves CloudRedirect configuration."""
        CR_DIR.mkdir(parents=True, exist_ok=True)
        with open(CR_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

        # Also update SLSsteam settings for backward compat
        if config.get("enabled"):
            SettingsManager.set("cloud_redirect_enabled", True)
            SettingsManager.set("cloud_redirect_provider", config.get("provider", "local"))
            if config.get("local_path"):
                SettingsManager.set("cloud_redirect_path", config["local_path"])

    @classmethod
    def get_provider_config(cls, provider: str) -> Dict[str, Any]:
        """Gets configuration for a specific provider."""
        config = cls.get_config()
        return config.get("providers", {}).get(provider, {})

    @classmethod
    def set_provider_config(cls, provider: str, provider_config: Dict[str, Any]) -> None:
        """Sets configuration for a specific provider."""
        config = cls.get_config()
        if "providers" not in config:
            config["providers"] = {}
        config["providers"][provider] = provider_config
        config["provider"] = provider  # active provider
        config["enabled"] = True
        cls.save_config(config)

    @classmethod
    def get_active_provider(cls) -> str:
        """Returns the currently active provider."""
        config = cls.get_config()
        return config.get("provider", "local")

    @classmethod
    def get_cloud_root(cls) -> str:
        """Returns the configured cloud root path."""
        config = cls.get_config()
        return config.get("cloud_root", str(CR_DIR / "cloud_storage"))

    @classmethod
    def set_cloud_root(cls, path: str) -> None:
        """Sets the cloud root path."""
        config = cls.get_config()
        config["cloud_root"] = path
        cls.save_config(config)

    # --- OAuth Flow ---

    @classmethod
    def build_auth_url(cls, provider: str, state: str = None) -> Optional[str]:
        """Builds the OAuth authorization URL for a provider."""
        if provider not in OAUTH_CONFIG:
            return None

        cfg = OAUTH_CONFIG[provider]
        params = {
            "client_id": cfg["client_id"],
            "redirect_uri": cfg["redirect_uri"],
            "response_type": "code",
            "scope": cfg["scope"],
            "access_type": "offline",
            "prompt": "consent",
        }
        if state:
            params["state"] = state

        return f"{cfg['auth_url']}?{urlencode(params)}"

    @classmethod
    async def exchange_code_for_token(cls, provider: str, code: str) -> Optional[Dict[str, Any]]:
        """Exchanges OAuth authorization code for access/refresh tokens."""
        if provider not in OAUTH_CONFIG:
            return None

        cfg = OAUTH_CONFIG[provider]
        data = {
            "client_id": cfg["client_id"],
            "client_secret": "",  # Public client - no secret for now
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": cfg["redirect_uri"],
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(cfg["token_url"], data=data)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Token exchange failed for {provider}: {e}")
            return None

    @classmethod
    async def refresh_access_token(cls, provider: str, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refreshes an expired access token."""
        if provider not in OAUTH_CONFIG:
            return None

        cfg = OAUTH_CONFIG[provider]
        data = {
            "client_id": cfg["client_id"],
            "client_secret": "",
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(cfg["token_url"], data=data)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Token refresh failed for {provider}: {e}")
            return None

    @classmethod
    def save_tokens(cls, provider: str, tokens: Dict[str, Any]) -> None:
        """Saves OAuth tokens to provider-specific file."""
        CR_TOKENS_DIR.mkdir(parents=True, exist_ok=True)
        token_file = CR_TOKENS_DIR / f"tokens_{provider}.json"
        with open(token_file, "w") as f:
            json.dump(tokens, f, indent=2)

        # Update provider config with token path
        provider_config = cls.get_provider_config(provider)
        provider_config["token_path"] = str(token_file)
        cls.set_provider_config(provider, provider_config)

    @classmethod
    def load_tokens(cls, provider: str) -> Optional[Dict[str, Any]]:
        """Loads OAuth tokens for a provider."""
        provider_config = cls.get_provider_config(provider)
        token_path = provider_config.get("token_path")
        if token_path and Path(token_path).exists():
            try:
                with open(token_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    @classmethod
    def is_authenticated(cls, provider: str) -> bool:
        """Checks if a provider has valid tokens."""
        tokens = cls.load_tokens(provider)
        if not tokens:
            return False
        # Check if access token exists (expiry check would need token introspection)
        return "access_token" in tokens

    # --- Steam Integration ---

    @classmethod
    def apply_game_hook(cls, app_id: int) -> bool:
        """
        Injects CloudRedirect LD_PRELOAD into game's Steam launch options.
        """
        if not cls.is_installed():
            logger.error("CloudRedirect binary not installed")
            return False

        config = cls.get_config()
        if not config.get("enabled"):
            logger.warning("CloudRedirect not enabled in config")
            return False

        provider = cls.get_active_provider()
        if not cls.is_authenticated(provider) and provider != "local":
            logger.warning(f"Provider {provider} not authenticated")
            return False

        try:
            manager = SLSsteamConfigManager()
            app_id_str = str(app_id)

            # Get current launch options
            current_opts = manager.get_launch_options(app_id_str) or ""

            # Build LD_PRELOAD
            preload = f"LD_PRELOAD={CR_SO_PATH} %command%"
            if preload in current_opts:
                return True  # Already applied

            new_opts = f"{preload} {current_opts}".strip()
            return manager.update_launch_options(app_id_str, new_opts)

        except Exception as e:
            logger.error(f"Failed to apply CloudRedirect hook to {app_id}: {e}")
            return False

    @classmethod
    def remove_game_hook(cls, app_id: int) -> bool:
        """Removes CloudRedirect hook from game's launch options."""
        try:
            manager = SLSsteamConfigManager()
            app_id_str = str(app_id)

            current_opts = manager.get_launch_options(app_id_str) or ""
            preload = f"LD_PRELOAD={CR_SO_PATH}"

            if preload not in current_opts:
                return True  # Not applied

            # Remove the LD_PRELOAD part
            new_opts = current_opts.replace(preload, "").replace("%command%", "").strip()
            # Clean up double spaces
            new_opts = " ".join(new_opts.split())

            return manager.update_launch_options(app_id_str, new_opts)

        except Exception as e:
            logger.error(f"Failed to remove CloudRedirect hook from {app_id}: {e}")
            return False

    @classmethod
    def get_hooked_games(cls) -> List[int]:
        """Returns list of app_ids that have CloudRedirect hook applied."""
        try:
            manager = SLSsteamConfigManager()
            hooked = []
            for app_id_str in manager.get_all_apps():
                opts = manager.get_launch_options(app_id_str) or ""
                if f"LD_PRELOAD={CR_SO_PATH}" in opts:
                    hooked.append(int(app_id_str))
            return hooked
        except Exception:
            return []

    @classmethod
    async def ensure_ready(cls, progress_callback: Optional[callable] = None) -> bool:
        """Ensures binary is installed and configured."""
        if not cls.is_installed():
            return await cls.install_binary(progress_callback)
        return True