import httpx
from typing import Dict, Any, List, Optional
from src.config.settings import SettingsManager

class HubcapAPIError(Exception):
    """Base exception for HubcapManifest API errors."""
    pass

class HubcapAuthError(HubcapAPIError):
    """Raised when the API key is invalid or missing."""
    pass

class HubcapRateLimitError(HubcapAPIError):
    """Raised when the API rate limit is exceeded."""
    pass

class HubcapClient:
    """
    Async client for the HubcapManifest API.
    Handles authentication, requests, error management, and basic in-memory caching.
    """
    BASE_URL = "https://hubcapmanifest.com/api/v1"

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._client: Optional[httpx.AsyncClient] = None

    def _get_api_key(self) -> str:
        api_key = SettingsManager.get("hubcap_api_key", "")
        if not api_key:
            raise HubcapAuthError("Hubcap API key is missing. Please set it in the settings.")
        return api_key

    def _get_client(self) -> httpx.AsyncClient:
        """Returns the active httpx client or creates a new one."""
        if self._client is None or self._client.is_closed:
            headers = {
                "Authorization": f"Bearer {self._get_api_key()}",
                "Accept": "application/json",
                "User-Agent": "GameLauncher/0.1.0"
            }
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=10.0
            )
        return self._client

    async def close(self) -> None:
        """Closes the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        """
        Internal method to execute HTTP requests with error handling.
        """
        client = self._get_client()
        try:
            response = await client.request(method, endpoint, **kwargs)

            if response.status_code == 401:
                raise HubcapAuthError("Invalid API key (401 Unauthorized).")
            elif response.status_code == 429:
                raise HubcapRateLimitError("Rate limit exceeded (429 Too Many Requests).")

            response.raise_for_status()
            
            if "application/json" not in response.headers.get("content-type", "").lower():
                raise HubcapAPIError("API, JSON formatında yanıt vermedi. (Sunucu çökmüş veya bakımda olabilir).")
                
            return response.json()

        except httpx.HTTPStatusError as e:
            raise HubcapAPIError(f"HTTP Error {e.response.status_code}: {e.response.text}") from e
        except httpx.RequestError as e:
            raise HubcapAPIError(f"Network error while requesting {e.request.url!r}: {e}") from e

    async def get_library(self, limit: int = 100, offset: int = 0, search: str = "", sort_by: str = "updated") -> Dict[str, Any]:
        """
        Browse all available games with pagination, search, and sorting.
        """
        params = {
            "limit": limit,
            "offset": offset,
            "sort_by": sort_by
        }
        if search:
            params["search"] = search
            
        return await self._request("GET", "/library", params=params)

    async def get_status(self, app_id: int) -> Dict[str, Any]:
        """
        Check if a manifest exists and get file information without downloading.
        """
        return await self._request("GET", f"/status/{app_id}")

    async def search_game(self, query: str, limit: int = 50, appid: bool = False) -> Dict[str, Any]:
        """
        Search for games by name or App ID.
        """
        params = {
            "q": query,
            "limit": limit,
            "appid": str(appid).lower()
        }
        return await self._request("GET", "/search", params=params)

    async def get_app_details(self, app_id: int) -> Dict[str, Any]:
        """
        Fetches detailed information for a specific game.
        Results are cached.
        """
        cache_key = f"app_details_{app_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Temporary fallback for Ryuu if needed, assuming the new Hubcap REST API uses /status or /library
        # For now, we'll try to fetch status as details
        data = await self.get_status(app_id)
        self._cache[cache_key] = data
        return data

    async def get_app_manifest_zip(self, app_id: int, force_update: bool = False, content: str = "") -> bytes:
        """
        Download a game manifest ZIP file. Counts toward daily usage limit.
        """
        client = self._get_client()
        params = {}
        if force_update:
            params["force_update"] = "true"
        if content:
            params["content"] = content
            
        try:
            response = await client.get(f"/manifest/{app_id}", params=params, timeout=60.0)
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HubcapAuthError("Invalid API key or exhausted quota (401).")
            raise HubcapAPIError(f"HTTP {e.response.status_code} while downloading manifest for {app_id}") from e
        except httpx.RequestError as e:
            raise HubcapAPIError(f"Network error downloading manifest: {e}") from e

    async def get_app_lua(self, app_id: int, section: str = "full") -> bytes:
        """
        Download the Lua manifest file. Counts toward daily usage limit.
        section can be "full", "basegame", or "dlc".
        """
        client = self._get_client()
        endpoint = f"/lua/{app_id}"
        if section == "basegame":
            endpoint = f"/lua/basegame/{app_id}"
        elif section == "dlc":
            endpoint = f"/lua/dlc/{app_id}"
            
        try:
            response = await client.get(endpoint, timeout=30.0)
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise HubcapAuthError("Invalid API key or exhausted quota (401).")
            raise HubcapAPIError(f"HTTP {e.response.status_code} while downloading lua for {app_id}") from e
        except httpx.RequestError as e:
            raise HubcapAPIError(f"Network error downloading lua: {e}") from e

    def clear_cache(self) -> None:
        """Clears the in-memory cache."""
        self._cache.clear()

# Global instance for easy access across the application
hubcap_api = HubcapClient()
