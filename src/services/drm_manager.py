import os
import shutil
import logging
import tempfile
import zipfile
import tarfile
from pathlib import Path
from typing import List, Set
import httpx

logger = logging.getLogger(__name__)

GOLDBERG_URL = "https://gitlab.com/Mr_Goldberg/goldberg_emulator/-/jobs/artifacts/master/download?job=build"
GOLDBERG_FALLBACK_URL = "https://raw.githubusercontent.com/FaultyPacketOverflowVector/Accela/main/deps/Goldberg.tar.gz"

class DRMManager:
    """Manages DRM removal using Goldberg Emulator."""
    
    @staticmethod
    def get_goldberg_src() -> Path:
        """Ensures Goldberg binaries exist and returns their path."""
        root_dir = Path(__file__).resolve().parent.parent.parent
        assets_dir = root_dir / "assets" / "goldberg"
        user_dir = Path.home() / ".local" / "share" / "GameLauncher" / "goldberg"

        for target_path in (assets_dir, user_dir):
            if (target_path / "windows" / "steam_api64.dll").exists() or (target_path / "steam_api64.dll").exists():
                return target_path
        
        # Try to copy from ACCELA's bundle if available
        accela_gb = Path.home() / ".local/share/ACCELA/squashfs-root/deps/Goldberg"
        if accela_gb.exists():
            try:
                assets_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(accela_gb, assets_dir, dirs_exist_ok=True)
                return assets_dir
            except Exception:
                pass

        # Download Goldberg automatically
        download_target = assets_dir
        try:
            assets_dir.parent.mkdir(parents=True, exist_ok=True)
            assets_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            download_target = user_dir
            download_target.mkdir(parents=True, exist_ok=True)

        DRMManager._download_goldberg(download_target)
        return download_target

    @staticmethod
    def _download_goldberg(target_dir: Path) -> None:
        """Downloads and extracts Goldberg Emulator binaries to target_dir."""
        logger.info(f"Downloading Goldberg Emulator to {target_dir}...")
        windows_dir = target_dir / "windows"
        linux_dir = target_dir / "linux"
        windows_dir.mkdir(parents=True, exist_ok=True)
        linux_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmp_dir:
            archive_path = Path(tmp_dir) / "goldberg.zip"
            downloaded = False

            for url in (GOLDBERG_URL, GOLDBERG_FALLBACK_URL):
                try:
                    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
                        resp = client.get(url)
                        if resp.status_code == 200:
                            archive_path.write_bytes(resp.content)
                            downloaded = True
                            break
                except Exception as e:
                    logger.warning(f"Failed to fetch Goldberg from {url}: {e}")

            if not downloaded or not archive_path.exists():
                raise FileNotFoundError(
                    "Goldberg Emulator otomatik olarak indirilemedi. Lütfen internet bağlantınızı kontrol edin."
                )

            try:
                if zipfile.is_zipfile(archive_path):
                    with zipfile.ZipFile(archive_path, "r") as z:
                        z.extractall(tmp_dir)
                elif tarfile.is_tarfile(archive_path):
                    with tarfile.open(archive_path, "r:*") as t:
                        t.extractall(tmp_dir)
            except Exception as e:
                raise RuntimeError(f"Goldberg arşivi açılamadı: {e}")

            # Search for steam_api binaries in extracted directory and copy them
            for root, _, files in os.walk(tmp_dir):
                for f in files:
                    f_lower = f.lower()
                    src_file = Path(root) / f
                    if f_lower == "steam_api.dll":
                        shutil.copy2(src_file, windows_dir / "steam_api.dll")
                    elif f_lower == "steam_api64.dll":
                        shutil.copy2(src_file, windows_dir / "steam_api64.dll")
                    elif f_lower == "libsteam_api.so":
                        shutil.copy2(src_file, linux_dir / "libsteam_api.so")
                    elif f_lower == "libsteam_api64.so":
                        shutil.copy2(src_file, linux_dir / "libsteam_api64.so")
    @staticmethod
    def apply_goldberg(app_id: str, game_dir: str):
        """Applies Goldberg emulator to the game directory."""
        goldberg_src = DRMManager.get_goldberg_src()
        game_path = Path(game_dir)
        
        # 1. Find all directories containing steam_api files
        steam_api_names = {
            "steam_api.dll", "steam_api64.dll",
            "libsteam_api.so", "libsteam_api64.so"
        }
        
        target_dirs = set()
        for root, dirs, files in os.walk(game_dir):
            if any(fname.lower() in steam_api_names for fname in files):
                target_dirs.add(root)
                
        if not target_dirs:
            # Maybe it's in a subfolder, or doesn't have steam DRM
            logging.warning(f"No steam_api files found in {game_dir}")
            
            # Still write steam_appid.txt in root just in case
            with open(game_path / "steam_appid.txt", "w") as f:
                f.write(str(app_id))
            return
            
        # 2. Process each directory
        for target_dir in target_dirs:
            DRMManager._apply_goldberg_to_single_dir(target_dir, str(app_id), goldberg_src)
            
    @staticmethod
    def _apply_goldberg_to_single_dir(target_dir: str, app_id: str, goldberg_src: Path):
        renamed_files = DRMManager._backup_steam_api_files(target_dir)
        DRMManager._copy_goldberg_matching_files(target_dir, goldberg_src, renamed_files)
        
        # Write appid
        with open(Path(target_dir) / "steam_appid.txt", "w") as f:
            f.write(app_id)
            
    @staticmethod
    def _backup_steam_api_files(directory: str) -> List[str]:
        renamed = []
        patterns = [
            "steam_api.dll", "steam_api64.dll",
            "libsteam_api.so", "libsteam_api64.so",
        ]
        for name in patterns:
            src = os.path.join(directory, name)
            if os.path.exists(src):
                dst = src + ".valve"
                if not os.path.exists(dst):
                    os.rename(src, dst)
                renamed.append(name)
        return renamed

    @staticmethod
    def _copy_goldberg_matching_files(target_dir: str, goldberg_src: Path, renamed_files: List[str]):
        for name in renamed_files:
            name_lower = name.lower()
            src = None
            if name_lower == "steam_api.dll":
                src = goldberg_src / "windows" / "steam_api.dll"
            elif name_lower == "steam_api64.dll":
                src = goldberg_src / "windows" / "steam_api64.dll"
            elif name_lower == "libsteam_api.so":
                src = goldberg_src / "linux" / "libsteam_api.so"
            elif name_lower == "libsteam_api64.so":
                src = goldberg_src / "linux" / "libsteam_api64.so"
                
            if src and src.exists():
                dest = os.path.join(target_dir, name)
                shutil.copy2(src, dest)
                
