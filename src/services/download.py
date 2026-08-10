import subprocess
import asyncio
from pathlib import Path
from typing import AsyncGenerator
from src.config.settings import SettingsManager

class DownloadError(Exception):
    pass

class DownloadManager:
    """
    Handles triggering game downloads via Steam protocol or DepotDownloaderMod.
    """

    @staticmethod
    def process_zip_bytes(zip_bytes: bytes, app_id: int = None) -> list:
        import zipfile
        import io
        import re
        from src.utils.paths import get_steam_path
        from src.utils.vdf_parser import VDFManager
        from src.config.slssteam import SLSsteamConfigManager

        steam_path = get_steam_path()
        vdf_mgr = None
        depotcache_dir = None
        if steam_path:
            depotcache_dir = steam_path / "depotcache"
            depotcache_dir.mkdir(parents=True, exist_ok=True)
            vdf_mgr = VDFManager(steam_path)

        sls_manager = SLSsteamConfigManager()
        if app_id:
            sls_manager.add_additional_app(app_id)

        depots = {}

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            for info in z.infolist():
                if info.filename.endswith(".manifest"):
                    if depotcache_dir:
                        # Write manifest to depotcache
                        with open(depotcache_dir / info.filename, "wb") as f:
                            f.write(z.read(info.filename))
                elif info.filename.endswith(".lua"):
                    content = z.read(info.filename).decode('utf-8', errors='ignore')

                    # Parse addappid(depot_id, type, "key")
                    for match in re.finditer(r'addappid\((\d+),\s*\d+,\s*"([a-fA-F0-9]+)"\)', content):
                        d_id, key = int(match.group(1)), match.group(2)
                        if d_id not in depots: depots[d_id] = {}
                        depots[d_id]["decryption_key"] = key
                        if vdf_mgr:
                            try: vdf_mgr.add_depot_key(d_id, key)
                            except: pass

                    # Parse setManifestid(depot_id, "manifest_id", ...)
                    for match in re.finditer(r'setManifestid\((\d+),\s*"(\d+)"', content):
                        d_id, m_id = int(match.group(1)), match.group(2)
                        if d_id not in depots: depots[d_id] = {}
                        depots[d_id]["manifest_id"] = m_id
                        sls_manager.set_manifest_id(d_id, m_id)

        # Save all config changes
        sls_manager.save()

        # Return list of depots for DDMod
        return [{"depot_id": k, "decryption_key": v.get("decryption_key"), "manifest_id": v.get("manifest_id")} for k, v in depots.items()]
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
        If scope is 'full', downloads ZIP and extracts manifests.
        If scope is 'basegame' or 'dlc', downloads only the relevant LUA file (saves quota/space).
        Returns a list of depot dictionaries for DDMod fallback.
        """
        from src.api.hubcap import hubcap_api
        
        if scope == "full":
            zip_bytes = await hubcap_api.get_app_manifest_zip(app_id)
            return DownloadManager.process_zip_bytes(zip_bytes, app_id)
        else:
            lua_bytes = await hubcap_api.get_app_lua(app_id, section=scope)
            lua_content = lua_bytes.decode('utf-8', errors='ignore')
            return DownloadManager.process_lua_content(lua_content, app_id)

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

    @staticmethod
    async def install_via_ddmod(app_id: int, depot_id: int, manifest_id: int) -> AsyncGenerator[str, None]:
        """
        Downloads depot contents directly using DepotDownloaderMod.
        Yields stdout lines for progress tracking in the UI.
        """
        ddmod_path_str = SettingsManager.get("depotdownloadermod_path", "")
        if not ddmod_path_str:
            raise DownloadError("DepotDownloaderMod path is not configured in settings.")

        ddmod_path = Path(ddmod_path_str)
        if not ddmod_path.exists() or not ddmod_path.is_file():
            raise DownloadError(f"DepotDownloaderMod not found at {ddmod_path}")

        is_dll = ddmod_path_str.lower().endswith('.dll')

        if is_dll:
            # Check for .NET runtime only if using DLL
            dotnet_check = await asyncio.create_subprocess_shell(
                "dotnet --version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await dotnet_check.communicate()
            if dotnet_check.returncode != 0:
                raise DownloadError(".NET runtime (dotnet) is not installed or not in PATH.")
            cmd = ["dotnet", str(ddmod_path)]
        else:
            # Standalone binary
            cmd = [str(ddmod_path)]

        cmd.extend([
            "-app", str(app_id),
            "-depot", str(depot_id),
            "-manifest", str(manifest_id)
        ])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT # Merge stderr into stdout for parsing
        )

        if process.stdout:
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                decoded_line = line.decode('utf-8', errors='replace').strip()
                if decoded_line:
                    yield decoded_line

        await process.wait()

        if process.returncode != 0:
            raise DownloadError(f"DepotDownloaderMod exited with code {process.returncode}")
