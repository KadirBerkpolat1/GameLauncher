import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from src.api.fix_providers import provider_registry, register_default_providers, FixInfo

logger = logging.getLogger(__name__)

def parse_version(v: str) -> tuple:
    """Parses a version string into a tuple of ints/strings for comparison."""
    import re
    parts = re.findall(r'\d+|[a-zA-Z]+', v)
    parsed = []
    for p in parts:
        if p.isdigit():
            parsed.append(int(p))
        else:
            parsed.append(p)
    return tuple(parsed)


class UnifiedFixFetcher:
    @staticmethod
    async def get_available_fixes(game_name: str) -> List[Dict]:
        """
        Searches all registered fix providers for the game.
        Returns a list of dictionaries with keys: 'source', 'title', 'version', 'url', 'badges', 'metadata'.
        """
        # Ensure providers are registered
        register_default_providers()
        
        import re
        # Oyun isminin sonundaki ".53" gibi eklentileri temizle (PEAK.53 -> PEAK)
        search_query = re.sub(r'\.\d+$', '', game_name).strip()
        
        fixes: List[FixInfo] = await provider_registry.search_all(search_query)
        
        # Convert FixInfo objects to dict format for backward compatibility
        result = []
        for fix in fixes:
            result.append({
                "source": fix.source,
                "title": fix.title,
                "version": fix.version,
                "url": fix.url,
                "badges": fix.badges,
                "metadata": fix.metadata,
            })
        
        # Fallback: if no results, try broad search like before
        if not result:
            clean_name = re.sub(r'[^a-zA-Z\s]', '', search_query).strip()
            if clean_name and clean_name != search_query:
                logger.info(f"UnifiedFixFetcher: No results for '{search_query}', trying broad search '{clean_name}'")
                fixes2 = await provider_registry.search_all(clean_name)
                for fix in fixes2:
                    result.append({
                        "source": fix.source,
                        "title": fix.title,
                        "version": fix.version,
                        "url": fix.url,
                        "badges": fix.badges,
                        "metadata": fix.metadata,
                    })
        
        # Add Goldberg as explicit offline fallback (NOT a provider, always available local fallback)
        result.append({
            "source": "goldberg",
            "title": "Remove Steam DRM (Singleplayer / Offline Only)",
            "version": "Auto",
            "url": "",
            "badges": ["Offline"],
            "metadata": {"is_fallback": True},
        })
        
        logger.info(f"UnifiedFixFetcher: Returning {len(result)} fixes for '{game_name}'")
        return result
