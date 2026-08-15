"""
Fix Provider Architecture - Unified interface for all fix sources.
"""
import abc
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FixInfo:
    """Standardized fix information across all providers."""
    source: str  # Provider identifier: "ryuu", "onlinefix", "freetp", "crackbypass", "goldberg"
    title: str   # Human-readable title
    version: str # Version string for sorting
    url: str     # Download URL or identifier
    badges: List[str] = None  # ["Online", "Bypass", "Crack", etc.]
    metadata: Dict[str, Any] = None  # Provider-specific extra data

    def __post_init__(self):
        if self.badges is None:
            self.badges = []
        if self.metadata is None:
            self.metadata = {}


class FixProvider(abc.ABC):
    """Abstract base class for all fix providers."""
    
    # Priority for provider selection (lower = higher priority)
    PRIORITY = 100
    
    # Human-readable name
    NAME = "Unknown"
    
    # Whether provider requires API key
    REQUIRES_AUTH = False
    
    @abc.abstractmethod
    async def search_game(self, query: str) -> List[FixInfo]:
        """
        Search for fixes for a game.
        
        Args:
            query: Game name to search for
            
        Returns:
            List of FixInfo objects, sorted by relevance (best first)
        """
        pass
    
    @abc.abstractmethod
    async def download_fix(self, fix: FixInfo, dest_dir) -> Optional[str]:
        """
        Download a fix to destination directory.
        
        Args:
            fix: FixInfo object from search_game()
            dest_dir: Path to download directory
            
        Returns:
            Path to downloaded file, or None on failure
        """
        pass
    
    async def get_badges(self, fix: FixInfo) -> List[str]:
        """Get badge labels for a fix (override if provider has badge data)."""
        return fix.badges
    
    def get_priority(self) -> int:
        """Get provider priority for sorting."""
        return self.PRIORITY
    
    def get_name(self) -> str:
        """Get provider display name."""
        return self.NAME


class ProviderRegistry:
    """Registry for fix providers with priority-based ordering."""
    
    def __init__(self):
        self._providers: List[FixProvider] = []
        self._initialized = False
    
    def register(self, provider: FixProvider) -> None:
        """Register a provider. Maintains priority order."""
        self._providers.append(provider)
        self._providers.sort(key=lambda p: p.get_priority())
    
    def get_all(self) -> List[FixProvider]:
        """Get all registered providers in priority order."""
        return self._providers[:]
    
    def get_by_name(self, name: str) -> Optional[FixProvider]:
        """Get provider by source name."""
        for p in self._providers:
            if p.get_name().lower() == name.lower() or \
               (hasattr(p, 'SOURCE_NAME') and p.SOURCE_NAME.lower() == name.lower()):
                return p
        return None
    
    async def search_all(self, query: str) -> List[FixInfo]:
        """Search all providers in priority order and merge results."""
        all_fixes = []
        
        # Run all searches in parallel
        import asyncio
        tasks = [p.search_game(query) for p in self._providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for provider, result in zip(self._providers, results):
            if isinstance(result, Exception):
                logger.warning(f"Provider {provider.get_name()} search failed: {result}")
                continue
            if result:
                all_fixes.extend(result)
        
        # Sort by badges priority, then version
        all_fixes.sort(key=self._fix_sort_key, reverse=True)
        return all_fixes
    
    def _fix_sort_key(self, fix: FixInfo) -> tuple:
        """Sort key: badge priority > version > source priority."""
        # Badge priority: Online=3, Bypass=2, Crack=1, none=0
        badge_priority = 0
        for badge in fix.badges:
            badge_lower = badge.lower()
            if "online" in badge_lower:
                badge_priority = max(badge_priority, 3)
            elif "bypass" in badge_lower:
                badge_priority = max(badge_priority, 2)
            elif "crack" in badge_lower:
                badge_priority = max(badge_priority, 1)
        
        # Parse version for comparison
        from src.utils.fix_utils import extract_version
        version_tuple = extract_version(fix.version)
        
        # Provider priority (lower = better)
        provider_priority = next(
            (p.get_priority() for p in self._providers if p.get_name().lower() == fix.source.lower()),
            999
        )
        
        return (badge_priority, version_tuple, -provider_priority)


# Global registry instance
provider_registry = ProviderRegistry()


def register_default_providers() -> None:
    """Register all built-in providers. Call on app startup."""
    if provider_registry._initialized:
        return
    
    # Import here to avoid circular imports
    from src.api.fix_providers.ryuu_provider import RyuuFixProvider
    from src.api.fix_providers.onlinefix_provider import OnlineFixProvider
    from src.api.fix_providers.freetp_provider import FreeTPProvider
    from src.api.fix_providers.crackbypass_provider import CrackBypassProvider
    
    provider_registry.register(RyuuFixProvider())
    provider_registry.register(CrackBypassProvider())
    provider_registry.register(OnlineFixProvider())
    provider_registry.register(FreeTPProvider())
    
    provider_registry._initialized = True
    logger.info(f"Registered {len(provider_registry._providers)} fix providers: "
                f"{[p.get_name() for p in provider_registry._providers]}")