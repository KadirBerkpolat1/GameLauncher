"""
CrackBypass Provider - Integrates CrakFiles (KoriaPolis/CrakFiles) as fix source.
Fetches crackfiles.json from GitHub, downloads from buzzheavier.com.
"""
import logging
import httpx
import tempfile
import zipfile
import subprocess
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

# Optional dependencies
try:
    import rarfile
    HAS_RARFILE = True
except ImportError:
    HAS_RARFILE = False

try:
    import patoolib
    HAS_PATOOLIB = True
except ImportError:
    HAS_PATOOLIB = False

from src.api.fix_providers import FixProvider, FixInfo

logger = logging.getLogger(__name__)

CRAKFILES_JSON_URL = "https://raw.githubusercontent.com/KoriaPolis/CrakFiles/main/crackfiles.json"


class CrackBypassProvider(FixProvider):
    """CrakFiles provider with Crack/Online Fix/Bypass badges."""
    
    PRIORITY = 20  # After Ryuu, before OnlineFix
    NAME = "CrackBypass"
    SOURCE_NAME = "crackbypass"
    REQUIRES_AUTH = False
    
    def __init__(self):
        self._crackfiles_cache: Optional[List[Dict[str, Any]]] = None
        self._client: Optional[httpx.AsyncClient] = None
    
    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
            )
        return self._client
    
    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def _fetch_crackfiles(self) -> List[Dict[str, Any]]:
        """Fetch and cache crackfiles.json."""
        if self._crackfiles_cache is not None:
            return self._crackfiles_cache
        
        try:
            client = self._get_client()
            resp = await client.get(CRAKFILES_JSON_URL)
            resp.raise_for_status()
            data = resp.json()
            
            # Validate structure
            if isinstance(data, list):
                self._crackfiles_cache = data
                logger.info(f"CrackBypass: Loaded {len(data)} entries from crackfiles.json")
                return data
            else:
                logger.warning("CrackBypass: Unexpected JSON structure")
                self._crackfiles_cache = []
                return []
                
        except Exception as e:
            logger.warning(f"CrackBypass: Failed to fetch crackfiles.json: {e}")
            self._crackfiles_cache = []
            return []
    
    async def search_game(self, query: str) -> List[FixInfo]:
        """Search CrakFiles for game fixes."""
        try:
            all_entries = await self._fetch_crackfiles()
            if not all_entries:
                return []
            
            # Normalize query
            from src.utils.fix_utils import normalize_string, score_title_match
            clean_query = normalize_string(query)
            
            matches = []
            for entry in all_entries:
                name = entry.get("name", "")
                buildid = entry.get("buildid", "")
                
                # Score by name match
                score = score_title_match(query, name)
                
                # Bonus for buildid match if query contains numbers
                if buildid and any(c.isdigit() for c in query):
                    if normalize_string(buildid) in clean_query:
                        score += 500
                
                if score > 0:
                    matches.append((score, entry))
            
            # Sort by score descending
            matches.sort(key=lambda x: x[0], reverse=True)
            
            fixes = []
            for score, entry in matches[:10]:  # Limit results
                fixes_list = entry.get("fixes", [])
                for fix_entry in fixes_list:
                    badges = fix_entry.get("badges", [])
                    badge_labels = []
                    for b in badges:
                        b_lower = b.lower()
                        if "online" in b_lower:
                            badge_labels.append("Online Fix")
                        elif "bypass" in b_lower:
                            badge_labels.append("Bypass")
                        elif "crack" in b_lower:
                            badge_labels.append("Crack")
                        elif "dlc" in b_lower:
                            badge_labels.append("DLC Unlocker")
                        else:
                            badge_labels.append(b)
                    
                    fix = FixInfo(
                        source="crackbypass",
                        title=f"{entry['name']} - {fix_entry.get('filename', 'Fix')}",
                        version=entry.get("buildid", "1.0.0"),
                        url=fix_entry.get("href", ""),
                        badges=badge_labels,
                        metadata={
                            "game_name": entry["name"],
                            "buildid": entry.get("buildid"),
                            "source_crack": entry.get("source_crack", []),
                            "original_download": entry.get("original_download", []),
                            "fix_filename": fix_entry.get("filename"),
                            "fix_size": fix_entry.get("size"),
                            "fix_badges": fix_entry.get("badges", []),
                        }
                    )
                    fixes.append(fix)
            
            logger.info(f"CrackBypass: Found {len(fixes)} fixes for '{query}'")
            return fixes
            
        except Exception as e:
            logger.warning(f"CrackBypass search failed for '{query}': {e}")
            return []
    
    async def download_fix(self, fix: FixInfo, dest_dir) -> str:
        """Download fix from buzzheavier.com."""
        url = fix.url
        if not url:
            raise ValueError("CrackBypass fix has no download URL")
        
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        filename = fix.metadata.get("fix_filename", "fix_download")
        dest_path = dest_dir / filename
        
        # Download with proper headers for buzzheavier
        client = self._get_client()
        headers = {
            "Referer": "https://buzzheavier.com/",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }
        
        async with client.stream("GET", url, headers=headers, timeout=300.0) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                async for chunk in resp.aiter_bytes(8192):
                    f.write(chunk)
        
        logger.info(f"CrackBypass: Downloaded {dest_path} ({dest_path.stat().st_size} bytes)")
        
        # Extract if archive
        extracted = await self._extract_archive(dest_path, dest_dir)
        return extracted
    
    async def _extract_archive(self, archive_path: Path, dest_dir: Path) -> str:
        """Extract ZIP/RAR archive, handle passwords."""
        try:
            # Try patoolib first (handles multiple formats and passwords)
            import shutil
            extract_dir = dest_dir / "extracted"
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            extract_dir.mkdir(parents=True)
            
            # Common passwords used by CrakFiles
            passwords = [None, "online-fix.me", "crackfiles", "buzzheavier", "fitgirl", "codex", "cpY", "rld", "skidrow"]
            
            for password in passwords:
                try:
                    if password:
                        patoolib.extract_archive(str(archive_path), outdir=str(extract_dir), password=password)
                    else:
                        patoolib.extract_archive(str(archive_path), outdir=str(extract_dir))
                    logger.info(f"CrackBypass: Extracted with password={password}")
                    break
                except Exception as e:
                    if password is None or "password" in str(e).lower():
                        continue
                    # Other error, might be format issue
                    logger.debug(f"CrackBypass: Extract failed with password={password}: {e}")
            else:
                # If all passwords failed, try without password as last resort
                patoolib.extract_archive(str(archive_path), outdir=str(extract_dir))
            
            # Return the extracted directory path
            return str(extract_dir)
            
        except Exception as e:
            logger.warning(f"CrackBypass: Archive extraction failed: {e}")
            # Return original archive path if extraction fails
            return str(archive_path)
    
    async def get_badges(self, fix: FixInfo) -> List[str]:
        """Get badge labels from metadata."""
        return fix.badges