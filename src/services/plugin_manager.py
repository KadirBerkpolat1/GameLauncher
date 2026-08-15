import os
import shutil
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Callable

import httpx

from src.config.settings import SettingsManager

logger = logging.getLogger(__name__)

# Target directories
SLS_DIR = Path.home() / ".local" / "share" / "SLSsteam"
FLATPAK_SLS_DIR = Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "SLSsteam"
LUMEN_DIR = Path.home() / ".local" / "share" / "Lumen"
PLUGINS_DIR = Path.home() / ".local" / "share" / "Steam" / "plugins"  # for lumen binary


class PluginManagerError(Exception):
    """Base exception for PluginManager operations."""
    pass


class PluginManager:
    """
    Manages modern Steam modding stack:
    - slsteam-moon: SLSsteam.so + Lumen + Steamless + SteamStub bypass (all-in-one release)
    - lumen: Standalone Steam overlay/menu integration (optional, for Steam Deck-like UI)
    """

    # GitHub release URLs
    SLSTEAM_MOON_REPO = "swwayps/slsteam-moon"
    LUMEN_REPO = "swwayps/lumen"
    @staticmethod
    def get_status() -> Dict[str, Any]:
        """Returns the installation status of slsteam-moon, lumen, and luatools."""
        sls_installed = False
        sls_dir = ""
        for d in (SLS_DIR, FLATPAK_SLS_DIR):
            if (d / "bin" / "SLSsteam.so").exists() or (d / "SLSsteam.so").exists():
                sls_installed = True
                sls_dir = str(d)
                break

        lumen_installed = (LUMEN_DIR / "lumen").exists() or (PLUGINS_DIR / "lumen").exists()
        
        # Check for LuaTools plugin (we don't install it, but detect if present)
        luatools_installed = (LUMEN_DIR / "lua" / "luatools").exists()

        return {
            "slsteam_moon": sls_installed,
            "slsteam_moon_dir": sls_dir,
            "lumen": lumen_installed,
            "lumen_dir": str(LUMEN_DIR) if (LUMEN_DIR / "lumen").exists() else str(PLUGINS_DIR),
            "luatools": luatools_installed,
            "luatools_dir": str(LUMEN_DIR / "lua" / "luatools") if luatools_installed else "",
        }

    @classmethod
    async def install_slsteam_moon(cls, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Downloads and installs slsteam-moon release.
        This REPLACES any existing Headcrab/SLSsteam installation.
        Includes: SLSsteam.so, library-inject.so, Lumen lua scripts, Steamless, SteamStub bypass, config.yaml
        Does NOT install LuaTools plugin - we use Lumen with our custom lua overlay instead.
        """
        def log(msg: str):
            logger.info(msg)
            if progress_callback:
                progress_callback(msg)

        try:
            log("Fetching latest slsteam-moon release...")
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                # Get latest release
                resp = await client.get(f"https://api.github.com/repos/{cls.SLSTEAM_MOON_REPO}/releases/latest")
                resp.raise_for_status()
                release = resp.json()

                # Find the linux-lumen asset
                asset_url = None
                version = release.get("tag_name", "unknown")
                for asset in release.get("assets", []):
                    name = asset.get("name", "")
                    if name.startswith("slsteam-moon-linux-") and name.endswith("-lumen.zip"):
                        asset_url = asset.get("browser_download_url")
                        break

                if not asset_url:
                    log(f"No linux-lumen asset found in release {version}")
                    return False

                log(f"Downloading slsteam-moon {version}...")
                # Remove old installations
                for d in (SLS_DIR, FLATPAK_SLS_DIR):
                    if d.exists():
                        shutil.rmtree(d, ignore_errors=True)

                # Create target dirs
                SLS_DIR.mkdir(parents=True, exist_ok=True)
                FLATPAK_SLS_DIR.mkdir(parents=True, exist_ok=True)

                # Download and extract
                async with client.stream("GET", asset_url, timeout=120.0) as resp:
                    resp.raise_for_status()
                    import tempfile
                    import zipfile
                    import io

                    zip_data = io.BytesIO()
                    async for chunk in resp.aiter_bytes(8192):
                        zip_data.write(chunk)
                    zip_data.seek(0)

                    with zipfile.ZipFile(zip_data, 'r') as zf:
                        # Extract to temp first
                        with tempfile.TemporaryDirectory() as tmpdir:
                            zf.extractall(tmpdir)
                            # Find extracted folder (slsteam-moon-<version>-lumen/)
                            extracted = Path(tmpdir)
                            for item in extracted.iterdir():
                                if item.is_dir() and item.name.startswith("slsteam-moon-"):
                                    # Copy bin/ and res/ to SLS_DIR
                                    bin_src = item / "bin"
                                    res_src = item / "res"
                                    tools_src = item / "tools"

                                    if bin_src.exists():
                                        shutil.copytree(bin_src, SLS_DIR / "bin", dirs_exist_ok=True)
                                        shutil.copytree(bin_src, FLATPAK_SLS_DIR / "bin", dirs_exist_ok=True)
                                    if res_src.exists():
                                        shutil.copytree(res_src, SLS_DIR / "res", dirs_exist_ok=True)
                                        shutil.copytree(res_src, FLATPAK_SLS_DIR / "res", dirs_exist_ok=True)
                                    if tools_src.exists():
                                        shutil.copytree(tools_src, SLS_DIR / "tools", dirs_exist_ok=True)
                                        shutil.copytree(tools_src, FLATPAK_SLS_DIR / "tools", dirs_exist_ok=True)
                                    break

                # Make binaries executable
                for so_file in (SLS_DIR / "bin" / "SLSsteam.so", SLS_DIR / "bin" / "library-inject.so"):
                    if so_file.exists():
                        so_file.chmod(0o755)

                log(f"✓ slsteam-moon {version} installed to {SLS_DIR}")
                return True

        except Exception as e:
            log(f"✗ slsteam-moon installation failed: {e}")
            return False

    @classmethod
    async def install_lumen(cls, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Downloads and installs lumen binary + lua scripts.
        Installs to ~/.local/share/Lumen/ and symlinks to Steam/plugins/
        """
        def log(msg: str):
            logger.info(msg)
            if progress_callback:
                progress_callback(msg)

        try:
            log("Fetching latest lumen release...")
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(f"https://api.github.com/repos/{cls.LUMEN_REPO}/releases/latest")
                resp.raise_for_status()
                release = resp.json()

                asset_url = None
                version = release.get("tag_name", "unknown")
                for asset in release.get("assets", []):
                    name = asset.get("name", "")
                    if name.startswith("lumen-linux") and name.endswith(".zip"):
                        asset_url = asset.get("browser_download_url")
                        break

                if not asset_url:
                    log(f"No linux asset found in lumen release {version}")
                    return False

                log(f"Downloading lumen {version}...")
                LUMEN_DIR.mkdir(parents=True, exist_ok=True)
                PLUGINS_DIR.mkdir(parents=True, exist_ok=True)

                async with client.stream("GET", asset_url, timeout=120.0) as resp:
                    resp.raise_for_status()
                    import tempfile
                    import zipfile
                    import io

                    zip_data = io.BytesIO()
                    async for chunk in resp.aiter_bytes(8192):
                        zip_data.write(chunk)
                    zip_data.seek(0)

                    with zipfile.ZipFile(zip_data, 'r') as zf:
                        with tempfile.TemporaryDirectory() as tmpdir:
                            zf.extractall(tmpdir)
                            extracted = Path(tmpdir)
                            # lumen binary
                            lumen_bin = extracted / "lumen"
                            if lumen_bin.exists():
                                dest_bin = LUMEN_DIR / "lumen"
                                shutil.copy2(lumen_bin, dest_bin)
                                dest_bin.chmod(0o755)
                                # Symlink to Steam/plugins/
                                plugin_link = PLUGINS_DIR / "lumen"
                                if plugin_link.exists() or plugin_link.is_symlink():
                                    plugin_link.unlink()
                                plugin_link.symlink_to(dest_bin)
                                log(f"✓ lumen binary installed to {dest_bin}")
                            # lua/ folder
                            lua_src = extracted / "lua"
                            if lua_src.exists():
                                shutil.copytree(lua_src, LUMEN_DIR / "lua", dirs_exist_ok=True)
                                log(f"✓ lumen lua scripts installed to {LUMEN_DIR}/lua")
                            
                            # Overlay Nebula custom lua files
                            await cls._overlay_nebula_lumen_custom(LUMEN_DIR, log)

                log(f"✓ lumen {version} installed")
                return True
        except Exception as e:
            log(f"✗ lumen installation failed: {e}")
            return False

    @classmethod
    async def _overlay_nebula_lumen_custom(cls, lumen_dir: Path, log_callback) -> None:
        """Overlay Nebula custom Lua files onto installed Lumen."""
        import shutil
        from pathlib import Path
        
        custom_dir = Path(__file__).parent.parent / "lumen_custom"
        if not custom_dir.exists():
            log_callback(f"  Nebula custom lua not found at {custom_dir}, skipping overlay")
            return
        
        try:
            # Copy custom fixesmenu.lua
            fixesmenu_src = custom_dir / "fixesmenu.lua"
            if fixesmenu_src.exists():
                shutil.copy2(fixesmenu_src, lumen_dir / "lua" / "fixesmenu.lua")
                log_callback(f"  ✓ Overlayed fixesmenu.lua")
            
            # Copy custom slsmenu.lua
            slsmenu_src = custom_dir / "slsmenu.lua"
            if slsmenu_src.exists():
                shutil.copy2(slsmenu_src, lumen_dir / "lua" / "slsmenu.lua")
                log_callback(f"  ✓ Overlayed slsmenu.lua")
            
            # Copy custom menu styles
            menu_custom_dir = custom_dir / "menu"
            if menu_custom_dir.exists():
                target_menu_dir = lumen_dir / "lua" / "menu"
                target_menu_dir.mkdir(parents=True, exist_ok=True)
                for file in menu_custom_dir.glob("*.lua"):
                    shutil.copy2(file, target_menu_dir / file.name)
                    log_callback(f"  ✓ Overlayed menu/{file.name}")
            
            log_callback(f"  ✓ Nebula Lumen customization applied")
            
        except Exception as e:
            log_callback(f"  ✗ Failed to overlay Nebula custom lua: {e}")

    @classmethod
    async def uninstall_slsteam_moon(cls) -> bool:
        """Removes slsteam-moon installation."""
        try:
            for d in (SLS_DIR, FLATPAK_SLS_DIR):
                if d.exists():
                    shutil.rmtree(d, ignore_errors=True)
            # Clean Flatpak override
            subprocess.run(
                ["flatpak", "override", "--user",
                 "--unset-env=LD_AUDIT", "--unset-env=SHARED_LIBRARY_GUARD",
                 "com.valvesoftware.Steam"],
                stderr=subprocess.DEVNULL, check=False
            )
            logger.info("slsteam-moon uninstalled")
            return True
        except Exception as e:
            logger.error(f"Uninstall failed: {e}")
            return False

    @classmethod
    async def uninstall_lumen(cls) -> bool:
        """Removes lumen installation."""
        try:
            for d in (LUMEN_DIR, PLUGINS_DIR):
                if d.exists():
                    shutil.rmtree(d, ignore_errors=True)
            logger.info("lumen uninstalled")
            return True
        except Exception as e:
            logger.error(f"Lumen uninstall failed: {e}")
            return False