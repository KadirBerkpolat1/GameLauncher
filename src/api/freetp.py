"""
FreeTP.org Scraper API for fetching game versions and multiplayer fixes.
"""
import re
import httpx
import html as html_lib
from typing import Optional, Dict, Tuple
from pathlib import Path

from src.utils.fix_utils import (
    extract_version,
    normalize_string,
    score_title_match,
)

FREETP_BASE = "https://freetp.org"


class FreeTPClient:
    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        )

    async def close(self):
        await self._client.aclose()

    async def search_game(self, query: str) -> Optional[Dict[str, str]]:
        """Searches FreeTP and returns the most relevant matched article info: url, version, title."""
        data = {
            "do": "search",
            "subaction": "search",
            "search_start": 0,
            "full_search": 0,
            "result_from": 1,
            "story": query,
        }

        try:
            resp = await self._client.post(f"{FREETP_BASE}/index.php?do=search", data=data)
            resp.raise_for_status()
            page_html = resp.content.decode('cp1251', errors='replace')

            _ARTICLE_RE = re.compile(
                r'<a href="(https://freetp\.org/[^"]+\.html)"><h2[^>]*>\s*(.*?)\s*</h2></a>'
            )

            best_match = None
            best_score = -1

            for m in _ARTICLE_RE.finditer(page_html):
                url = m.group(1)
                title = html.unescape(m.group(2)).strip()
                score = score_title_match(query, title)
                if score > best_score:
                    best_score = score
                    best_match = {"url": url, "title": title}

            if not best_match:
                return None

            # Get version from article page
            article_resp = await self._client.get(best_match["url"])
            article_resp.raise_for_status()
            article_html = article_resp.content.decode('cp1251', errors='replace')
            version = extract_version(article_html)

            return {"url": best_match["url"], "version": version, "title": best_match["title"]}

        except Exception as e:
            print(f"FreeTP search error: {e}")
            return None

    async def download_fix(self, article_url: str, dest_dir: Path) -> Optional[Path]:
        """Downloads the fix (torrent) from the given article URL."""
        try:
            dest_dir = Path(dest_dir)
            dest_dir.mkdir(parents=True, exist_ok=True)

            # First, get the article page to find the download form
            resp = await self._client.get(article_url)
            resp.raise_for_status()
            page_html = resp.content.decode('cp1251', errors='replace')

            # Find the getfile link (e.g., /getfile-19906)
            getfile_match = re.search(r'href=["\']([^"\']*getfile-\d+)["\']', page_html, re.IGNORECASE)
            if not getfile_match:
                return None

            getfile_url = getfile_match.group(1)
            if not getfile_url.startswith('http'):
                from urllib.parse import urljoin
                getfile_url = urljoin(article_url, getfile_url)

            # Get the download page to find the form
            resp = await self._client.get(getfile_url)
            resp.raise_for_status()
            download_page_html = resp.content.decode('cp1251', errors='replace')

            # Extract form ID and area
            id_match = re.search(r'name="id"\s+value="(\d+)"', download_page_html)
            area_match = re.search(r'name="area"\s+value="([^"]*)"', download_page_html)

            if not id_match:
                return None

            form_id = id_match.group(1)
            form_area = area_match.group(1) if area_match else ""

            # POST to download.php
            download_data = {
                'id': form_id,
                'area': ''
            }

            headers = {
                'Referer': 'https://freetp.org/',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded',
            }

            download_resp = await self._client.post(
                'https://freetp.org/engine/download.php',
                data={'id': form_id, 'area': ''},
                headers={'Referer': 'https://freetp.org/', 'Content-Type': 'application/x-www-form-urlencoded'},
                follow_redirects=True
            )
            download_resp.raise_for_status()

            # Check if we got a torrent file
            content_type = download_resp.headers.get('Content-Type', '')
            content_disp = download_resp.headers.get('Content-Disposition', '')

            # Extract filename from Content-Disposition
            filename = "fix.torrent"
            if 'filename=' in content_disp:
                import re as _re
                fname_match = _re.search(r'filename[^;=\n]*=([\'"]?)([^;\'"]+)\1', content_disp)
                if fname_match:
                    filename = fname_match.group(2)

            dest_dir = Path(dest_dir)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / filename

            with open(dest_file, 'wb') as f:
                f.write(download_resp.content)

            return dest_file

        except Exception as e:
            print(f"FreeTP download error: {e}")
            return None

    async def close(self):
        await self._client.aclose()


freetp_api = FreeTPClient()