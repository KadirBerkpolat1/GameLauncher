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
                if "linux-x64.zip" in asset["name"].lower():
                    download_url = asset["browser_download_url"]
                    break
            
            # Fallback to any zip if linux-x64 is not found
            if not download_url:
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

            # Look for linux standalone binary first, then fallback to dll
            bin_path = cls.INSTALL_DIR / "DepotDownloader"
            if not bin_path.exists():
                for path in cls.INSTALL_DIR.rglob("DepotDownloader"):
                    bin_path = path
                    break

            if bin_path.exists() and not bin_path.is_dir():
                # Make it executable
                bin_path.chmod(0o755)
                found_path = bin_path
            else:
                # Fallback to .dll
                dll_path = cls.INSTALL_DIR / "DepotDownloader.dll"
                if not dll_path.exists():
                    for path in cls.INSTALL_DIR.rglob("DepotDownloader.dll"):
                        dll_path = path
                        break
                found_path = dll_path if dll_path.exists() else None

            if found_path:
                from src.config.settings import SettingsManager
                SettingsManager.set("depotdownloadermod_path", str(found_path))
            else:
                raise InstallerError("DepotDownloader executable/dll not found after extraction.")

            return tag

    @classmethod
    async def uninstall_ddmod(cls) -> None:
        if cls.INSTALL_DIR.exists():
            shutil.rmtree(cls.INSTALL_DIR)
        from src.config.settings import SettingsManager
        SettingsManager.set("depotdownloadermod_path", "")

class SLSsteamInstaller:
    """
    Downloads and runs h3adcr-b from the Deadboy666/h3adcr-b GitHub repo.
    """
    @classmethod
    async def update_slssteam(cls) -> str:
        cmd = 'curl -fsSL https://raw.githubusercontent.com/Deadboy666/h3adcr-b/refs/heads/main/headcrab.sh | bash'
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode(errors="replace")

        if proc.returncode != 0:
            raise InstallerError(f"SLSsteam kurulumu (headcrab) başarısız:\n{output}")

        return "latest (h3adcr-b)"

    @classmethod
    async def uninstall_slssteam(cls) -> None:
        # headcrab.sh installs to ~/.local/share/SLSsteam or flatpak path.
        # We manually remove it as headcrab.sh does not provide an uninstall command.
        sls_paths = [
            Path.home() / ".local" / "share" / "SLSsteam",
            Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "SLSsteam",
            Path.home() / ".config" / "SLSsteam",
            Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".config" / "SLSsteam"
        ]
        for p in sls_paths:
            if p.exists() and p.is_dir():
                shutil.rmtree(p, ignore_errors=True)

        # Clean Flatpak override
        import subprocess
        subprocess.run(
            ["flatpak", "override", "--user",
             "--unset-env=LD_AUDIT", "--unset-env=SHARED_LIBRARY_GUARD",
             "com.valvesoftware.Steam"],
            stderr=subprocess.DEVNULL,
            check=False,
        )
