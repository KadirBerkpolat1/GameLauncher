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

    async def search_game(self, query: str) -> List[Dict[str, Any]]:
        """
        Searches for a game by name. Requires minimum 3 characters.
        Uses in-memory caching to prevent duplicate API calls for the same query.
        """
        if len(query) < 3:
            raise ValueError("Search query must be at least 3 characters long.")

        cache_key = f"search_{query.lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        data = await self._request("GET", "/search", params={"q": query})

        # Assuming the API returns a list of games or a dict with a 'results' key.
        # Adjust parsing based on actual HubcapManifest API structure.
        results = data.get("results", []) if isinstance(data, dict) else data

        self._cache[cache_key] = results
        return results

    async def get_app_details(self, app_id: int) -> Dict[str, Any]:
        """
        Fetches detailed information for a specific game (depots, manifests, decryption keys).
        Results are cached.
        """
        cache_key = f"app_{app_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        data = await self._request("GET", f"/apps/{app_id}")
        self._cache[cache_key] = data
        return data

    async def get_app_manifest_zip(self, app_id: int) -> bytes:
        """
        Downloads the raw ZIP archive containing the .manifest files and the .lua keys
        from the Hubcap API.
        """
        client = self._get_client()
        try:
            response = await client.get(f"/manifest/{app_id}", timeout=15.0)
            if response.status_code == 401:
                raise HubcapAuthError("Invalid API key (401 Unauthorized).")
            elif response.status_code == 429:
                raise HubcapRateLimitError("Rate limit exceeded (429 Too Many Requests).")
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as e:
            raise HubcapAPIError(f"HTTP Error {e.response.status_code}: {e.response.text}") from e
        except httpx.RequestError as e:
            raise HubcapAPIError(f"Network error while requesting {e.request.url!r}: {e}") from e

    def clear_cache(self) -> None:
        """Clears the in-memory cache."""
        self._cache.clear()

# Global instance for easy access across the application
hubcap_api = HubcapClient()
