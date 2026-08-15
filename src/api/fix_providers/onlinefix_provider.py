"""
OnlineFix Provider - Wraps existing OnlineFixClient for unified provider interface.
"""
import logging
from typing import List
from src.api.fix_providers import FixProvider, FixInfo
from src.api.onlinefix import onlinefix_api

logger = logging.getLogger(__name__)


class OnlineFixProvider(FixProvider):
    """Online-Fix.me provider with multiplayer fixes."""
    
    PRIORITY = 30  # After Ryuu and CrackBypass
    NAME = "OnlineFix"
    SOURCE_NAME = "onlinefix"
    REQUIRES_AUTH = False
    
    async def search_game(self, query: str) -> List[FixInfo]:
        """Search OnlineFix for fixes."""
        try:
            results = await onlinefix_api.search_game(query, limit=10)
            fixes = []
            
            for raw in results:
                # Get detailed page info for version
                page_info = await onlinefix_api.get_game_page(raw["url"])
                version = page_info.get("version", raw.get("version", "1.0.0"))
                
                fix = FixInfo(
                    source="onlinefix",
                    title=raw.get("title", "OnlineFix Multiplayer Fix"),
                    version=version,
                    url=raw["url"],
                    badges=["Online"],
                    metadata={
                        "hoster_link": page_info.get("hoster_link"),
                        "entries": page_info.get("entries", []),
                    }
                )
                fixes.append(fix)
            
            logger.info(f"OnlineFix: Found {len(fixes)} fixes for '{query}'")
            return fixes
            
        except Exception as e:
            logger.warning(f"OnlineFix search failed for '{query}': {e}")
            return []
    
    async def download_fix(self, fix: FixInfo, dest_dir) -> str:
        """Download OnlineFix fix (requires hoster resolution)."""
        import tempfile
        from pathlib import Path
        from urllib.parse import urlparse, unquote
        
        metadata = fix.metadata
        hoster_url = metadata.get("hoster_link")
        
        if not hoster_url:
            raise ValueError("OnlineFix fix has no hoster link")
        
        # Get fix entries and pick best
        game_name = unquote(urlparse(hoster_url).path.strip("/"))
        entries = await onlinefix_api.get_fix_entries(game_name)
        best_fix = onlinefix_api.pick_fix(entries)
        
        if not best_fix:
            raise ValueError("No suitable fix found in OnlineFix entries")
        
        # Resolve direct download
        direct_url, cookies = await onlinefix_api.resolve_direct(best_fix)
        
        dest_path = Path(dest_dir) / f"onlinefix_{game_name}_{best_fix['file_name']}"
        await onlinefix_api.download(direct_url, str(dest_path), cookies)
        
        logger.info(f"OnlineFix: Downloaded fix to {dest_path}")
        return str(dest_path)