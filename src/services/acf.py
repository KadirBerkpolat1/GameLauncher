import logging
import os
import re
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

def is_steam_running() -> bool:
    """Checks if Steam process is currently active."""
    try:
        res = subprocess.run(["pgrep", "-x", "steam"], capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False

def _safe_folder_name(game_name: str, app_id: str) -> str:
    safe = re.sub(r"[^\w\s-]", "", game_name or "").strip().replace(" ", "_")
    if not safe:
        safe = f"App_{app_id}"

def create_appmanifest(steamapps_dir, game_data: dict, size_on_disk: int = 0) -> str:
    """
    Generates a Steam appmanifest_<appid>.acf file inside steamapps_dir so the
    downloaded game appears as installed in the Steam library. Mirrors Accela's
    ACF format: StateFlags=4, installdir, buildid, InstalledDepots and a
    Proton override config when Windows depots are installed on Linux.

    Returns the path of the created file.
    """
    app_id = str(game_data.get("appid", ""))
    if not app_id:
        logger.error("Cannot create appmanifest: missing appid")
        return ""

    installdir = game_data.get("installdir") or _safe_folder_name(
        game_data.get("game_name"), app_id
    )
    buildid = str(game_data.get("buildid") or "0")
    game_name = game_data.get("game_name") or f"App_{app_id}"
    manifests = game_data.get("manifests", {}) or {}
    depots = game_data.get("depots", {}) or {}

    # Depot -> manifest mapping: prefer manifests dict, then depots entries.
    depot_manifest = {}
    for depot_id, manifest_id in (manifests or {}).items():
        if manifest_id:
            depot_manifest[str(depot_id)] = manifest_id
    for depot_id, d in depots.items():
        if str(depot_id) not in depot_manifest and d.get("manifest_id"):
            depot_manifest[str(depot_id)] = d["manifest_id"]

    # Platform config: Proton override when Windows depots are present on Linux.
    empty_platform_config = (
        '\t"UserConfig"\n'
        '\t{\n'
        '\t}\n'
        '\t"MountedConfig"\n'
        '\t{\n'
        '\t}'
    )
    platform_config = empty_platform_config
    if sys.platform == "linux":
        downloading_windows = False
        downloading_linux = False
        for depot_id_str in depot_manifest:
            oslist = str((depots.get(depot_id_str) or {}).get("oslist", "") or "").lower()
            if oslist == "windows":
                downloading_windows = True
            elif oslist == "linux":
                downloading_linux = True

        if downloading_windows and not downloading_linux:
            platform_config = (
                '\t"UserConfig"\n'
                '\t{\n'
                '\t\t"platform_override_dest"\t\t"linux"\n'
                '\t\t"platform_override_source"\t\t"windows"\n'
                '\t}\n'
                '\t"MountedConfig"\n'
                '\t{\n'
                '\t\t"platform_override_dest"\t\t"linux"\n'
                '\t\t"platform_override_source"\t\t"windows"\n'
                '\t}'
            )

    # InstalledDepots: only filled on Windows (matches Accela behaviour; on
    # Linux Steam re-resolves the depot list itself).
    depots_content = ""
    for depot_id_str, manifest_gid in depot_manifest.items():
        depots_content += (
            f'\t\t"{depot_id_str}"\n'
            f'\t\t{{\n'
            f'\t\t\t"manifest"\t\t"{manifest_gid}"\n'
            f'\t\t}}\n'
        )

    if depots_content and sys.platform == "win32":
        installed_depots_str = f'\t"InstalledDepots"\n\t{{\n{depots_content}\t}}'
    else:
        installed_depots_str = '\t"InstalledDepots"\n\t{\n\t}'

    acf_content = (
        f'"AppState"\n'
        f'{{\n'
        f'\t"appid"\t\t"{app_id}"\n'
        f'\t"Universe"\t\t"1"\n'
        f'\t"name"\t\t"{game_name}"\n'
        f'\t"StateFlags"\t\t"4"\n'
        f'\t"installdir"\t\t"{installdir}"\n'
        f'\t"SizeOnDisk"\t\t"{size_on_disk}"\n'
        f'\t"buildid"\t\t"{buildid}"\n'
        f'{installed_depots_str}\n'
        f'{platform_config}\n'
        f'}}\n'
    )
    acf_path = os.path.join(steamapps_dir, f"appmanifest_{app_id}.acf")
    tmp_path = acf_path + ".tmp"

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(acf_content)
        os.replace(tmp_path, acf_path)
        logger.info(f"Wrote appmanifest: {acf_path}")
    except Exception as e:
        logger.error(f"Failed to write appmanifest: {e}")
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return ""

    return acf_path
