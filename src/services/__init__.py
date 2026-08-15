"""
Services for game management, DRM, downloads, and Steam integration.
"""
from src.services.drm_manager import DRMManager
from src.services.download import DownloadManager
from src.services.download_task import DownloadTask
from src.services.installer import DDModInstaller, SLSsteamInstaller
from src.services.acf import create_appmanifest, get_installed_games
from src.services.metadata import MetadataFetcher
from src.services.plugin_manager import PluginManager
from src.services.cloud_redirect import CloudRedirectManager
from src.services.uninstall import uninstall_game, UninstallError

__all__ = [
    "DRMManager", "DownloadManager", "DownloadTask", "DDModInstaller",
    "SLSsteamInstaller", "create_appmanifest", "get_installed_games",
    "MetadataFetcher", "PluginManager", "CloudRedirectManager",
    "uninstall_game", "UninstallError",
]