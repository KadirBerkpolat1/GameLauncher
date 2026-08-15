import os
import shutil
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Callable

import httpx

from src.services.cloud_redirect import CloudRedirectManager
from src.services.drm_manager import DRMManager

logger = logging.getLogger(__name__)

SLS_DIR = Path.home() / ".local" / "share" / "SLSsteam"
FLATPAK_SLS_DIR = Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "SLSsteam"
CLOUDREDIRECT_DIR = Path.home() / ".local" / "share" / "CloudRedirect"


class PluginManagerError(Exception):
    """Base exception for PluginManager operations."""
    pass


class PluginManager:
    """
    Manages Steam modding tools and cloud services:
    - Headcrab / SLSsteam (Client pinning & license bypass)
    - CloudRedirect (Custom cloud save redirection)
    - Goldberg Emulator (Offline DRM emulation)
    """

    @staticmethod
    def get_status() -> Dict[str, Any]:
        """Returns the installation status of core tools."""
        sls_installed = (
            (SLS_DIR / "SLSsteam.so").exists() or 
            (SLS_DIR / "library-inject.so").exists() or
            (FLATPAK_SLS_DIR / "SLSsteam.so").exists()
        )
        cr_installed = CloudRedirectManager.is_installed()
        
        goldberg_installed = False
        try:
            gb_path = DRMManager.get_goldberg_src()
            goldberg_installed = gb_path.exists()
        except Exception:
            goldberg_installed = False

        return {
            "slssteam": sls_installed,
            "cloudredirect": cr_installed,
            "goldberg": goldberg_installed,
            "sls_dir": str(SLS_DIR),
            "cloudredirect_dir": str(CLOUDREDIRECT_DIR)
        }

    @classmethod
    async def install_headcrab(cls, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Runs the rootless headcrab.sh script to setup/pin SLSsteam."""
        def log(msg: str):
            logger.info(msg)
            if progress_callback:
                progress_callback(msg)

        root_dir = Path(__file__).resolve().parent.parent.parent
        headcrab_sh = root_dir / "headcrab.sh"

        if not headcrab_sh.exists():
            log(f"headcrab.sh not found at {headcrab_sh}")
            return False

        log("Running Headcrab installer (SLSsteam client pinning)...")
        headcrab_sh.chmod(0o755)

        proc = await asyncio.create_subprocess_exec(
            "bash", str(headcrab_sh),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").strip()
            if text:
                log(text)

        await proc.wait()
        if proc.returncode == 0:
            log("✓ Headcrab / SLSsteam setup completed successfully!")
            return True
        else:
            log(f"⚠ Headcrab completed with code: {proc.returncode}")
            return True
    @classmethod
    async def install_sls_moon(cls, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Downloads and installs slsteam-moon over existing SLSsteam installations."""
        import zipfile
        import tempfile
        
        def log(msg: str):
            logger.info(msg)
            if progress_callback:
                progress_callback(msg)

        log("Preparing to install Native Steam (Moon) Engine...")
        api_url = "https://api.github.com/repos/swwayps/slsteam-moon/releases/latest"
        headers = {
            "User-Agent": "NebulaLauncher/0.1.0",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(api_url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                assets = data.get("assets", [])
                
                # Find the regular slsteam-moon asset (not the lumen one, or grab whichever fits)
                dl_url = None
                for asset in assets:
                    name = asset.get("name", "").lower()
                    if "slsteam-moon-linux" in name and name.endswith(".zip"):
                        dl_url = asset.get("browser_download_url")
                        break
                
                if not dl_url:
                    # Fallback URL if GitHub API rate limits or format changes
                    dl_url = "https://github.com/swwayps/slsteam-moon/releases/download/v2.5/slsteam-moon-linux.zip"
                    log(f"Release asset not found, using fallback: {dl_url}")

                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_path = Path(tmp_dir)
                    zip_path = tmp_path / "slsteam-moon.zip"
                    
                    log(f"Downloading slsteam-moon from {dl_url}...")
                    dl_resp = await client.get(dl_url)
                    dl_resp.raise_for_status()
                    zip_path.write_bytes(dl_resp.content)
                    
                    log("Extracting slsteam-moon files...")
                    with zipfile.ZipFile(zip_path, "r") as z:
                        z.extractall(tmp_path)
                    
                    # Locate extracted files
                    extracted_bin = tmp_path / "bin"
                    if not extracted_bin.exists():
                        # Some releases might extract without a top-level dir
                        if (tmp_path / "SLSsteam.so").exists():
                            extracted_bin = tmp_path
                        else:
                            # Check subfolders
                            for sub in tmp_path.iterdir():
                                if sub.is_dir() and (sub / "bin").exists():
                                    extracted_bin = sub / "bin"
                                    break

                    if not (extracted_bin / "SLSsteam.so").exists():
                        raise Exception("SLSsteam.so not found in the downloaded archive.")

                    SLS_DIR.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(extracted_bin / "SLSsteam.so", SLS_DIR / "SLSsteam.so")
                    if (extracted_bin / "library-inject.so").exists():
                        shutil.copy2(extracted_bin / "library-inject.so", SLS_DIR / "library-inject.so")
                        
                    if FLATPAK_SLS_DIR.parent.exists():
                        FLATPAK_SLS_DIR.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(extracted_bin / "SLSsteam.so", FLATPAK_SLS_DIR / "SLSsteam.so")
                        if (extracted_bin / "library-inject.so").exists():
                            shutil.copy2(extracted_bin / "library-inject.so", FLATPAK_SLS_DIR / "library-inject.so")

                    log("✓ slsteam-moon successfully installed!")
                    return True
        except Exception as e:
            log(f"✗ Failed to install slsteam-moon: {e}")
            return False

    @classmethod
    async def install_cloudredirect(cls, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Installs the CloudRedirect 32-bit hook."""
        def log(msg: str):
            logger.info(msg)
            if progress_callback:
                progress_callback(msg)

        log("Installing CloudRedirect hook...")
        try:
            path = await CloudRedirectManager.ensure_installed()
            log(f"✓ CloudRedirect installed at {path}")
            return True
        except Exception as e:
            log(f"✗ Failed to install CloudRedirect: {e}")
            return False
