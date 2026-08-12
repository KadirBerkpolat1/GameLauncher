import os
import shutil
import logging
from pathlib import Path
from typing import List, Set

class DRMManager:
    """Manages DRM removal using Goldberg Emulator."""
    
    @staticmethod
    def get_goldberg_src() -> Path:
        """Ensures Goldberg binaries exist and returns their path."""
        root_dir = Path(__file__).resolve().parent.parent.parent
        assets_dir = root_dir / "assets" / "goldberg"
        
        if not assets_dir.exists():
            # Try to copy from ACCELA's bundle if available
            accela_gb = Path.home() / ".local/share/ACCELA/squashfs-root/deps/Goldberg"
            if accela_gb.exists():
                assets_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(accela_gb, assets_dir)
            else:
                raise FileNotFoundError(
                    "Goldberg Emulator dosyaları bulunamadı!\n"
                    f"Lütfen '{assets_dir}' dizinine Goldberg dosyalarını ekleyin."
                )
        return assets_dir

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
                
