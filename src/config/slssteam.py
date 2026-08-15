import logging
import yaml
from pathlib import Path
from typing import Dict, Any
from src.utils.paths import get_slssteam_config_path
from src.utils.vdf_parser import LocalConfigManager

logger = logging.getLogger(__name__)

# Launch options prefix for Nebula fixes
NEBULA_FIX_PREFIX = "NEBULA_FIX_"

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
            self.config_data["AdditionalApps"].append(int(app_id))
            self.save()

    def remove_additional_app(self, app_id: int) -> None:
        if self.config_data.get("AdditionalApps") and int(app_id) in self.config_data["AdditionalApps"]:
            self.config_data["AdditionalApps"].remove(int(app_id))
            self.save()

    def set_disable_cloud(self, disabled: bool) -> None:
        """Configures DisableCloud (set to False for CloudRedirect)."""
        self.config_data["DisableCloud"] = bool(disabled)
        self.save()

    def is_cloud_disabled(self) -> bool:
        return self.config_data.get("DisableCloud", True)

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
    def _build_fix_launch_option(self, app_id: int, source: str) -> str:
        """Build the launch option string for a fix."""
        # Map fix source to appropriate LD_PRELOAD/LD_AUDIT
        if source == "ryuu":
            # Ryuu fixes use Lua scripts loaded via SLSsteam
            return f"{NEBULA_FIX_PREFIX}{source}_{app_id}=ld_preload_sls"
        elif source == "crackbypass":
            # Crack fixes typically use winmm.dll or steam_api64.dll replacement
            return f"{NEBULA_FIX_PREFIX}{source}_{app_id}=ld_preload_crack"
        elif source == "onlinefix":
            # OnlineFix uses onlinefix64.dll
            return f"{NEBULA_FIX_PREFIX}{source}_{app_id}=ld_preload_onlinefix"
        elif source == "freetp":
            # FreeTP typically uses steam_api64.dll replacement
            return f"{NEBULA_FIX_PREFIX}{source}_{app_id}=ld_preload_freetp"
        elif source == "goldberg":
            return f"{NEBULA_FIX_PREFIX}{source}_{app_id}=goldberg"
        return f"{NEBULA_FIX_PREFIX}{source}_{app_id}=generic"

    def apply_fix_launch_options(self, app_id: int, source: str) -> bool:
        """Apply fix launch options to Steam localconfig.vdf (no restart needed)."""
        fix_opt = self._build_fix_launch_option(app_id, source)
        
        # Get current launch options
        local_mgr = LocalConfigManager()
        current_opts = local_mgr.get_launch_options(str(app_id))
        
        # Add our fix option if not present
        if fix_opt not in current_opts:
            if current_opts:
                new_opts = f"{current_opts} {fix_opt}"
            else:
                new_opts = fix_opt
            
            success = local_mgr.set_launch_options(str(app_id), new_opts)
            if success:
                logger.info(f"Applied fix launch options for app {app_id} (source: {source}): {fix_opt}")
            return success
        return True

    def remove_fix_launch_options(self, app_id: int) -> bool:
        """Remove all Nebula fix launch options for an app."""
        local_mgr = LocalConfigManager()
        current_opts = local_mgr.get_launch_options(str(app_id))
        
        if not current_opts:
            return True
        
        # Remove all NEBULA_FIX_* options
        parts = current_opts.split()
        filtered = [p for p in parts if not p.startswith(NEBULA_FIX_PREFIX)]
        new_opts = " ".join(filtered)
        
        if new_opts != current_opts:
            return local_mgr.set_launch_options(str(app_id), new_opts)
        return True

    def get_fix_launch_options(self, app_id: int) -> Dict[str, str]:
        """Get all active Nebula fix launch options for an app."""
        local_mgr = LocalConfigManager()
        current_opts = local_mgr.get_launch_options(str(app_id))
        
        fixes = {}
        for part in current_opts.split():
            if part.startswith(NEBULA_FIX_PREFIX):
                # Parse format: NEBULA_FIX_source_appid=value
                try:
                    key, value = part.split("=", 1)
                    # Extract source from key
                    prefix_len = len(NEBULA_FIX_PREFIX)
                    source_appid = key[prefix_len:]
                    source = source_appid.rsplit("_", 1)[0]
                    fixes[source] = value
                except ValueError:
                    continue
        return fixes

    def sync_from_steam(self, app_id: int) -> Dict[str, str]:
        """Sync fix status from Steam client launch options."""
        return self.get_fix_launch_options(app_id)
