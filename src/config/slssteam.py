import yaml
from pathlib import Path
from typing import Dict, Any
from src.utils.paths import get_slssteam_config_path

class SLSsteamConfigError(Exception):
    pass

class SLSsteamConfigManager:
    """
    Manages the reading and writing of the SLSsteam config.yaml file.
    """
    def __init__(self) -> None:
        self.config_path: Path = get_slssteam_config_path()
        self.config_data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Loads the YAML configuration. Creates a default one if it doesn't exist."""
        if not self.config_path.exists():
            self._create_default_config()
        else:
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if not data:
                        data = {}
                    # Merge: inject missing keys from defaults
                    defaults = self._get_default_structure()
                    dirty = False
                    for key, val in defaults.items():
                        if key not in data:
                            data[key] = val
                            dirty = True
                    self.config_data = data
                    # Persist merged config so SLSsteam sees all keys
                    if dirty:
                        self.save()
            except Exception as e:
                raise SLSsteamConfigError(f"Failed to load SLSsteam config: {e}")

    def save(self) -> None:
        """Saves the current configuration back to the YAML file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                # Use default_flow_style=False for block style YAML formatting
                yaml.dump(self.config_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        except Exception as e:
            raise SLSsteamConfigError(f"Failed to save SLSsteam config: {e}")

    def _get_default_structure(self) -> Dict[str, Any]:
        return {
            "PlayNotOwnedGames": True,
            "DisableFamilyShareLock": True,
            "UseWhitelist": False,
            "AppIds": None,
            "AdditionalApps": None,
            "DlcData": None,
            "AppTokens": None,
            "FakeOffline": None,
            "FakeAppIds": None,
            "ManifestIds": None,
            "DepotBlacklist": None,
            "IdleStatus": {"AppId": 0, "Title": ""},
            "GameTitles": None,
            "SubscriptionTimestamps": None,
            "DenuvoGames": None,
            "SteamIdOverride": None,
            "MaxSchemaTries": 10,
            "SafeMode": False,
            "Notifications": True,
            "WarnHashMissmatch": False,
            "NotifyInit": True,
            "API": False,
            "DisableCloud": True,
            "DisableUpdates": True,
            "FakeName": "",
            "FakeEmail": "",
            "FakeWalletBalance": 0,
            "LogLevel": 2,
            "DumpClientInterfaces": False,
            "ExtendedLogging": False,
        }

    def _create_default_config(self) -> None:
        self.config_data = self._get_default_structure()
        self.save()

    def add_additional_app(self, app_id: int) -> None:
        if not self.config_data.get("AdditionalApps"):
            self.config_data["AdditionalApps"] = []
        if app_id not in self.config_data["AdditionalApps"]:
            self.config_data["AdditionalApps"].append(app_id)
            self.save()

    def set_manifest_id(self, depot_id: int, manifest_id: int) -> None:
        if not self.config_data.get("ManifestIds"):
            self.config_data["ManifestIds"] = {}
        self.config_data["ManifestIds"][depot_id] = manifest_id
        self.save()

    def ensure_play_not_owned_games(self, enabled: bool = True) -> bool:
        """Ensures PlayNotOwnedGames is set to the requested value.
        Returns True if a write was performed, False if already in the desired state."""
        if self.config_data.get("PlayNotOwnedGames") == enabled:
            return False
        self.config_data["PlayNotOwnedGames"] = enabled
        self.save()
        return True
