"""
API clients for external services (Hubcap, Ryuu, OnlineFix, FreeTP).
"""
from src.api.hubcap import hubcap_api, HubcapAPIError, HubcapAuthError, HubcapRateLimitError
from src.api.ryuu import ryuu_api, RyuuAPIError, RyuuAuthError, RyuuRateLimitError
from src.api.onlinefix import onlinefix_api
from src.api.freetp import freetp_api
from src.api.unified_fix import UnifiedFixFetcher

__all__ = [
    "hubcap_api", "HubcapAPIError", "HubcapAuthError", "HubcapRateLimitError",
    "ryuu_api", "RyuuAPIError", "RyuuAuthError", "RyuuRateLimitError",
    "onlinefix_api", "freetp_api", "UnifiedFixFetcher",
]