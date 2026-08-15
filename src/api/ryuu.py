import logging
from typing import Dict, Any, Optional
import httpx
from src.config.settings import SettingsManager

logger = logging.getLogger(__name__)


class RyuuAPIError(Exception):
    """Base exception for Ryuu Manifest API errors."""
    pass


class RyuuAuthError(RyuuAPIError):
    """Raised when the Ryuu API key is missing or invalid."""
    pass


class RyuuRateLimitError(RyuuAPIError):
    """Raised when Ryuu API rate limits are exceeded."""
    pass


class RyuuClient:
    """
    Async client for Ryuu's Manifest Generator API (generator.ryuu.lol).
    Provides access to .lua manifest generators, manifests, and game updates.
    """
    BASE_URL = "https://generator.ryuu.lol/api"

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    def _get_api_key(self) -> str:
        key = SettingsManager.get("ryuu_api_key", "").strip()
        return key

    def _get_client(self) -> httpx.AsyncClient:
        key = self._get_api_key()
        headers = {
            "User-Agent": "NebulaLauncher/0.1.0",
            "Accept": "application/json"
        }
        if key:
            headers["X-Auth-Key"] = key

        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=20.0
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def download_manifest(self, app_id: int, file_type: str = "lua", branch: str = "public") -> bytes:
        """
        Downloads a manifest, .lua file, or full zip for a given Steam AppID.
        :param app_id: Steam Application ID
        :param file_type: 'lua', 'manifest', or 'zip'
        :param branch: Steam branch name (default 'public')
        """
        client = self._get_client()
        params = {}
        if branch and branch != "public":
            params["branch"] = branch
        if file_type in ("lua", "manifest"):
            params["file_type"] = file_type

        try:
            resp = await client.get(f"/download/{app_id}", params=params)
            if resp.status_code == 401 or resp.status_code == 403:
                raise RyuuAuthError("Ryuu API authentication failed. Check your API key in Settings.")
            if resp.status_code == 429:
                raise RyuuRateLimitError("Ryuu API rate limit exceeded.")
            resp.raise_for_status()
            return resp.content
        except httpx.HTTPStatusError as e:
            raise RyuuAPIError(f"HTTP error {e.response.status_code} from Ryuu: {e}") from e
        except Exception as e:
            raise RyuuAPIError(f"Network error requesting Ryuu manifest for {app_id}: {e}") from e


    async def get_available_fixes(self, game_name: str) -> list:
        """
        Fetches fixes.json from Ryuu and searches for the game.
        Returns a list of fixes formatted for UnifiedFixFetcher.
        """
        import re
        client = self._get_client()
        try:
            resp = await client.get("https://generator.ryuu.lol/files/fixes.json")
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"Failed to fetch fixes.json from Ryuu: {e}")
            return []
            
        search_query = re.sub(r'[\W_]+', '', game_name.lower())
        fixes = []
        
        for item in data:
            item_name = re.sub(r'[\W_]+', '', item.get("name", "").lower())
            if item_name == search_query or search_query in item_name:
                for fix in item.get("fixes", []):
                    badges = fix.get("badges", [])
                    badges_str = ", ".join(badges)
                    title_suffix = f" [{badges_str}]" if badges else ""
                    
                    fixes.append({
                        "source": "ryuu",
                        "title": f"Ryuu Fix{title_suffix}",
                        "version": fix.get("size", "0.0"),
                        "url": fix.get("href", ""),
                        "badges": badges
                    })
        return fixes
    async def request_manifest(self, app_id: int) -> Dict[str, Any]:
        """Requests generation of a new or updated manifest for a Steam app."""
        # request_update endpoint is at root, not under /api
        import httpx
        headers = {"User-Agent": "NebulaLauncher/0.1.0", "Accept": "application/json"}
        key = self._get_api_key()
        if key:
            headers["X-Auth-Key"] = key
        async with httpx.AsyncClient(headers=headers, timeout=20.0) as client:
            resp = await client.get("https://generator.ryuu.lol/requestupdate", params={"appid": app_id})
            resp.raise_for_status()
            return resp.json()


ryuu_api = RyuuClient()
