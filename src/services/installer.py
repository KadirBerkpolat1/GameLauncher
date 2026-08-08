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
    Downloads and runs slssteam_install.sh from the GameLauncher GitHub repo.
    The shell script handles: AceSLS/SLSsteam 7z download → extract → copy .so files.
    """
    INSTALL_SCRIPT_URL = (
        "https://raw.githubusercontent.com/KadirBerkpolat1/GameLauncher/main/slssteam_install.sh"
    )
    TEMP_SCRIPT = Path("/tmp/slssteam_install.sh")

    @classmethod
    async def _fetch_script(cls) -> None:
        """Downloads the install script from GitHub to a temp file."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                resp = await client.get(cls.INSTALL_SCRIPT_URL, timeout=15.0)
                resp.raise_for_status()
                cls.TEMP_SCRIPT.write_bytes(resp.content)
                cls.TEMP_SCRIPT.chmod(0o755)
            except Exception as e:
                raise InstallerError(f"Kurulum betiği indirilemedi: {e}")

    @classmethod
    async def update_slssteam(cls) -> str:
        if not shutil.which("7z") and not shutil.which("7za"):
            raise InstallerError(
                "Sistemde '7z' bulunamadı. Lütfen önce p7zip (veya 7zip) kurun.\n"
                "  Arch:   sudo pacman -S p7zip\n"
                "  Debian: sudo apt install p7zip-full"
            )

        await cls._fetch_script()

        proc = await asyncio.create_subprocess_exec(
            "bash", str(cls.TEMP_SCRIPT), "install",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode(errors="replace")

        if proc.returncode != 0:
            raise InstallerError(f"SLSsteam kurulumu başarısız:\n{output}")

        # Sürüm etiketini çıktıdan al, yoksa "latest" döndür
        for line in output.splitlines():
            if "installed successfully" in line:
                tag = line.split()[1] if len(line.split()) > 1 else "latest"
                return tag
        return "latest"

    @classmethod
    async def uninstall_slssteam(cls) -> None:
        await cls._fetch_script()

        proc = await asyncio.create_subprocess_exec(
            "bash", str(cls.TEMP_SCRIPT), "uninstall",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await proc.communicate()

        # Flatpak override'ı temizle (varsa)
        import subprocess
        subprocess.run(
            ["flatpak", "override", "--user",
             "--unset-env=LD_AUDIT", "--unset-env=SHARED_LIBRARY_GUARD",
             "com.valvesoftware.Steam"],
            stderr=subprocess.DEVNULL,
            check=False,
        )
