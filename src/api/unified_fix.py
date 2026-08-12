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
        import re
        # Oyun isminin sonundaki ".53" gibi eklentileri temizle (PEAK.53 -> PEAK)
        search_query = re.sub(r'\.\d+$', '', game_name).strip()
        
        of_task = onlinefix_api.search_game(search_query, limit=1)
        ft_task = freetp_api.search_game(search_query)


        of_results, ft_result = await asyncio.gather(of_task, ft_task, return_exceptions=True)

        fixes = []

        async def _process_results(of_res, ft_res):
            if not isinstance(of_res, Exception) and of_res:
                of_best = of_res[0]
                try:
                    page_info = await onlinefix_api.get_game_page(of_best["url"])
                    of_best["version"] = page_info.get("version", of_best.get("version", "0.0.0"))
                except Exception:
                    pass
                of_best["source"] = "onlinefix"
                fixes.append(of_best)
                
            if not isinstance(ft_res, Exception) and ft_res:
                ft_best = ft_res
                ft_best["source"] = "freetp"
                fixes.append(ft_best)

        await _process_results(of_results, ft_result)
        
        # Eğer iki siteden de hicbir sonuc donmediyse ismin icindeki noktalama/rakamlari 
        # silip (ornegin PEAK.53 -> PEAK) tekrar kaba bir arama yapalim.
        # Eger yama bulunamadiysa ve isimde hala rakam vb varsa, genisletilmis arama yapabiliriz.
        # Ancak flood control (15sn) yuzunden pes pese arama yaparsak OnlineFix bos doner.
        if not fixes:
            clean_name = re.sub(r'[^a-zA-Z\s]', '', search_query).strip()
            if clean_name and clean_name != search_query:
                # OnlineFix flood control e takilabilir, ama FreeTP takilmaz.
                of_task2 = onlinefix_api.search_game(clean_name, limit=1)
                ft_task2 = freetp_api.search_game(clean_name)
                of_res2, ft_res2 = await asyncio.gather(of_task2, ft_task2, return_exceptions=True)
                await _process_results(of_res2, ft_res2)

        # Sort fixes so the highest version comes first
        def get_ver_tuple(fix):
            try:
                return parse_version(fix.get("version", "0.0.0"))
            except:
                return (0,)
                
        fixes.sort(key=get_ver_tuple, reverse=True)
        return fixes
