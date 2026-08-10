import subprocess
import tempfile
import zipfile
import io
import os
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MANIFEST_TEMP_DIR = os.path.join(tempfile.gettempdir(), "gamelauncher_manifests")


class DownloadError(Exception):
    pass


class DownloadManager:
    """
    Handles triggering game downloads via DepotDownloaderMod (modded fork).
    Mirrors the Accela flow: manifests are extracted to a temp dir and handed
    to DDMod via -manifestfile, depot keys go via -depotkeys, and the game is
    downloaded straight into the Steam library at steamapps/common/<installdir>.
    """

    @staticmethod
    def _parse_lua(lua_content: str, app_id) -> dict:
        """Parses Hubcap/Enter-the-Wired style LUA into depot/dlc data.
        Returns dict with appid, game_name, depots {id: {key, desc}}, dlcs.
        AppID is taken from the caller (authoritative); lines carrying a depot
        decryption key become depots, key-less lines become DLCs."""
        game_data = {"appid": str(app_id), "depots": {}, "dlcs": {}}

        all_app_matches = list(
            re.finditer(r"addappid\((.*?)\)(.*)", lua_content, re.IGNORECASE)
        )
        if not all_app_matches:
            return game_data

        # Best-effort game name from the first addappid's trailing comment.
        first_app_match = all_app_matches[0]
        comment_part = first_app_match.group(2)
        game_name_match = re.search(r"--\s*(.*)", comment_part)
        game_data["game_name"] = (
            game_name_match.group(1).strip()
            if game_name_match
            else f"App_{game_data['appid']}"
        )

        # Every addappid carrying a depot key is a depot; key-less ones are DLCs.
        # The game line itself (no key) is never added as a depot.
        for match in all_app_matches:
            args = [arg.strip() for arg in match.group(1).strip().split(",")]
            app_id_line = args[0]

            comment_part = match.group(2)
            desc_match = re.search(r"--\s*(.*)", comment_part)
            desc = desc_match.group(1).strip() if desc_match else f"Depot {app_id_line}"

            if len(args) > 2 and args[2].strip('"'):
                depot_key = args[2].strip('"')
                game_data["depots"][app_id_line] = {"key": depot_key, "desc": desc}
            else:
                game_data["dlcs"][app_id_line] = desc

        # Optional manifest sizes: setManifestid(depot, "manifest", size)
        manifest_size_matches = list(
            re.finditer(
                r'setManifestid\(\s*(\d+)\s*,\s*".*?"\s*,\s*(\d+)\s*\)',
                lua_content,
                re.IGNORECASE,
            )
        )
        game_data["manifest_sizes"] = {}
        for match in manifest_size_matches:
            game_data["manifest_sizes"][match.group(1).strip()] = match.group(2).strip()

        return game_data

    @staticmethod
    def process_zip_bytes(zip_bytes: bytes) -> tuple:
        """Extracts the full Lua and .manifest files from a game ZIP.

        The Hubcap ZIP bundles everything needed in a single (usage-counted)
        call: the full Lua (depot keys + setManifestid + DLC info) and the
        per-depot .manifest files.

        Returns (lua_content, manifest_map, manifest_dir):
        - lua_content: str — the full Lua source from inside the ZIP.
        - manifest_map: dict mapping depot_id(str) -> manifest_id(str)
        - manifest_dir: temp dir where the .manifest files were written.
        Manifests are also copied into Steam's depotcache for the SLSsteam
        (Steam client) flow.
        """
        import re as _re
        from src.utils.paths import get_steam_path

        manifest_map = {}
        lua_content = ""

        steam_path = get_steam_path()
        if steam_path:
            depotcache_dir = steam_path / "depotcache"
            depotcache_dir.mkdir(parents=True, exist_ok=True)

        os.makedirs(MANIFEST_TEMP_DIR, exist_ok=True)

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            for info in z.infolist():
                if info.filename.endswith(".manifest"):
                    m = _re.match(r'^(\d+)_(\d+)\.manifest$', info.filename)
                    if m:
                        manifest_map[m.group(1)] = m.group(2)
                    content = z.read(info.filename)
                    with open(os.path.join(MANIFEST_TEMP_DIR, info.filename), "wb") as f:
                        f.write(content)
                    if steam_path:
                        with open(depotcache_dir / info.filename, "wb") as f:
                            f.write(content)
                elif info.filename.endswith(".lua"):
                    lua_content = z.read(info.filename).decode("utf-8", errors="ignore")

        return lua_content, manifest_map, MANIFEST_TEMP_DIR

    @staticmethod
    async def fetch_installdir_and_buildid(app_id: int) -> dict:
        """Fetches installdir and buildid from api.steamcmd.net (Steam PICS)."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"https://api.steamcmd.net/v1/info/{app_id}")
                if resp.status_code != 200:
                    return {}
                data = resp.json().get("data", {}).get(str(app_id), {})
                installdir = data.get("config", {}).get("installdir")
                buildid = (
                    data.get("depots", {})
                    .get("branches", {})
                    .get("public", {})
                    .get("buildid")
                )
                return {
                    "installdir": installdir,
                    "buildid": buildid,
                }
        except Exception as e:
            logger.error(f"Failed to fetch installdir/buildid for {app_id}: {e}")
            return {}

    @staticmethod
    def parse_lua_for_depots(lua_content: str, app_id: int) -> list:
        """Parses LUA and returns the depot list for the Accela-style DDMod flow."""
        parsed = DownloadManager._parse_lua(lua_content, app_id)
        depots = []

        for d_id, data in parsed.get("depots", {}).items():
            entry = {
                "depot_id": d_id,
                "decryption_key": data.get("key"),
                "manifest_id": None,
            }
            depots.append(entry)

        # setManifestid(depot_id, "manifest_id", ...)
        for match in re.finditer(r'setManifestid\((\d+),\s*"(\d+)"', lua_content):
            d_id, m_id = int(match.group(1)), match.group(2)
            for depot in depots:
                if int(depot["depot_id"]) == d_id:
                    depot["manifest_id"] = m_id

        return depots

    @staticmethod
    def apply_steam_side_effects(lua_content: str, app_id: int):
        from src.utils.paths import get_steam_path
        from src.utils.vdf_parser import VDFManager
        from src.config.slssteam import SLSsteamConfigManager

        steam_path = get_steam_path()
        vdf_mgr = VDFManager(steam_path) if steam_path else None
        sls_manager = SLSsteamConfigManager()
        if app_id:
            sls_manager.add_additional_app(app_id)

        parsed = DownloadManager._parse_lua(lua_content, app_id)

        for d_id, data in parsed.get("depots", {}).items():
            if vdf_mgr:
                try:
                    vdf_mgr.add_depot_key(d_id, data.get("key"))
                except Exception:
                    pass

        # setManifestid(depot_id, "manifest_id", ...)
        for match in re.finditer(r'setManifestid\((\d+),\s*"(\d+)"', lua_content):
            d_id, m_id = int(match.group(1)), match.group(2)
            sls_manager.set_manifest_id(d_id, m_id)

        sls_manager.save()

    @staticmethod
    async def _get_manifest_zip_cached(app_id: int) -> bytes:
        """Fetches the manifest ZIP, caching it on disk so re-installs of a
        game (e.g. adding DLC later) reuse it without spending another credit.

        The ZIP is tiny (~50 KB); a TTL guards against stale manifests.
        """
        from datetime import datetime
        from src.api.hubcap import hubcap_api

        cache_dir = Path.home() / ".cache" / "GameLauncher" / "manifests"
        cache_file = cache_dir / f"{app_id}.zip"

        try:
            if cache_file.exists():
                age = datetime.now().timestamp() - cache_file.stat().st_mtime
                if age < 7 * 24 * 3600:
                    logger.info(f"Manifest ZIP for {app_id} loaded from cache")
                    return cache_file.read_bytes()
        except OSError:
            pass

        zip_bytes = await hubcap_api.get_app_manifest_zip(app_id)
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file.write_bytes(zip_bytes)
        except OSError:
            pass
        return zip_bytes

    @staticmethod
    async def prepare_game_data(app_id: int, scope: str = "full") -> dict:
        """
        Prepares Accela-style game data for a download.

        Uses a SINGLE usage-counted API call: the manifest ZIP. The ZIP bundles
        the full Lua (depot keys + setManifestid + DLC info) together with the
        per-depot .manifest files, so no separate /lua request is needed
        (Accela parity: one credit per game). The ZIP is cached on disk, so
        later re-installs (e.g. adding DLC) cost 0 credits.

        Returns dict with keys: appid, game_name, installdir, buildid,
        depots {depot_id: {key, manifest_id}}, manifests, manifest_dir.
        """
        zip_bytes = await DownloadManager._get_manifest_zip_cached(app_id)
        lua_content, manifest_map, manifest_dir = DownloadManager.process_zip_bytes(
            zip_bytes
        )

        # Get the depot list for the Accela-style DDMod flow
        depot_list = DownloadManager.parse_lua_for_depots(lua_content, app_id)

        parsed = DownloadManager._parse_lua(lua_content, app_id)
        depots = {}
        for entry in depot_list:
            depots[entry["depot_id"]] = {
                "key": entry.get("decryption_key"),
                "manifest_id": entry.get("manifest_id"),
            }

        # Merge manifest IDs from ZIP filenames into depot list (fallback).
        for depot_id, manifest_id in manifest_map.items():
            if depot_id not in depots:
                depots[depot_id] = {"key": None, "manifest_id": None}
            if not depots[depot_id].get("manifest_id"):
                depots[depot_id]["manifest_id"] = manifest_id

        info = await DownloadManager.fetch_installdir_and_buildid(app_id)

        game_data = {
            "appid": str(app_id),
            "game_name": parsed.get("game_name", f"App_{app_id}"),
            "installdir": info.get("installdir") or parsed.get("installdir"),
            "buildid": info.get("buildid") or "",
            "depots": depots,
            "manifests": {
                depot_id: d.get("manifest_id")
                for depot_id, d in depots.items()
                if d.get("manifest_id")
            },
            "manifest_dir": manifest_dir,
            "lua_content": lua_content,
        }

        # Store installdir back onto parsed for callers that use process_lua_content output.
        if info.get("installdir"):
            parsed["installdir"] = info["installdir"]

        return game_data

    @staticmethod
    def install_local_zip(file_path: str) -> None:
        with open(file_path, "rb") as f:
            zip_bytes = f.read()
        lua_content, _manifest_map, _manifest_dir = DownloadManager.process_zip_bytes(zip_bytes)
        DownloadManager.apply_steam_side_effects(lua_content, None)

    @staticmethod
    def install_local_lua(file_path: str) -> None:
        import shutil
        from src.utils.paths import get_steam_path
        from src.utils.vdf_parser import VDFManager
        from src.config.slssteam import SLSsteamConfigManager

        steam_path = get_steam_path()
        vdf_mgr = None
        if steam_path:
            vdf_mgr = VDFManager(steam_path)
            plugin_dir = steam_path / "config" / "st-plug-in"
            plugin_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, plugin_dir)
        else:
            raise DownloadError("Steam path not found. Please configure it in Settings.")

        sls_manager = SLSsteamConfigManager()

        path_obj = Path(file_path)
        if path_obj.stem.isdigit():
            sls_manager.add_additional_app(int(path_obj.stem))

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        DownloadManager.apply_steam_side_effects(content, int(path_obj.stem) if path_obj.stem.isdigit() else None)

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
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            raise DownloadError(f"Failed to launch Steam protocol (xdg-open): {e}")
