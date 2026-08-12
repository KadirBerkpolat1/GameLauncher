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
    async def get_best_fix(game_name: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Searches both Online-Fix and FreeTP for the game.
        Returns (best_result_dict, source_name).
        Result dict contains at least 'url', 'version', 'title'.
        source_name is either 'onlinefix' or 'freetp'.
        """
        of_task = onlinefix_api.search_game(game_name, limit=1)
        ft_task = freetp_api.search_game(game_name)

        of_results, ft_result = await asyncio.gather(of_task, ft_task, return_exceptions=True)

        of_best = None
        if not isinstance(of_results, Exception) and of_results:
            of_best = of_results[0]
            
        ft_best = None
        if not isinstance(ft_result, Exception) and ft_result:
            ft_best = ft_result

        if not of_best and not ft_best:
            return None, None

        if of_best and not ft_best:
            return of_best, "onlinefix"
            
        if ft_best and not of_best:
            return ft_best, "freetp"

        # Compare versions
        v_of = of_best.get("version", "0.0.0")
        v_ft = ft_best.get("version", "0.0.0")

        try:
            p_of = parse_version(v_of)
            p_ft = parse_version(v_ft)
        except:
            p_of = (0,)
            p_ft = (0,)

        # if freetp is strictly newer, pick freetp. Otherwise onlinefix.
        if p_ft > p_of:
            return ft_best, "freetp"
        
        return of_best, "onlinefix"
