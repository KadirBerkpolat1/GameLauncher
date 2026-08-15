import os
import shutil
import subprocess
import tempfile
import configparser
from pathlib import Path
from src.utils.vdf_parser import LocalConfigManager

ARCHIVE_PASSWORD = "online-fix.me"


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

        OnlineFixPatcher._finalize(app_id, game_dir)

    @staticmethod
    def _find_extractor() -> str:
        """7z/7za/7zz veya bsdtar bulur; yoksa None."""
        for exe in ("7z", "7za", "7zz", "bsdtar"):
            if shutil.which(exe):
                return exe
        return None


    @staticmethod
    def apply_freetp_exe(exe_path: str, app_id: str, game_dir: str) -> str:
        """
        FreeTP'den inen Inno Setup .exe dosyasini innoextract ile acar.
        """
        if not shutil.which("innoextract"):
            raise FileNotFoundError("innoextract bulunamadi! Lutfen terminalden kurun: sudo pacman -S innoextract")
            
        tmp = tempfile.mkdtemp(prefix="freetp_")
        try:
            # -d tmp -e exe_path
            subprocess.run(["innoextract", "-s", "-d", tmp, exe_path], check=True, capture_output=True)
            
            # Inno Setup genelde {app} klasoru altina cikarir
            app_dir = Path(tmp) / "app"
            src_dir = app_dir if app_dir.exists() else Path(tmp)
            
            # Kopyala
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    src_file = Path(root) / file
                    rel_path = src_file.relative_to(src_dir)
                    dest_file = Path(game_dir) / rel_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dest_file)
                    
            OnlineFixPatcher._finalize(app_id, game_dir)
            return tmp
        except subprocess.CalledProcessError as e:
            shutil.rmtree(tmp, ignore_errors=True)
            raise RuntimeError(f"innoextract hatasi: {e.stderr.decode('utf-8', 'replace')}")

    @staticmethod
    def apply_patch_from_archive(rar_path: str, app_id: str, game_dir: str,
                                 password: str = ARCHIVE_PASSWORD) -> str:
        """
        Internetten inilen fix arşivini (rar/zip) şifresiyle açar ve oyun
        klasörüne uygular. OnlineFix.ini AppId güncellemesi ve launch
        options burada da yapılır.

        Returns: açılan geçici klasörün yolu (temizlik arayana bırakılır).
        """
        extractor = OnlineFixPatcher._find_extractor()
        if not extractor:
            raise FileNotFoundError("7z veya bsdtar bulunamadı! p7zip kurun.")

        rar_path = str(Path(rar_path).resolve())
        if not os.path.exists(rar_path):
            raise FileNotFoundError(f"Fix arşivi bulunamadı: {rar_path}")

        # Her iki taraf da rar/zip şifresi için benzer bayraklar kullanır.
        tmp = tempfile.mkdtemp(prefix="ofme_fix_")
        if extractor == "bsdtar":
            cmd = [extractor, "-xf", rar_path, "-C", tmp]
            if password:
                cmd.extend(["--passphrase", password])
        else:
            cmd = [extractor, "x", "-y", f"-o{tmp}", rar_path]
            if password:
                cmd.insert(2, f"-p{password}")

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode not in (0, 1):  # 7z: 1 = uyarılı başarı
            shutil.rmtree(tmp, ignore_errors=True)
            raise RuntimeError(
                f"Arşiv açılamadı (extractor={extractor}, rc={result.returncode}). "
                f"Stderr: {result.stderr.strip()[:400]}"
            )

        # Açılan içeriği oyun klasörüne kopyala (üst dizinler dahil).
        game_path = Path(game_dir)
        game_path.mkdir(parents=True, exist_ok=True)
        copied = 0
        for item in Path(tmp).iterdir():
            dest = game_path / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
            copied += 1

        if copied == 0:
            shutil.rmtree(tmp, ignore_errors=True)
            raise RuntimeError("Fix arşivi boş veya tanınamadı.")

        OnlineFixPatcher._finalize(app_id, game_dir)
        return tmp

    @staticmethod
    def _finalize(app_id: str, game_dir: str):
        """OnlineFix.ini AppId günceller + Steam launch options ayarlar."""
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
