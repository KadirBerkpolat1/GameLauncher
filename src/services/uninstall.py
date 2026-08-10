import re
import shutil
from pathlib import Path
from typing import Optional

from src.config.slssteam import SLSsteamConfigManager
from src.utils.paths import get_steam_path, get_steam_libraries


class UninstallError(Exception):
    pass


def _read_manifest_zip_cache(app_id: int) -> Optional[dict]:
    """
    Reads the locally cached manifest ZIP (~/.cache/GameLauncher/manifests/<appid>.zip)
    and extracts the depot -> manifest_id map for the game.
    Returns {} if the cache is missing or unreadable.
    """
    cache_file = Path.home() / ".cache" / "GameLauncher" / "manifests" / f"{app_id}.zip"
    if not cache_file.exists():
        return {}

    import io
    import zipfile

    try:
        with zipfile.ZipFile(io.BytesIO(cache_file.read_bytes())) as z:
            manifest_map = {}
            for info in z.infolist():
                if info.filename.endswith(".manifest"):
                    m = re.match(r"^(\d+)_(\d+)\.manifest$", info.filename)
                    if m:
                        manifest_map[m.group(1)] = m.group(2)
                elif info.filename.endswith(".lua"):
                    lua = z.read(info.filename).decode("utf-8", errors="ignore")
                    for match in re.finditer(r"setManifestid\(\s*(\d+)\s*,\s*\"(\d+)\"", lua):
                        manifest_map.setdefault(match.group(1), match.group(2))
            return manifest_map
    except Exception:
        return {}


def _find_installdir(app_id: int) -> str:
    """Reads 'installdir' from appmanifest_<appid>.acf in any Steam library."""
    for lib in get_steam_libraries():
        acf = Path(lib) / "steamapps" / f"appmanifest_{app_id}.acf"
        if acf.exists():
            try:
                m = re.search(r'"installdir"\s*"([^"]+)"', acf.read_text(errors="ignore"))
                if m:
                    return m.group(1)
            except OSError:
                continue
    return ""


def uninstall_game(app_id: int, remove_files: bool = True, remove_lua: bool = True) -> dict:
    """
    Fully removes a game from the system:
      - deletes game files (steamapps/common/<installdir>)
      - deletes appmanifest_<appid>.acf
      - deletes the Proton prefix (steamapps/compatdata/<appid>)
      - deletes depotcache manifests belonging to the game
      - removes the game's depot keys from config.vdf
      - removes the game's ManifestIds / AppIds / AdditionalApps from SLSsteam config
      - removes the cached manifest ZIP and stplug-in Lua file

    Returns a summary dict of what was deleted.
    """
    summary = {
        "files": False,
        "acf": False,
        "prefix": False,
        "depotcache": 0,
        "config_vdf": 0,
        "config": False,
        "lua": False,
        "cache": False,
    }

    app_id_str = str(app_id)
    depot_map = _read_manifest_zip_cache(app_id)
    installdir = _find_installdir(app_id) or _read_installdir_from_cache(app_id)

    # --- Steam library data: files, ACF, Proton prefix, depotcache ---
    steam_path = get_steam_path()

    if remove_files:
        for lib in get_steam_libraries():
            steamapps = Path(lib) / "steamapps"

            acf = steamapps / f"appmanifest_{app_id_str}.acf"
            if acf.exists():
                try:
                    acf.unlink()
                    summary["acf"] = True
                except OSError:
                    pass

            if installdir:
                common_dir = steamapps / "common" / installdir
                if common_dir.exists():
                    try:
                        shutil.rmtree(common_dir)
                        summary["files"] = True
                    except OSError:
                        pass

            compatdata = steamapps / "compatdata" / app_id_str
            if compatdata.exists():
                try:
                    shutil.rmtree(compatdata)
                    summary["prefix"] = True
                except OSError:
                    pass

            depotcache = steamapps / "depotcache"
            if depot_map and depotcache.exists():
                for depot_id, man_id in depot_map.items():
                    mfile = depotcache / f"{depot_id}_{man_id}.manifest"
                    try:
                        if mfile.exists():
                            mfile.unlink()
                            summary["depotcache"] += 1
                    except OSError:
                        continue

        # Steam root depotcache (copied during prepare_game_data)
        if steam_path:
            depotcache_dir = steam_path / "depotcache"
            if depot_map and depotcache_dir.exists():
                for depot_id, man_id in depot_map.items():
                    mfile = depotcache_dir / f"{depot_id}_{man_id}.manifest"
                    try:
                        if mfile.exists():
                            mfile.unlink()
                            summary["depotcache"] += 1
                    except OSError:
                        continue

    # --- config.vdf: remove depot keys for this game ---
    if remove_files and steam_path:
        try:
            from src.utils.vdf_parser import VDFManager
            vdf_mgr = VDFManager(steam_path)
            for depot_id in depot_map:
                try:
                    if vdf_mgr.remove_depot_key(depot_id):
                        summary["config_vdf"] += 1
                except Exception:
                    continue
        except Exception:
            pass

    # --- SLSsteam config: AppIds, AdditionalApps, ManifestIds ---
    if remove_lua:
        try:
            manager = SLSsteamConfigManager()
            manager.config_data["AdditionalApps"] = [
                x for x in (manager.config_data.get("AdditionalApps") or [])
                if str(x) != app_id_str
            ]
            manager.config_data["AppIds"] = [
                x for x in (manager.config_data.get("AppIds") or [])
                if str(x) != app_id_str
            ]
            manifest_ids = manager.config_data.get("ManifestIds")
            if isinstance(manifest_ids, dict):
                for depot_id in depot_map:
                    manifest_ids.pop(depot_id, None)
            app_tokens = manager.config_data.get("AppTokens")
            if isinstance(app_tokens, dict):
                app_tokens.pop(app_id_str, None)
            manager.save()
            summary["config"] = True
        except Exception as e:
            raise UninstallError(f"Failed to update SLSsteam config: {e}")

    # --- stplug-in Lua file ---
    if remove_lua and steam_path:
        for plugin_dir_name in ("stplug-in", "st-plug-in"):
            plugin_dir = steam_path / "config" / plugin_dir_name
            if plugin_dir.exists():
                for lua_file in plugin_dir.glob(f"{app_id_str}*.lua"):
                    try:
                        lua_file.unlink()
                        summary["lua"] = True
                    except OSError:
                        continue

    # --- Cached manifest ZIP ---
    if remove_files:
        cache_file = Path.home() / ".cache" / "GameLauncher" / "manifests" / f"{app_id_str}.zip"
        if cache_file.exists():
            try:
                cache_file.unlink()
                summary["cache"] = True
            except OSError:
                pass

    return summary


def _read_installdir_from_cache(app_id: int) -> str:
    """Best-effort: extract installdir from the cached Lua (addappid comment)."""
    cache_file = Path.home() / ".cache" / "GameLauncher" / "manifests" / f"{app_id}.zip"
    if not cache_file.exists():
        return ""
    import io
    import zipfile
    try:
        with zipfile.ZipFile(io.BytesIO(cache_file.read_bytes())) as z:
            for info in z.infolist():
                if info.filename.endswith(".lua"):
                    lua = z.read(info.filename).decode("utf-8", errors="ignore")
                    for match in re.finditer(r"--\s*installdir\s*=\s*([^\s,]+)", lua, re.IGNORECASE):
                        return match.group(1).strip('"')
                    return ""
    except Exception:
        return ""
