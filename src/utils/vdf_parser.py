import vdf
from pathlib import Path
from typing import Dict, Any

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

    def update_launch_options(self, app_id: str):
        launch_opts = 'WINEDLLOVERRIDES="custom=n;onlinefix64=n;steam_api64=n;winmm=n,b;SteamOverlay64=n" %command%'
        for user_dir in self.userdata_paths:
            config_file = user_dir / "config" / "localconfig.vdf"
            if not config_file.exists():
                continue
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = vdf.load(f)
                
                node = data.setdefault("UserLocalConfigStore", {}).setdefault("Software", {}).setdefault("Valve", {}).setdefault("Steam", {}).setdefault("apps", {}).setdefault(str(app_id), {})
                
                existing_opts = node.get("LaunchOptions", "")
                if launch_opts not in existing_opts:
                    if existing_opts:
                        node["LaunchOptions"] = f'{existing_opts} {launch_opts}'
                    else:
                        node["LaunchOptions"] = launch_opts
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    vdf.dump(data, f, pretty=True)
            except Exception:
                pass
