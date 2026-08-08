import asyncio
import httpx
import os
import shutil
import tarfile
import zipfile
import io
from pathlib import Path
from typing import Dict, Any

class InstallerError(Exception):
    pass

class DDModInstaller:
    """Handles downloading and setting up DepotDownloader from SteamRE."""
    GITHUB_API_URL = "https://api.github.com/repos/SteamRE/DepotDownloader/releases/latest"
    INSTALL_DIR = Path.home() / ".config" / "GameLauncher" / "DDMod"

    @classmethod
    async def update_ddmod(cls) -> str:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(cls.GITHUB_API_URL, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            tag = data.get("tag_name", "unknown")
            assets = data.get("assets", [])

            download_url = None
            for asset in assets:
                if asset["name"].endswith(".zip"):
                    download_url = asset["browser_download_url"]
                    break

            if not download_url:
                raise InstallerError("No ZIP asset found in latest DepotDownloader release.")

            zip_resp = await client.get(download_url, timeout=30.0)
            zip_resp.raise_for_status()

            if cls.INSTALL_DIR.exists():
                shutil.rmtree(cls.INSTALL_DIR)
            cls.INSTALL_DIR.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as z:
                z.extractall(cls.INSTALL_DIR)

            dll_path = cls.INSTALL_DIR / "DepotDownloader.dll"
            if not dll_path.exists():
                # Check subdirectories if wrapped in a folder
                for path in cls.INSTALL_DIR.rglob("DepotDownloader.dll"):
                    dll_path = path
                    break

            if dll_path.exists():
                from src.config.settings import SettingsManager
                SettingsManager.set("depotdownloadermod_path", str(dll_path))
            else:
                raise InstallerError("DepotDownloader.dll not found after extraction.")

            return tag

    @classmethod
    async def uninstall_ddmod(cls) -> None:
        if cls.INSTALL_DIR.exists():
            shutil.rmtree(cls.INSTALL_DIR)
        from src.config.settings import SettingsManager
        SettingsManager.set("depotdownloadermod_path", "")

class SLSsteamInstaller:
    """
    Handles downloading, building, and installing SLSsteam directly from GitHub.
    """
    GITHUB_API_URL = "https://api.github.com/repos/AceSLS/SLSsteam/releases/latest"
    TEMP_DIR = Path("/tmp/slssteam_build")

    @classmethod
    async def get_latest_version_info(cls) -> Dict[str, Any]:
        """Fetches the latest release info from GitHub."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(cls.GITHUB_API_URL, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                return data
            except Exception as e:
                raise InstallerError(f"Failed to fetch latest SLSsteam release: {e}")

    @classmethod
    async def update_slssteam(cls) -> str:
        # 7z kontrolü
        if not shutil.which("7z") and not shutil.which("7za"):
            raise InstallerError("Sistemde '7z' bulunamadı. Lütfen önce p7zip (veya 7zip) kurun.")

        info = await cls.get_latest_version_info()
        
        download_url = None
        for asset in info.get("assets", []):
            if asset["name"] == "SLSsteam-Any.7z":
                download_url = asset["browser_download_url"]
                break
                
        if not download_url:
            raise InstallerError("GitHub release içinde 'SLSsteam-Any.7z' bulunamadı.")

        if cls.TEMP_DIR.exists():
            shutil.rmtree(cls.TEMP_DIR)
        cls.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        
        archive_path = cls.TEMP_DIR / "SLSsteam-Any.7z"
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                resp = await client.get(download_url, timeout=60.0)
                resp.raise_for_status()
                with open(archive_path, "wb") as f:
                    f.write(resp.content)
            except Exception as e:
                raise InstallerError(f"Dosya indirilemedi: {e}")

        # 7z ile çıkartma
        extract_proc = await asyncio.create_subprocess_shell(
            f"7z x {archive_path} -y -o{cls.TEMP_DIR}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await extract_proc.communicate()
        if extract_proc.returncode != 0:
            raise InstallerError("7z çıkartma işlemi başarısız oldu.")

        # Kurulum Betiğini Çalıştır
        install_proc = await asyncio.create_subprocess_shell(
            "bash setup.sh install",
            cwd=str(cls.TEMP_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await install_proc.communicate()
        if install_proc.returncode != 0:
            raise InstallerError(f"Kurulum başarısız:\n{stderr.decode()}")
            
        # Flatpak kurulumunu da dene (varsa kurar, yoksa sessizce geçer)
        flatpak_proc = await asyncio.create_subprocess_shell(
            "bash setup.sh flatpak-install",
            cwd=str(cls.TEMP_DIR),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await flatpak_proc.communicate()

        # Temizlik
        shutil.rmtree(cls.TEMP_DIR)

        return info["tag_name"]

    @classmethod
    async def uninstall_slssteam(cls) -> None:
        home = Path.home()
        paths_to_remove = [
            home / ".local/share/SLSsteam",
            home / ".local/share/applications/steam.desktop",
            home / ".local/share/applications/steam-native.desktop",
            home / ".config/fish/SLSsteam.fish",
            home / ".config/SLSsteam"
        ]
        
        for p in paths_to_remove:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.is_file():
                p.unlink(missing_ok=True)
                
        import subprocess
        subprocess.run(
            ["flatpak", "override", "--user", "--unset-env=LD_AUDIT", "--unset-env=SHARED_LIBRARY_GUARD", "com.valvesoftware.Steam"],
            stderr=subprocess.DEVNULL
        )
        
        flatpak_slsdir = home / ".var/app/com.valvesoftware.Steam/.local/share/SLSsteam"
        if flatpak_slsdir.exists():
            shutil.rmtree(flatpak_slsdir, ignore_errors=True)

