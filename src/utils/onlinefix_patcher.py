import os
import shutil
import configparser
from pathlib import Path
from src.utils.vdf_parser import LocalConfigManager

class OnlineFixPatcher:
    @staticmethod
    def apply_patch(app_id: str, game_dir: str):
        root_dir = Path(__file__).resolve().parent.parent.parent
        assets_dir = root_dir / "assets" / "onlinefix"
        legacy_dir = root_dir / "REPO_Fix_Repair_Steam_V5_Generic"

        # Check and rename legacy dir if it exists and assets_dir doesn't
        if not assets_dir.exists() and legacy_dir.exists():
            assets_dir.parent.mkdir(parents=True, exist_ok=True)
            # Use shutil.move to handle cross-device links just in case, though rename is usually fine here
            shutil.move(str(legacy_dir), str(assets_dir))

        if not assets_dir.exists():
            raise FileNotFoundError(f"Yama şablonu bulunamadı! Beklenen yol: {assets_dir}")

        # Copy files to game_dir
        for item in assets_dir.iterdir():
            dest = Path(game_dir) / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

        # Update OnlineFix.ini AppId
        ini_path = Path(game_dir) / "OnlineFix.ini"
        if ini_path.exists():
            config = configparser.ConfigParser()
            config.optionxform = str  # Preserve case
            
            try:
                config.read(ini_path, encoding='utf-8')
            except:
                config.read(ini_path, encoding='utf-8-sig')

            section_to_use = None
            if config.has_section("OnlineFix"):
                section_to_use = "OnlineFix"
            elif config.has_section("Main"):
                section_to_use = "Main"
            else:
                section_to_use = "OnlineFix"
                config.add_section(section_to_use)

            config.set(section_to_use, "AppId", str(app_id))
            
            with open(ini_path, 'w', encoding='utf-8') as configfile:
                config.write(configfile, space_around_delimiters=False)

        # Update launch options
        manager = LocalConfigManager()
        manager.update_launch_options(app_id)
