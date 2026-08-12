import asyncio
from typing import Dict, Optional, Tuple
from pathlib import Path

from src.api.onlinefix import onlinefix_api
from src.api.freetp import freetp_api

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
    async def get_available_fixes(game_name: str) -> list:
        """
        Searches both Online-Fix and FreeTP for the game.
        Returns a list of dictionaries with keys: 'source', 'title', 'version', 'url'.
        """
        of_task = onlinefix_api.search_game(game_name, limit=1)
        ft_task = freetp_api.search_game(game_name)

        of_results, ft_result = await asyncio.gather(of_task, ft_task, return_exceptions=True)

        fixes = []

        if not isinstance(of_results, Exception) and of_results:
            of_best = of_results[0]
            # Fetch the actual game page to get the correct version (OnlineFix hides it in the page body)
            try:
                page_info = await onlinefix_api.get_game_page(of_best["url"])
                of_best["version"] = page_info.get("version", of_best.get("version", "0.0.0"))
            except Exception:
                pass
            of_best["source"] = "onlinefix"
            fixes.append(of_best)
            
        if not isinstance(ft_result, Exception) and ft_result:
            ft_best = ft_result
            ft_best["source"] = "freetp"
            fixes.append(ft_best)

        # Sort fixes so the highest version comes first
        def get_ver_tuple(fix):
            try:
                return parse_version(fix.get("version", "0.0.0"))
            except:
                return (0,)
                
        fixes.sort(key=get_ver_tuple, reverse=True)
        return fixes
