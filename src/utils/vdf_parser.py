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
