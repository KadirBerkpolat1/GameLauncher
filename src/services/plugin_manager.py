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
    def _find_terminal() -> Optional[str]:
        """Find a usable terminal emulator for interactive installs."""
        import shutil as _shutil
        for t in ("konsole", "gnome-terminal", "xfce4-terminal", "mate-terminal",
                  "lxterminal", "qterminal", "alacritty", "foot", "kitty", "tilix",
                  "xterm", "x-terminal-emulator"):
            if _shutil.which(t):
                return t
        return None

    @staticmethod
    def _terminal_launch_cmd(term: str, inner: str) -> Optional[list]:
        """Build the argv that opens `term` running the shell command `inner`."""
        if term == "konsole":
            return ["konsole", "--hold", "-e", "bash", "-c", inner]
        if term == "gnome-terminal":
            return ["gnome-terminal", "--", "bash", "-c", inner]
        if term == "xfce4-terminal":
            return ["xfce4-terminal", "-H", "-x", "bash", "-c", inner]
        if term == "mate-terminal":
            return ["mate-terminal", "--", "bash", "-c", inner]
        if term in ("lxterminal", "qterminal", "tilix"):
            return [term, "-e", "bash", "-c", inner]
        if term in ("alacritty", "foot", "kitty"):
            return [term, "-e", "bash", "-c", inner]
        if term == "xterm":
            return ["xterm", "-hold", "-e", "bash", "-c", inner]
        if term == "x-terminal-emulator":
            return ["x-terminal-emulator", "-e", "bash", "-c", inner]
        return None

    @classmethod
    async def _run_setup_in_terminal(cls, workdir: Path, mode: str, marker: Path) -> bool:
        """Open a visible terminal running `bash setup.sh <mode>` in workdir.
        The command writes its exit code to `marker`; returns True if a terminal
        was successfully launched (caller then polls the marker)."""
        import shlex
        term = cls._find_terminal()
        if not term:
            return False
        marker.parent.mkdir(parents=True, exist_ok=True)
        try:
            marker.unlink(missing_ok=True)
        except OSError:
            pass
        inner = (
            f"cd {shlex.quote(str(workdir))} && bash setup.sh {mode}; rc=$?; "
            f"printf '%s' \"$rc\" > {shlex.quote(str(marker))}; echo; "
            f"echo 'slsteam-moon {mode} finished (exit code: $rc). You can close this window.'; "
            "read -r _"
        )
        cmd = cls._terminal_launch_cmd(term, inner)
        if not cmd:
            return False
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
            return True
        except Exception:
            return False

    @staticmethod
    async def _wait_for_marker(marker: Path, timeout: float = 900.0) -> Optional[int]:
        """Poll until the marker file contains the setup.sh exit code."""
        import time as _time
        deadline = _time.monotonic() + timeout
        while _time.monotonic() < deadline:
            if marker.exists():
                try:
                    text = marker.read_text().strip()
                    if text:
                        return int(text)
                except Exception:
                    return None
            await asyncio.sleep(2)
        return None

    @classmethod
    async def _run_setup_noninteractive(cls, workdir: Path, mode: str) -> tuple[bool, str]:
        """Fallback when no terminal emulator exists: run setup.sh in the
        background with sudo denied (user desktop coverage only)."""
        env = os.environ.copy()
        env["SLSM_SUDO_DENIED"] = "1"
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                ["bash", "setup.sh", mode],
                cwd=str(workdir),
                env=env,
                capture_output=True,
                text=True,
                timeout=600,
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
                        # Extract to a persistent temp dir: a visible terminal
                        # may still be running setup.sh from here after this
                        # function returns, so it must survive the async task.
                        import tempfile
                        tmpdir = tempfile.mkdtemp(prefix="slsteam-moon-install-")
                        try:
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
                                # plain file copy cannot do). Runs in a visible
                                # terminal so the user can enter the sudo
                                # password right there.
                                marker = extracted / "install.exit"
                                launched = await cls._run_setup_in_terminal(extracted, "install", marker)
                                if launched:
                                    log("A terminal has been opened - follow the installer and enter your sudo password there.")
                                    log("Waiting for the installer to finish...")
                                    rc = await cls._wait_for_marker(marker)
                                    if rc is None:
                                        log("✗ Timed out waiting for setup.sh (terminal may have been closed early)")
                                        return False
                                    if rc != 0:
                                        log(f"✗ setup.sh exited with code {rc} - check the terminal output")
                                        return False
                                    log("setup.sh completed successfully")
                                else:
                                    log("No terminal emulator found; running setup.sh non-interactively (user desktop coverage only).")
                                    ok, output = await cls._run_setup_noninteractive(extracted, "install")
                                    for line in output.splitlines():
                                        log(line)
                                    if not ok:
                                        log("✗ Non-interactive setup.sh failed")
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
                        finally:
                            # Remove the extracted release only once setup.sh
                            # finished (marker written); if the user is still
                            # running the installer in a terminal, leave the dir
                            # for the OS temp cleaner.
                            try:
                                if extracted is not None and (extracted / "install.exit").exists():
                                    shutil.rmtree(tmpdir, ignore_errors=True)
                            except Exception:
                                pass

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
                marker = SLS_DIR / "uninstall.exit"
                launched = await cls._run_setup_in_terminal(SLS_DIR, "uninstall", marker)
                if launched:
                    rc = await cls._wait_for_marker(marker, timeout=600)
                    if rc is None:
                        logger.warning("Timed out waiting for setup.sh uninstall")
                    elif rc != 0:
                        logger.warning(f"setup.sh uninstall exited {rc}")
                else:
                    ok, output = await cls._run_setup_noninteractive(SLS_DIR, "uninstall")
                    if not ok:
                        logger.warning(f"Non-interactive uninstall failed: {output[:500]}")
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