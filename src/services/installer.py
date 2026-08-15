import asyncio
import httpx
import shutil
from pathlib import Path

class InstallerError(Exception):
    pass

class DDModInstaller:
    """
    Sets up the modded DepotDownloaderMod binary (SteamAutoCracks fork).

    The fork adds -depotkeys and -manifestfile, enabling anonymous downloads
    with just the depot keys and a manifest file. Its official releases only
    ship Windows builds, so we bundle a self-contained x64 Linux build in
    assets/deps/ (rebuilt via scripts/build_ddmod.sh). If the bundle is not
    present (e.g. a source checkout), we fall back to the binary Accela ships.
    """
    # Bundled Linux standalone built from the fork (see scripts/build_ddmod.sh).
    BUNDLED_PATH = Path(__file__).resolve().parents[2] / "assets" / "deps" / "DepotDownloaderMod"
    # Fallback: the Linux build Accela bundles (same fork).
    MOD_BINARY_URL = (
        "https://raw.githubusercontent.com/FaultyPacketOverflowVector/Accela/"
        "main/src/deps/DepotDownloaderMod"
    )
    INSTALL_DIR = Path.home() / ".config" / "GameLauncher" / "DDMod"

    @classmethod
    async def update_ddmod(cls) -> str:
        source = None
        content = None

        # Prefer the bundled binary shipped with this repo.
        if cls.BUNDLED_PATH.exists():
            content = cls.BUNDLED_PATH.read_bytes()
            source = str(cls.BUNDLED_PATH)

        # Otherwise fetch the fallback URL.
        if content is None:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(cls.MOD_BINARY_URL, timeout=30.0)
                resp.raise_for_status()
                content = resp.content
                source = cls.MOD_BINARY_URL

        # Sanity check: make sure we actually got an ELF and not an HTML error page.
        if content[:4] != b"\x7fELF":
            raise InstallerError(
                "Downloaded DepotDownloaderMod is not a valid Linux binary."
            )

        if cls.INSTALL_DIR.exists():
            shutil.rmtree(cls.INSTALL_DIR)
        cls.INSTALL_DIR.mkdir(parents=True, exist_ok=True)

        bin_path = cls.INSTALL_DIR / "DepotDownloaderMod"
        bin_path.write_bytes(content)
        bin_path.chmod(0o755)

        from src.config.settings import SettingsManager
        SettingsManager.set("depotdownloadermod_path", str(bin_path))
        return f"3.4.0-mod (from {source})"

    @classmethod
    async def uninstall_ddmod(cls) -> None:
        if cls.INSTALL_DIR.exists():
            shutil.rmtree(cls.INSTALL_DIR, ignore_errors=True)
        SettingsManager.set("depotdownloadermod_path", "")

    @classmethod
    def run_installer_async(cls, progress_callback: callable, done_callback: callable) -> None:
        """Runs DDMod update in background thread."""
        import asyncio
        from src.utils.async_utils import get_async_loop
        
        async def _task():
            try:
                result = await cls.update_ddmod()
                done_callback(True, f"DDMod updated: {result}")
            except Exception as e:
                done_callback(False, f"DDMod update failed: {e}")
        
        asyncio.run_coroutine_threadsafe(_task(), get_async_loop())


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
        subprocess.run(
            ["flatpak", "override", "--user",
             "--unset-env=LD_AUDIT", "--unset-env=SHARED_LIBRARY_GUARD",
             "com.valvesoftware.Steam"],
            stderr=subprocess.DEVNULL,
            check=False,
        )

    @classmethod
    def run_installer_async(cls, progress_callback: callable, done_callback: callable) -> None:
        """Runs SLSsteam update in background thread."""
        import asyncio
        from src.utils.async_utils import get_async_loop
        
        async def _task():
            try:
                result = await cls.update_slssteam()
                done_callback(True, f"SLSsteam updated: {result}")
            except Exception as e:
                done_callback(False, f"SLSsteam update failed: {e}")
        
        asyncio.run_coroutine_threadsafe(_task(), get_async_loop())
        import subprocess
        subprocess.run(
            ["flatpak", "override", "--user",
             "--unset-env=LD_AUDIT", "--unset-env=SHARED_LIBRARY_GUARD",
             "com.valvesoftware.Steam"],
            stderr=subprocess.DEVNULL,
            check=False,
        )
