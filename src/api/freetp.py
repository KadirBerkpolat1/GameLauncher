"""
FreeTP.org Scraper API for fetching game versions and multiplayer fixes.
"""
import re
import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import Optional, Dict, Tuple
from pathlib import Path

FREETP_BASE = "https://freetp.org"

# Extracts versions like v1.8.6, 1.8.6, build 1234
_VERSION_RE = re.compile(r"(?:v\.?|version|build)?\s*(\d+(?:\.\d+)*[a-zA-Z]*)", re.IGNORECASE)

class FreeTPClient:
    def __init__(self):
        self._client = httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=15.0,
            verify=False # In case of SSL issues
        )

    async def close(self):
        await self._client.aclose()

    def _normalize(self, s: str) -> str:
        """Keep only alphanumerics for title matching."""
        return re.sub(r"[\W_]+", "", s.lower())

    def _extract_version(self, text: str) -> str:
        """Finds the version string in a title, e.g. 'Chained Together v1.8.6' -> '1.8.6'"""
        matches = _VERSION_RE.findall(text)
        if matches:
            # Usually the last number sequence in the title is the version, or the longest one
            return matches[-1]
        return "0.0.0"

    async def search_game(self, query: str) -> Optional[Dict[str, str]]:
        """Searches FreeTP and returns the first matched article info: url, version."""
        data = {
            "do": "search",
            "subaction": "search",
            "story": query
        }
        
        try:
            resp = await self._client.post(f"{FREETP_BASE}/index.php?do=search", data=data)
            resp.raise_for_status()
            
            # The HTML is encoded in cp1251
            html = resp.content.decode('cp1251', errors='replace')
            soup = BeautifulSoup(html, 'html.parser')
            
            query_norm = self._normalize(query)
            
            for item in soup.find_all('div', class_='heading'):
                a_tag = item.find('a')
                if not a_tag:
                    continue
                    
                title = a_tag.text.strip()
                url = a_tag['href']
                
                # Check if the title actually matches the query
                title_norm = self._normalize(title)
                if query_norm in title_norm:
                    version = self._extract_version(title)
                    return {"url": url, "version": version, "title": title}
            
            return None
            
        except Exception as e:
            print(f"FreeTP search error: {e}")
            return None

    async def download_fix(self, article_url: str, dest_dir: Path) -> Optional[Path]:
        """Downloads the fix .exe from the given article URL."""
        try:
            resp = await self._client.get(article_url)
            html = resp.content.decode('cp1251', errors='replace')
            soup = BeautifulSoup(html, 'html.parser')
            
            fix_link = None
            # Find the download link for the fix (usually contains 'Fix' or 'Multiplayer')
            for a in soup.find_all('a'):
                href = a.get('href', '')
                text = a.text.lower()
                if "getfile" in href and ("fix" in text or "фикс" in text):
                    fix_link = href
                    break
            
            if not fix_link:
                # Fallback: maybe just take the second getfile link? The first is usually the game torrent.
                getfile_links = [a.get('href') for a in soup.find_all('a') if "getfile" in a.get('href', '')]
                if len(getfile_links) >= 2:
                    fix_link = getfile_links[1]
                else:
                    return None

            download_page_url = FREETP_BASE + fix_link if fix_link.startswith('/') else fix_link
            
            # Fetch the download page to get the actual file ID for engine/download.php
            dp_resp = await self._client.get(download_page_url)
            dp_html = dp_resp.content.decode('cp1251', errors='replace')
            
            # Extract ID: <input type="hidden" name="id" value="15424">
            m = re.search(r'name="id"\s+value="(\d+)"', dp_html)
            if not m:
                return None
                
            file_id = m.group(1)
            download_url = f"{FREETP_BASE}/engine/download.php?id={file_id}"
            
            # Download the actual file. Referer MUST be the download page!
            headers = {"Referer": download_page_url}
            exe_resp = await self._client.get(download_url, headers=headers, follow_redirects=True)
            
            if exe_resp.status_code != 200:
                return None
                
            dest_file = dest_dir / f"freetp_fix_{file_id}.exe"
            dest_file.write_bytes(exe_resp.content)
            
            return dest_file
            
        except Exception as e:
            print(f"FreeTP download error: {e}")
            return None

freetp_api = FreeTPClient()
