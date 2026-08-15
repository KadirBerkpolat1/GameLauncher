import logging
import re
import vdf
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class VDFParserError(Exception):
    pass

class VDFManager:
    """
    Handles reading and modifying Steam's config.vdf file,
    specifically injecting depot decryption keys.
    """
    def __init__(self, steam_path: Path):
        self.steam_path = steam_path
        self.config_vdf_path = self.steam_path / "config" / "config.vdf"

    def _ensure_exists(self) -> None:
        if not self.config_vdf_path.exists():
            raise VDFParserError(f"config.vdf not found at {self.config_vdf_path}")

    def add_depot_key(self, depot_id: str, decryption_key: str) -> None:
        """
        Injects a decryption key into the config.vdf file under the 'depots' section.
        """
        self._ensure_exists()

        try:
            with open(self.config_vdf_path, 'r', encoding='utf-8') as f:
                data = vdf.load(f)
        except Exception as e:
            raise VDFParserError(f"Failed to parse config.vdf: {e}")

        # The structure is usually "InstallConfigStore" -> "Software" -> "Valve" -> "Steam"
        # However, older or different clients might just have it at root or under "Software".
        # We will navigate safely.

        # Standard navigation
        try:
            steam_node = data.get("InstallConfigStore", {}).get("Software", {}).get("Valve", {}).get("Steam", {})
            if not steam_node:
                # Fallback to older format if InstallConfigStore isn't the root
                steam_node = data.get("Software", {}).get("Valve", {}).get("Steam", {})

            if not steam_node:
                raise VDFParserError("Could not locate Software->Valve->Steam node in config.vdf")

            # Ensure "depots" node exists
            if "depots" not in steam_node:
                steam_node["depots"] = {}

            # Ensure specific depot_id node exists
            if str(depot_id) not in steam_node["depots"]:
                steam_node["depots"][str(depot_id)] = {}

            # Inject the DecryptionKey
            steam_node["depots"][str(depot_id)]["DecryptionKey"] = decryption_key

        except Exception as e:
            raise VDFParserError(f"Error navigating/modifying VDF structure: {e}")

        # Save changes
        try:
            with open(self.config_vdf_path, 'w', encoding='utf-8') as f:
                vdf.dump(data, f, pretty=True)
        except Exception as e:
            raise VDFParserError(f"Failed to write changes to config.vdf: {e}")

    def remove_depot_key(self, depot_id: str) -> bool:
        """
        Removes the depot decryption key entry for the given depot from the
        config.vdf 'depots' section. Returns True if an entry was removed.
        """
        self._ensure_exists()

        try:
            with open(self.config_vdf_path, 'r', encoding='utf-8') as f:
                data = vdf.load(f)
        except Exception as e:
            raise VDFParserError(f"Failed to parse config.vdf: {e}")

        steam_node = data.get("InstallConfigStore", {}).get("Software", {}).get("Valve", {}).get("Steam", {})
        if not steam_node:
            steam_node = data.get("Software", {}).get("Valve", {}).get("Steam", {})

        if not steam_node:
            raise VDFParserError("Could not locate Software->Valve->Steam node in config.vdf")

        depots = steam_node.get("depots")
        removed = False
        if isinstance(depots, dict) and str(depot_id) in depots:
            del depots[str(depot_id)]
            removed = True

        if not removed:
            return False

        try:
            with open(self.config_vdf_path, 'w', encoding='utf-8') as f:
                vdf.dump(data, f, pretty=True)
        except Exception as e:
            raise VDFParserError(f"Failed to write changes to config.vdf: {e}")

        return True

class LocalConfigManager:
    """
    Manages Steam localconfig.vdf files across all userdata profiles.
    """
    def __init__(self):
        self.userdata_paths = self._find_userdata_paths()

    def _find_userdata_paths(self):
        paths = []
        possible_steam_paths = [
            Path.home() / ".local" / "share" / "Steam",
            Path.home() / ".steam" / "steam",
            Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam"
        ]
        for sp in possible_steam_paths:
            userdata = sp / "userdata"
            if userdata.is_dir():
                for d in userdata.iterdir():
                    if d.is_dir():
                        paths.append(d)
        return paths

    def get_launch_options(self, app_id: str) -> str:
        """Get current launch options for an app."""
        for user_dir in self.userdata_paths:
            config_file = user_dir / "config" / "localconfig.vdf"
            if not config_file.exists():
                continue
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = vdf.load(f)
                
                node = data.get("UserLocalConfigStore", {}).get("Software", {}).get("Valve", {}).get("Steam", {}).get("apps", {}).get(str(app_id), {})
                return node.get("LaunchOptions", "")
            except Exception:
                pass
        return ""

    def set_launch_options(self, app_id: str, launch_options: str) -> bool:
        """Set launch options for an app across all userdata profiles."""
        updated = False
        for user_dir in self.userdata_paths:
            config_file = user_dir / "config" / "localconfig.vdf"
            if not config_file.exists():
                continue
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = vdf.load(f)
                
                apps_node = data.setdefault("UserLocalConfigStore", {}).setdefault("Software", {}).setdefault("Valve", {}).setdefault("Steam", {}).setdefault("apps", {})
                app_node = apps_node.setdefault(str(app_id), {})
                
                app_node["LaunchOptions"] = launch_options
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    vdf.dump(data, f, pretty=True)
                updated = True
            except Exception as e:
                logger.warning(f"Failed to set launch options for {app_id}: {e}")
        return updated

    def update_launch_options(self, app_id: str):
        """Merge fix DLL overrides into existing launch options.

        Preserves any user-added options and only adds/updates the
        WINEDLLOVERRIDES block needed for OnlineFix + Steamless/SteamStubs.
        """
        existing = self.get_launch_options(app_id)

        # Required DLL overrides: OnlineFix + Steamless/SteamStubs + common mod DLLs
        required = {
            "custom": "n",
            "onlinefix64": "n",
            "steam_api": "n",
            "steam_api64": "n",
            "tier0_s": "n",
            "vstdlib_s": "n",
            "winmm": "n,b",
        }

        # Parse existing WINEDLLOVERRIDES="..." if present
        existing_overrides = {}
        wo_match = re.search(r'WINEDLLOVERRIDES="([^"]*)"', existing)
        if wo_match:
            for pair in wo_match.group(1).split(";"):
                pair = pair.strip()
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    existing_overrides[k.strip()] = v.strip()

        # Merge: keep existing overrides, add/update required ones
        merged = {**existing_overrides, **required}
        merged_str = ";".join(f"{k}={v}" for k, v in merged.items())

        # Strip old WINEDLLOVERRIDES block from existing options
        cleaned = re.sub(r'WINEDLLOVERRIDES="[^"]*"\s*', '', existing).strip()

        # Build final options: merged overrides + whatever user had (e.g. %command%)
        parts = [f'WINEDLLOVERRIDES="{merged_str}"']
        if cleaned:
            parts.append(cleaned)
        launch_opts = " ".join(parts)

        self.set_launch_options(app_id, launch_opts)
