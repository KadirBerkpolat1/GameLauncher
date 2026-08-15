"""
FreeTP Provider - Wraps existing FreeTPClient for unified provider interface.
"""
import logging
from typing import List
from src.api.fix_providers import FixProvider, FixInfo
from src.api.freetp import freetp_api

logger = logging.getLogger(__name__)


class FreeTPProvider(FixProvider):
    """FreeTP.org provider with multiplayer fixes."""
    
    PRIORITY = 40  # After OnlineFix
    NAME = "FreeTP"
    SOURCE_NAME = "freetp"
    REQUIRES_AUTH = False
    
    async def search_game(self, query: str) -> List[FixInfo]:
        """Search FreeTP for fixes."""
        try:
            result = await freetp_api.search_game(query)
            fixes = []
            
            if result:
                fix = FixInfo(
                    source="freetp",
                    title=result.get("title", "FreeTP Multiplayer Fix"),
                    version=result.get("version", "1.0.0"),
                    url=result.get("url", ""),
                    badges=["Online"],
                    metadata={}
                )
                fixes.append(fix)
            
            logger.info(f"FreeTP: Found {len(fixes)} fixes for '{query}'")
            return fixes
            
        except Exception as e:
            logger.warning(f"FreeTP search failed for '{query}': {e}")
            return []
    
    async def download_fix(self, fix: FixInfo, dest_dir) -> str:
        """Download FreeTP fix (.exe installer)."""
        import tempfile
        from pathlib import Path
        
        url = fix.url
        if not url:
            raise ValueError("FreeTP fix has no download URL")
        
        dest_path = await freetp_api.download_fix(url, Path(dest_dir))
        
        if not dest_path:
            raise ValueError("FreeTP download failed")
        
        logger.info(f"FreeTP: Downloaded fix to {dest_path}")
        return str(dest_path)