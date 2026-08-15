"""
Ryuu Fix Provider - Wraps existing RyuuClient for unified provider interface.
"""
import logging
from typing import List, Dict, Any
from src.api.fix_providers import FixProvider, FixInfo
from src.api.ryuu import ryuu_api

logger = logging.getLogger(__name__)


class RyuuFixProvider(FixProvider):
    """Ryuu API fix provider with Online/Bypass badges."""
    
    PRIORITY = 10  # Highest priority - primary source
    NAME = "Ryuu"
    SOURCE_NAME = "ryuu"
    REQUIRES_AUTH = True
    
    async def search_game(self, query: str) -> List[FixInfo]:
        """Search Ryuu for fixes."""
        try:
            raw_fixes = await ryuu_api.get_available_fixes(query)
            fixes = []
            
            for raw in raw_fixes:
                # Parse badges from Ryuu response
                badges = []
                if raw.get("online"):
                    badges.append("Online")
                if raw.get("bypass"):
                    badges.append("Bypass")
                
                fix = FixInfo(
                    source="ryuu",
                    title=raw.get("name", "Ryuu Fix"),
                    version=raw.get("version", "1.0.0"),
                    url=raw.get("url", ""),
                    badges=badges,
                    metadata={
                        "app_id": raw.get("app_id"),
                        "file_type": raw.get("file_type", "lua"),
                        "branch": raw.get("branch", "public"),
                    }
                )
                fixes.append(fix)
            
            logger.info(f"Ryuu: Found {len(fixes)} fixes for '{query}'")
            return fixes
            
        except Exception as e:
            logger.warning(f"Ryuu search failed for '{query}': {e}")
            return []
    
    async def download_fix(self, fix: FixInfo, dest_dir) -> str:
        """Download Ryuu fix ZIP."""
        import httpx
        import tempfile
        from pathlib import Path
        from src.config.settings import SettingsManager
        
        url = fix.url
        if not url:
            raise ValueError("Ryuu fix has no download URL")
        
        dest_path = Path(dest_dir) / f"ryuu_fix_{fix.metadata.get('app_id', 'unknown')}.zip"
        
        headers = {}
        ryuu_key = SettingsManager.get("ryuu_api_key", "").strip()
        if ryuu_key:
            headers["X-Auth-Key"] = ryuu_key
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=120.0, headers=headers) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            dest_path.write_bytes(resp.content)
        
        logger.info(f"Ryuu: Downloaded fix to {dest_path}")
        return str(dest_path)