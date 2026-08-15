import asyncio
import os
import re
import tempfile
import time
from pathlib import Path
from src.config.settings import SettingsManager
from src.utils.manifest import parse_manifest

class DownloadTask:
    """
    Manages a multi-depot download session for a single game via the modded
    DepotDownloaderMod (Accela-style flow). Downloads anonymously using
    -depotkeys (decryption keys) and -manifestfile (manifest loaded from disk),
    straight into the Steam library at steamapps/common/<installdir>.
    Supports pause, resume, and cancel by controlling the underlying subprocess.
    """
    _support_cache: dict = {}

    def __init__(self, game_data: dict, title: str):
        self.app_id = game_data.get("appid")
        self.title = title
        self.game_data = game_data
        self.depots = game_data.get("depots", {})
        self._ordered_depot_ids = sorted(self.depots, key=lambda d: int(d))
        self.is_paused = False
        self.is_canceled = False
        self.current_process = None
        self._speed_state = None
        self._current_depot_idx = 0
        self.download_dir = None
        self.steamapps_dir = None
        self.used_fallback = False


    def _resolve_target_dir(self) -> str:
        """Picks the Steam library target: <library>/steamapps/common/<installdir>."""
        from src.utils.paths import get_steam_libraries

        installdir = self.game_data.get("installdir")
        libraries = get_steam_libraries()

        if libraries and installdir:
            target_lib = self.game_data.get("target_library")
            preferred_lib = SettingsManager.get("preferred_steam_library", "")

            chosen_library = None
            if target_lib and target_lib in libraries:
                chosen_library = target_lib
            elif preferred_lib and preferred_lib in libraries:
                chosen_library = preferred_lib
            else:
                chosen_library = libraries[0]

            self.steamapps_dir = os.path.join(chosen_library, "steamapps")
            target = os.path.join(
                self.steamapps_dir, "common", installdir
            )
            os.makedirs(target, exist_ok=True)
            return target

        # Fallback: plain download folder (game will not be wired into Steam).
        self.used_fallback = True
        downloads_folder = SettingsManager.get(
            "downloads_folder", str(Path.home() / "Downloads")
        )
        return downloads_folder or str(Path.home() / "Downloads")
    async def _supports_mod_flags(self, ddmod_path: Path) -> bool:
        """Detects whether the binary supports -depotkeys/-manifestfile (modded fork)."""
        cache_key = str(ddmod_path)
        if cache_key in self._support_cache:
            return self._support_cache[cache_key]

        supported = False
        try:
            proc = await asyncio.create_subprocess_exec(
                str(ddmod_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            out, _ = await proc.communicate()
            help_text = out.decode("utf-8", errors="replace").lower()
            supported = "-depotkeys" in help_text and "-manifestfile" in help_text
        except Exception:
            supported = False

        self._support_cache[cache_key] = supported
        return supported

    def pause(self):
        self.is_paused = True
        if self.current_process and self.current_process.returncode is None:
            self.current_process.terminate()

    def resume(self):
        self.is_paused = False

    def cancel(self):
        self.is_canceled = True
        if self.current_process and self.current_process.returncode is None:
            self.current_process.terminate()


    async def _write_keys_file(self) -> str:
        """Writes '<depot_id>;<hexkey>' lines to a temp keys file."""
        key_lines = [
            f"{depot_id};{d.get('key')}"
            for depot_id, d in self.depots.items()
            if d.get("key")
        ]
        if not key_lines:
            return ""

        fd, path = tempfile.mkstemp(suffix=".keys", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("\n".join(key_lines) + "\n")
        except Exception:
            os.unlink(path)
            raise
        return path

    async def run(self, progress_callback=None, error_callback=None, complete_callback=None):
        ddmod_path_str = SettingsManager.get("depotdownloadermod_path", "")
        if not ddmod_path_str:
            if error_callback:
                error_callback("DepotDownloaderMod path is not configured in settings.")
            return

        ddmod_path = Path(ddmod_path_str)
        if not ddmod_path.exists() or not ddmod_path.is_file():
            if error_callback:
                error_callback(f"DepotDownloaderMod not found at {ddmod_path}")
            return

        is_dll = ddmod_path_str.lower().endswith(".dll")


        # Target: Steam library steamapps/common/<installdir> (Accela-style).
        self.download_dir = self._resolve_target_dir()
        if not self.download_dir:
            if error_callback:
                error_callback(
                    "Steam kütüphanesi bulunamadı. Lütfen Settings'te Steam yolunu ayarlayın."
                )
            return
        if self.used_fallback and progress_callback:
            progress_callback(
                "⚠ UYARI: Steam kütüphanesi bulunamadı! Oyun Downloads klasörüne "
                "inecek ve Steam'e otomatik bağlanmayacak. Settings → Steam & "
                "Downloads'tan Steam yolunu ayarlayın."
            )
        if progress_callback:
            provider = SettingsManager.get("manifest_provider", "auto").upper()
            progress_callback(f"🚀 İndirme Başlatılıyor: {self.title} (AppID: {self.app_id}) [Engine: {provider}]")
            progress_callback(f"--- Hedef dizin: {self.download_dir} ---")
        manifest_dir = self.game_data.get("manifest_dir") or ""
        manifests = self.game_data.get("manifests", {}) or {}

        keys_file_path = None
        supports_mod = await self._supports_mod_flags(ddmod_path)

        try:
            if supports_mod:
                keys_file_path = await self._write_keys_file()
            elif error_callback:
                error_callback(
                    "Uyarı: DDMod binary'si -depotkeys/-manifestfile desteklemiyor "
                    "(vanilla build). Settings → Advanced Tools'tan modlanmış "
                    "DepotDownloaderMod'u kurun."
                )

            while self._current_depot_idx < len(self._ordered_depot_ids):
                if self.is_canceled:
                    return

                while self.is_paused:
                    await asyncio.sleep(0.5)
                    if self.is_canceled:
                        return

                depot_id = self._ordered_depot_ids[self._current_depot_idx]
                depot = self.depots[depot_id]
                man_id = depot.get("manifest_id")
                manifest_file = os.path.join(
                    manifest_dir, f"{depot_id}_{man_id}.manifest"
                ) if (manifest_dir and man_id) else ""
                if not depot_id:
                    self._current_depot_idx += 1
                    continue

                self._speed_state = None
                if manifest_file and os.path.exists(manifest_file):
                    sizes = parse_manifest(manifest_file)
                    if sizes:
                        # DDMod prints forward slashes; manifest keys use backslashes.
                        sizes = {k.replace("\\", "/"): v for k, v in sizes.items()}
                        self._speed_state = {
                            "sizes": sizes,
                            "seen": set(),
                            "bytes": 0,
                            "time": time.monotonic(),
                            "ema": None,
                        }

                if is_dll:
                    cmd = ["dotnet", str(ddmod_path)]
                else:
                    cmd = [str(ddmod_path)]

                cmd.extend([
                    "-app", str(self.app_id),
                    "-depot", str(depot_id),
                ])
                # -manifest is optional: without it DDMod fetches the current
                # manifest for the branch automatically.
                if man_id:
                    cmd.extend(["-manifest", str(man_id)])

                if supports_mod and manifest_file and os.path.exists(manifest_file):
                    cmd.extend(["-manifestfile", manifest_file])

                if keys_file_path:
                    cmd.extend(["-depotkeys", keys_file_path])


                cmd.extend(["-max-downloads", "25"])
                cmd.extend(["-dir", self.download_dir])
                cmd.extend(["-validate"])

                try:
                    self.current_process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                    )

                    while not self.current_process.stdout.at_eof():

                        try:
                            line = await asyncio.wait_for(
                                self.current_process.stdout.readline(), timeout=0.1
                            )
                            if line and progress_callback:
                                decoded_line = line.decode("utf-8", errors="replace").strip()
                                if decoded_line:
                                    progress_callback(self._enrich_with_speed(decoded_line))
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            if not self.is_canceled and not self.is_paused:
                                raise e

                    if self.is_canceled:
                        return
                    elif self.is_paused:
                        continue
                    else:
                        await self.current_process.wait()
                        if self.current_process.returncode != 0:
                            if error_callback:
                                error_callback(
                                    f"DepotDownloaderMod exited with code {self.current_process.returncode} for depot {depot_id}"
                                )
                            return

                        self._current_depot_idx += 1

                except Exception as e:
                    if error_callback:
                        error_callback(str(e))
                    return

            if complete_callback and not self.is_canceled:
                await self._post_download_steps_async()
                complete_callback()
        finally:
            if keys_file_path:
                try:
                    os.unlink(keys_file_path)
                except OSError:
                    pass

    def _enrich_with_speed(self, line: str) -> str:
        """Appends ' (x.x MB/s)' to DDMod progress lines derived from manifest sizes."""
        st = self._speed_state
        if not st:
            return line
        m = re.match(r"^\s*[\d.]+%\s+(.+?)\s*$", line)
        if not m:
            return line
        rel = m.group(1).replace("\\", "/")
        if self.download_dir:
            prefix = str(self.download_dir).replace("\\", "/")
            if rel.startswith(prefix):
                rel = rel[len(prefix):].lstrip("/")
        size = st["sizes"].get(rel)
        if size is not None and rel not in st["seen"]:
            st["seen"].add(rel)
            st["bytes"] += size
        now = time.monotonic()
        dt = now - st["time"]
        if dt >= 1.0 and st["bytes"] > 0:
            instant = st["bytes"] / dt / 1_000_000.0
            st["ema"] = instant if st["ema"] is None else st["ema"] * 0.6 + instant * 0.4
            st["time"] = now
            st["bytes"] = 0
            return f"{line}  ({st['ema']:.1f} MB/s)"
        return line

    async def _post_download_steps_async(self):
        """Wires the downloaded files into Steam: ACF, depotcache, SLSsteam config. Also Auto-Applies Ryuu fixes."""
        from src.services.acf import create_appmanifest
        from src.config.slssteam import SLSsteamConfigManager
        from src.utils.paths import get_steam_path

        # appmanifest_<appid>.acf so the game shows as installed.
        if self.steamapps_dir:
            create_appmanifest(self.steamapps_dir, self.game_data)

        # Ensure manifests are in Steam depotcache (Steam client reads them).
        manifest_dir = self.game_data.get("manifest_dir") or ""
        if manifest_dir:
            steam_path = get_steam_path()
            if steam_path:
                depotcache_dir = steam_path / "depotcache"
                depotcache_dir.mkdir(parents=True, exist_ok=True)
                for depot_id, man_id in (self.game_data.get("manifests", {}) or {}).items():
                    manifest_file = os.path.join(
                        manifest_dir, f"{depot_id}_{man_id}.manifest"
                    )
                    if os.path.exists(manifest_file):
                        try:
                            import shutil
                            shutil.copy2(
                                manifest_file,
                                depotcache_dir / f"{depot_id}_{man_id}.manifest",
                            )
                        except OSError:
                            pass

        # SLSsteam must allow playing unowned games.
        try:
            SLSsteamConfigManager().ensure_play_not_owned_games(True)
        except Exception:
            pass

        # Executable permissions for Linux binaries.
        self._set_linux_binary_permissions()

        # Auto-apply fix if applicable - try all providers in priority order
        try:
            provider = SettingsManager.get("manifest_provider", "auto")
            if provider in ("auto", "ryuu", "crackbypass", "onlinefix", "freetp") and self.download_dir:
                from src.api.unified_fix import UnifiedFixFetcher
                from src.utils.onlinefix_patcher import OnlineFixPatcher
                from src.config.slssteam import SLSsteamConfigManager
                import httpx
                import tempfile
                from pathlib import Path
                
                logger.info(f"Checking for auto-fix for {self.title}...")
                fixes = await UnifiedFixFetcher.get_available_fixes(self.title)
                
                if fixes:
                    # Try each fix in priority order (already sorted by badge/version)
                    for fix in fixes:
                        source = fix.get("source", "")
                        if source == "goldberg":
                            continue  # Skip Goldberg for auto-fix
                        
                        url = fix.get("url", "")
                        if not url:
                            continue
                        
                        logger.info(f"Attempting auto-fix from {source} for {self.title}...")
                        dest = Path(tempfile.gettempdir()) / f"autofix_{source}_{self.app_id}.zip"
                        
                        headers = {}
                        if source == "ryuu":
                            ryuu_key = SettingsManager.get("ryuu_api_key", "").strip()
                            if ryuu_key:
                                headers["X-Auth-Key"] = ryuu_key
                        
                        try:
                            async with httpx.AsyncClient(follow_redirects=True, timeout=120.0, headers=headers) as client:
                                resp = await client.get(url)
                                if resp.status_code == 200:
                                    dest.write_bytes(resp.content)
                                    
                                    # Apply fix based on source
                                    if source == "freetp":
                                        # FreeTP is an .exe installer
                                        OnlineFixPatcher.apply_freetp_exe(str(dest), str(self.app_id), str(self.download_dir))
                                    else:
                                        # Ryuu, CrackBypass, OnlineFix are archives
                                        OnlineFixPatcher.apply_patch_from_archive(str(dest), str(self.app_id), str(self.download_dir), password="")
                                    
                                    logger.info(f"Successfully auto-applied {source} fix for {self.title}.")
                                    
                                    # Apply launch options so fix works from Steam client without restart
                                    SLSsteamConfigManager().apply_fix_launch_options(self.app_id, source)
                                    break  # Success, stop trying other fixes
                                else:
                                    logger.warning(f"{source} fix download failed: HTTP {resp.status_code}")
                        except Exception as e:
                            logger.warning(f"Failed to apply {source} fix: {e}")
                            continue
                    else:
                        logger.info(f"No working auto-fix found for {self.title} from any provider")
        except Exception as e:
            logger.error(f"Failed to auto-apply fix: {e}")


    def _set_linux_binary_permissions(self):
        """Marks ELF/sh binaries executable after download (Accela parity)."""
        import sys
        if sys.platform != "linux" or not self.download_dir:
            return

        linux_extensions = {".sh", ".x86", ".x86_64", ".bin"}
        elf_magic = b"\x7fELF"

        try:
            for root, _dirs, files in os.walk(self.download_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_lower = file.lower()

                    try:
                        if os.path.getsize(file_path) < 1024:
                            continue
                    except OSError:
                        continue

                    should_chmod = False
                    if any(file_lower.endswith(ext) for ext in linux_extensions):
                        should_chmod = True
                    elif "." not in file:
                        try:
                            with open(file_path, "rb") as f:
                                if f.read(4) == elf_magic:
                                    should_chmod = True
                        except (IOError, OSError):
                            continue

                    if should_chmod:
                        try:
                            current_mode = os.stat(file_path).st_mode
                            if not (current_mode & 0o111):
                                os.chmod(file_path, current_mode | 0o755)
                        except OSError:
                            pass
        except OSError:
            pass
