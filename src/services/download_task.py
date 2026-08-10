import asyncio
import os
import subprocess
import tempfile
from pathlib import Path
from src.config.settings import SettingsManager

class DownloadPausedError(Exception):
    pass

class DownloadCanceledError(Exception):
    pass

class DownloadTask:
    """
    Manages a multi-depot download session for a single game via DepotDownloaderMod.
    Supports pause, resume, and cancel by controlling the underlying subprocess.
    """
    def __init__(self, app_id: int, title: str, depots: list):
        self.app_id = app_id
        self.title = title
        self.depots = depots
        self.is_paused = False
        self.is_canceled = False
        self.current_process = None
        self._current_depot_idx = 0

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

        is_dll = ddmod_path_str.lower().endswith('.dll')

        steam_username = SettingsManager.get("steam_username", "")
        steam_password = SettingsManager.get("steam_password", "")

        # Build a depot keys file from the decryption keys already fetched via Hubcap.
        # This lets DepotDownloaderMod download anonymously without relying on config.vdf.
        keys_file_path = None
        try:
            key_lines = [
                f"{d['depot_id']};{d['decryption_key']}"
                for d in self.depots
                if d.get("depot_id") and d.get("decryption_key")
            ]
            # Only use the keys file if every queued depot has a key; otherwise fall back
            # to config.vdf/credentials so a missing key doesn't break the whole batch.
            all_have_keys = len(key_lines) == len(self.depots) and bool(key_lines)
            if all_have_keys:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".keys", delete=False, encoding="utf-8") as f:
                    f.write("\n".join(key_lines) + "\n")
                    keys_file_path = f.name

            while self._current_depot_idx < len(self.depots):
                if self.is_canceled:
                    return

                # Wait while paused
                while self.is_paused:
                    await asyncio.sleep(0.5)
                    if self.is_canceled:
                        return

                depot = self.depots[self._current_depot_idx]
                depot_id = depot.get("depot_id")
                man_id = depot.get("manifest_id")

                if not depot_id or not man_id:
                    self._current_depot_idx += 1
                    continue

                if is_dll:
                    cmd = ["dotnet", str(ddmod_path)]
                else:
                    cmd = [str(ddmod_path)]

                cmd.extend([
                    "-app", str(self.app_id),
                    "-depot", str(depot_id),
                    "-manifest", str(man_id)
                ])

                if keys_file_path:
                    cmd.extend(["-depotkeys", keys_file_path])

                if steam_username and steam_password:
                    cmd.extend(["-username", steam_username, "-password", steam_password])

                downloads_folder = SettingsManager.get("downloads_folder", str(Path.home() / "Downloads"))
                if downloads_folder:
                    cmd.extend(["-dir", downloads_folder])

                try:
                    self.current_process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT
                    )

                    while not self.current_process.stdout.at_eof():
                        if self.is_canceled or self.is_paused:
                            if self.current_process.returncode is None:
                                self.current_process.terminate()
                            await self.current_process.wait()
                            break
                            
                        try:
                            line = await asyncio.wait_for(self.current_process.stdout.readline(), timeout=0.1)
                            if line and progress_callback:
                                decoded_line = line.decode('utf-8', errors='replace').strip()
                                if decoded_line:
                                    progress_callback(decoded_line)
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            if not self.is_canceled and not self.is_paused:
                                raise e

                    if self.is_canceled:
                        return
                    elif self.is_paused:
                        continue  # Break inner loop, restarts same depot
                    else:
                        await self.current_process.wait()
                        if self.current_process.returncode != 0:
                            if error_callback:
                                error_callback(f"DepotDownloaderMod exited with code {self.current_process.returncode}")
                            return
                        
                        # Successfully completed this depot
                        self._current_depot_idx += 1

                except Exception as e:
                    if error_callback:
                        error_callback(str(e))
                    return

            if complete_callback and not self.is_canceled:
                complete_callback()
        finally:
            if keys_file_path:
                try:
                    os.unlink(keys_file_path)
                except OSError:
                    pass
