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
            so_exists = (d / "bin" / "SLSsteam.so").exists() or (d / "SLSsteam.so").exists()
            wrapper_exists = (d / "path" / "steam").exists()
            if so_exists and wrapper_exists:
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

    @staticmethod
    def _write_askpass() -> Optional[Path]:
        """Write a GUI askpass helper that shows the themed SudoPasswordDialog.
        Runs with the app's own interpreter so PySide6 and the app theme are
        always available."""
        import sys
        try:
            SLS_DIR.mkdir(parents=True, exist_ok=True)
            askpass = SLS_DIR / "askpass.py"
            app_root = Path(__file__).parent.parent.parent
            script = (
                f"#!{sys.executable}\n"
                "import sys\n"
                f"sys.path.insert(0, {str(app_root)!r})\n"
                "from PySide6.QtWidgets import QApplication, QDialog\n"
                "from src.ui.styles import DARK_THEME\n"
                "from src.ui.sudo_dialog import SudoPasswordDialog\n"
                "app = QApplication(sys.argv)\n"
                "app.setStyleSheet(DARK_THEME)\n"
                "dlg = SudoPasswordDialog(\n"
                "    prompt='Administrator authentication',\n"
                "    detail='slsteam-moon needs root access to install the Steam "
                "launcher shim. Enter your sudo password.',\n"
                ")\n"
                "if dlg.exec() == QDialog.DialogCode.Accepted:\n"
                "    print(dlg.password)\n"
                "    sys.exit(0)\n"
                "sys.exit(1)\n"
            )
            askpass.write_text(script)
            askpass.chmod(0o755)
            return askpass
        except Exception:
            return None

    @classmethod
    def _setup_env(cls) -> Dict[str, str]:
        """Build env for setup.sh. Uses sudo without prompting when credentials
        are already cached (sudo -n); otherwise wires a themed GUI askpass
        helper so the user is prompted for the sudo password in-app. If no
        askpass helper can be created, system launcher interception is skipped
        and only user desktop coverage applies."""
        env = os.environ.copy()
        try:
            primed = subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=10).returncode == 0
        except Exception:
            primed = False
        if primed:
            env["SLSM_SUDO_PRIMED"] = "1"
        else:
            askpass = cls._write_askpass()
            if askpass is not None:
                env["SUDO_ASKPASS"] = str(askpass)
            else:
                env["SLSM_SUDO_DENIED"] = "1"
        return env

    @classmethod
    async def _run_setup(cls, workdir: Path, mode: str) -> tuple[bool, str]:
        """Run `bash setup.sh <mode>` in workdir. The sudo password is asked
        via the themed GUI dialog when credentials are not cached."""
        env = cls._setup_env()
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                ["bash", "setup.sh", mode],
                cwd=str(workdir),
                env=env,
                capture_output=True,
                text=True,
                timeout=900,
            )
            output = (proc.stdout or "") + (proc.stderr or "")
            return proc.returncode == 0, output
        except Exception as e:
            return False, str(e)

    @classmethod
    async def install_slsteam_moon(cls, progress_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Downloads and installs slsteam-moon release by running its official
        setup.sh: installs libs, creates the Steam wrapper
        (~/.local/share/SLSsteam/path/steam) and patches desktop entries so
        Steam launches through the injection wrapper.
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
                        # Extract to a temp dir for the setup run
                        import tempfile
                        with tempfile.TemporaryDirectory() as tmpdir:
                            zf.extractall(tmpdir)
                            # Find extracted folder (slsteam-moon-<version>-lumen/)
                            extracted = None
                            for item in Path(tmpdir).iterdir():
                                if item.is_dir() and item.name.startswith("slsteam-moon-"):
                                    extracted = item
                                    break
                            if not extracted:
                                log("Extracted release folder not found")
                                return False

                            setup_script = extracted / "setup.sh"
                            if setup_script.exists():
                                # Official installer: creates the wrapper and
                                # patches desktop entries (the critical part a
                                # plain file copy cannot do). The sudo password
                                # is requested via the themed GUI dialog.
                                log("Running slsteam-moon setup.sh (wrapper + desktop coverage)...")
                                if cls._write_askpass() is not None:
                                    log("If prompted, enter your sudo password to intercept the Steam launcher.")
                                ok, output = await cls._run_setup(extracted, "install")
                                for line in output.splitlines():
                                    log(line)
                                if not ok:
                                    log("✗ setup.sh failed - see output above")
                                    return False
                                # Keep setup.sh (and its tools libs) for later uninstall
                                shutil.copy2(setup_script, SLS_DIR / "setup.sh")
                                (SLS_DIR / "setup.sh").chmod(0o755)
                                tools_src = extracted / "tools"
                                if tools_src.exists():
                                    shutil.copytree(tools_src, SLS_DIR / "tools", dirs_exist_ok=True)
                                # Mirror binaries to flatpak location as a best-effort copy
                                for sub in ("bin", "res", "tools"):
                                    src = SLS_DIR / sub
                                    if src.exists():
                                        shutil.copytree(src, FLATPAK_SLS_DIR / sub, dirs_exist_ok=True)
                                for so_file in (SLS_DIR / "bin" / "SLSsteam.so", SLS_DIR / "bin" / "library-inject.so",
                                                SLS_DIR / "SLSsteam.so", SLS_DIR / "library-inject.so"):
                                    if so_file.exists():
                                        so_file.chmod(0o755)
                                log(f"✓ slsteam-moon {version} installed (wrapper + desktop coverage active)")
                                return True

                            # Fallback: release without setup.sh - plain file copy only
                            log("setup.sh not found in release; doing plain file install (no desktop coverage)")
                            bin_src = extracted / "bin"
                            res_src = extracted / "res"
                            tools_src = extracted / "tools"

                            if bin_src.exists():
                                shutil.copytree(bin_src, SLS_DIR / "bin", dirs_exist_ok=True)
                                shutil.copytree(bin_src, FLATPAK_SLS_DIR / "bin", dirs_exist_ok=True)
                            if res_src.exists():
                                shutil.copytree(res_src, SLS_DIR / "res", dirs_exist_ok=True)
                                shutil.copytree(res_src, FLATPAK_SLS_DIR / "res", dirs_exist_ok=True)
                            if tools_src.exists():
                                shutil.copytree(tools_src, SLS_DIR / "tools", dirs_exist_ok=True)
                                shutil.copytree(tools_src, FLATPAK_SLS_DIR / "tools", dirs_exist_ok=True)

                            for so_file in (SLS_DIR / "bin" / "SLSsteam.so", SLS_DIR / "bin" / "library-inject.so"):
                                if so_file.exists():
                                    so_file.chmod(0o755)

                            log(f"✓ slsteam-moon {version} files installed to {SLS_DIR}")
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
        """Removes slsteam-moon installation and restores desktop entries."""
        try:
            setup_script = SLS_DIR / "setup.sh"
            if setup_script.exists():
                if cls._write_askpass() is not None:
                    logger.info("If prompted, enter your sudo password to restore the Steam launcher.")
                ok, output = await cls._run_setup(SLS_DIR, "uninstall")
                if not ok:
                    logger.warning(f"setup.sh uninstall failed: {output[:500]}")
            else:
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