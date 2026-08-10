import subprocess

class DownloadError(Exception):
    pass

class DownloadManager:
    """
    Handles triggering game downloads via Steam protocol or DepotDownloaderMod.
    """

    @staticmethod
    def process_zip_bytes(zip_bytes: bytes, app_id: int = None) -> dict:
        """Extracts .manifest files into the Steam depotcache directory.
        Returns a dict mapping depot_id -> manifest_id parsed from filenames."""
        import zipfile
        import io
        import re
        from src.utils.paths import get_steam_path
        from src.config.slssteam import SLSsteamConfigManager

        manifest_map = {}  # depot_id -> manifest_id

        steam_path = get_steam_path()
        if steam_path:
            depotcache_dir = steam_path / "depotcache"
            depotcache_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            for info in z.infolist():
                if info.filename.endswith(".manifest"):
                    # Parse depot_id and manifest_id from filename: {depot_id}_{manifest_id}.manifest
                    m = re.match(r'^(\d+)_(\d+)\.manifest$', info.filename)
                    if m:
                        manifest_map[int(m.group(1))] = m.group(2)
                    if steam_path:
                        with open(depotcache_dir / info.filename, "wb") as f:
                            f.write(z.read(info.filename))

        # Persist depot -> manifest_id mapping into SLSsteam config.yaml so the
        # modded Steam client can find the manifests in depotcache. In the current
        # Hubcap format the LUA no longer carries setManifestid lines, only the ZIP.
        if manifest_map:
            sls_manager = SLSsteamConfigManager()
            for d_id, m_id in manifest_map.items():
                if not sls_manager.config_data.get("ManifestIds"):
                    sls_manager.config_data["ManifestIds"] = {}
                sls_manager.config_data["ManifestIds"][d_id] = m_id
            sls_manager.save()

        return manifest_map
    @staticmethod
    def process_lua_content(lua_content: str, app_id: int) -> list:
        import re
        from src.utils.paths import get_steam_path
        from src.utils.vdf_parser import VDFManager
        from src.config.slssteam import SLSsteamConfigManager

        steam_path = get_steam_path()
        vdf_mgr = VDFManager(steam_path) if steam_path else None
        sls_manager = SLSsteamConfigManager()
        if app_id:
            sls_manager.add_additional_app(app_id)

        depots = {}

        # Parse addappid(depot_id, type, "key")
        for match in re.finditer(r'addappid\((\d+),\s*\d+,\s*"([a-fA-F0-9]+)"\)', lua_content):
            d_id, key = int(match.group(1)), match.group(2)
            if d_id not in depots: depots[d_id] = {}
            depots[d_id]["decryption_key"] = key
            if vdf_mgr:
                try: vdf_mgr.add_depot_key(d_id, key)
                except: pass

        # Parse setManifestid(depot_id, "manifest_id", ...)
        for match in re.finditer(r'setManifestid\((\d+),\s*"(\d+)"', lua_content):
            d_id, m_id = int(match.group(1)), match.group(2)
            if d_id not in depots: depots[d_id] = {}
            depots[d_id]["manifest_id"] = m_id
            sls_manager.set_manifest_id(d_id, m_id)

        sls_manager.save()
        return [{"depot_id": k, "decryption_key": v.get("decryption_key"), "manifest_id": v.get("manifest_id")} for k, v in depots.items()]


    @staticmethod
    async def prepare_game_data(app_id: int, scope: str = "full") -> list:
        """
        Downloads the Hubcap game data.
        Always downloads the LUA file to parse depots and keys.
        If scope is 'full', additionally downloads ZIP and extracts manifests to depotcache.
        Returns a list of depot dictionaries for DDMod.
        """
        from src.api.hubcap import hubcap_api
        
        # Always fetch LUA to get depots and update SLSsteam config
        # If scope is full, we use section="full" for Lua to get all keys
        lua_scope = scope if scope in ["basegame", "dlc"] else "full"
        lua_bytes = await hubcap_api.get_app_lua(app_id, section=lua_scope)
        lua_content = lua_bytes.decode('utf-8', errors='ignore')
        
        depots = DownloadManager.process_lua_content(lua_content, app_id)
        
        if scope == "full":
            try:
                zip_bytes = await hubcap_api.get_app_manifest_zip(app_id)
                manifest_map = DownloadManager.process_zip_bytes(zip_bytes, app_id)
                # Merge manifest IDs from ZIP filenames into depot list
                for depot in depots:
                    did = depot.get("depot_id")
                    if did and manifest_map.get(did):
                        depot["manifest_id"] = manifest_map[did]
            except Exception as e:
                print(f"Warning: Failed to download/extract manifest ZIP: {e}")

        return depots

    @staticmethod
    def install_local_zip(file_path: str) -> None:
        with open(file_path, "rb") as f:
            zip_bytes = f.read()
        DownloadManager.process_zip_bytes(zip_bytes)

    @staticmethod
    def install_local_lua(file_path: str) -> None:
        import re
        import shutil
        from pathlib import Path
        from src.utils.paths import get_steam_path
        from src.utils.vdf_parser import VDFManager
        from src.config.slssteam import SLSsteamConfigManager

        steam_path = get_steam_path()
        vdf_mgr = None
        if steam_path:
            vdf_mgr = VDFManager(steam_path)
            plugin_dir = steam_path / "config" / "stplug-in"
            plugin_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, plugin_dir)
        else:
            raise DownloadError("Steam path not found. Please configure it in Settings.")

        sls_manager = SLSsteamConfigManager()

        # Try to infer app_id from filename (e.g. 1091500.lua)
        path_obj = Path(file_path)
        if path_obj.stem.isdigit():
            sls_manager.add_additional_app(int(path_obj.stem))

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        for match in re.finditer(r'addappid\((\d+),\s*\d+,\s*"([a-fA-F0-9]+)"\)', content):
            d_id, key = int(match.group(1)), match.group(2)
            if vdf_mgr:
                try: vdf_mgr.add_depot_key(d_id, key)
                except: pass

        for match in re.finditer(r'setManifestid\((\d+),\s*"(\d+)"', content):
            d_id, m_id = int(match.group(1)), match.group(2)
            sls_manager.set_manifest_id(d_id, m_id)

        sls_manager.save()

    @staticmethod
    def install_via_steam(app_id: int) -> None:
        """
        Triggers the default Steam installation UI.
        Requires the manifest to be in depotcache and keys in config.vdf.
        """
        try:
            # xdg-open handles URI schemes on most Linux desktops
            subprocess.Popen(
                ["xdg-open", f"steam://install/{app_id}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            raise DownloadError(f"Failed to launch Steam protocol (xdg-open): {e}")
