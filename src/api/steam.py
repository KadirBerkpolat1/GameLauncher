import shutil
from pathlib import Path

class SteamManagerError(Exception):
    pass

class SteamManager:
    """
    Handles file operations directly related to Steam directories,
    such as copying manifest files into the depotcache.
    """
    def __init__(self, steam_path: Path):
        self.steam_path = steam_path
        self.depotcache_path = self.steam_path / "depotcache"

    def install_manifest(self, manifest_source: Path) -> None:
        """
        Copies a .manifest file from a source location into Steam's depotcache.
        """
        if not manifest_source.exists() or not manifest_source.is_file():
            raise SteamManagerError(f"Source manifest file not found: {manifest_source}")

        if not str(manifest_source).endswith(".manifest"):
            raise SteamManagerError("File must have a .manifest extension")

        # Ensure depotcache directory exists
        self.depotcache_path.mkdir(parents=True, exist_ok=True)

        destination = self.depotcache_path / manifest_source.name

        try:
            shutil.copy2(manifest_source, destination)
        except Exception as e:
            raise SteamManagerError(f"Failed to copy manifest to depotcache: {e}")

    def verify_manifest_exists(self, manifest_id: str) -> bool:
        """
        Checks if a specific manifest file already exists in the depotcache.
        Usually manifest files are named like <depot_id>_<manifest_id>.manifest
        We can check by matching the manifest ID in the filename.
        """
        if not self.depotcache_path.exists():
            return False

        for file_path in self.depotcache_path.glob("*.manifest"):
            if manifest_id in file_path.name:
                return True

        return False
