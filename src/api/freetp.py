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
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=15.0,
            verify=False
        )

    async def close(self):
        await self._client.aclose()

    async def search_game(self, query: str) -> Optional[Dict[str, str]]:
        """Searches FreeTP and returns the most relevant matched article info: url, version, title."""
        data = {
            "do": "search",
            "subaction": "search",
            "story": query
        }

        try:
            resp = await self._client.post(f"{FREETP_BASE}/index.php?do=search", data=data)
            resp.raise_for_status()
            html = resp.content.decode('cp1251', errors='replace')

            # Search results: <a href="...html"><h2 class="title">Game Name</h2></a>
            _SEARCH_ITEM_RE = re.compile(
                r'<a href="(https://freetp\.org/[^"]+\.html)"><h2 class="title">\s*(.*?)\s*</h2></a>',
                re.S,
            )
            matches = _SEARCH_ITEM_RE.finditer(html)
            candidates = []
            for m in matches:
                url = m.group(1)
                title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
                title = html_lib.unescape(title)
                score = score_title_match(query, title)
                if score > 0:
                    candidates.append((score, url, title))

            if not candidates:
                return None

            # Sort so the exact/best match is index 0
            candidates.sort(key=lambda c: c[0], reverse=True)
            best_score, best_url, best_title = candidates[0]

            # Fetch the actual article page to get the version
            page_resp = await self._client.get(best_url)
            page_html = page_resp.content.decode('cp1251', errors='replace')

            version = "0.0.0"
            _TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
            title_match = _TITLE_RE.search(page_html)
            if title_match:
                full_title = html_lib.unescape(title_match.group(1)).strip()
                version = extract_version(full_title)

            if version == "0.0.0":
                torrent_m = re.search(r'href=["\'][^"\']*?([^/"\']+\.torrent)["\']', page_html, re.IGNORECASE)
                if torrent_m:
                    torrent_name = torrent_m.group(1)
                    ver_m = re.search(r'v[\.\-]?(\d+(?:\.\d+)+)', torrent_name, re.IGNORECASE)
                    if ver_m:
                        version = ver_m.group(1)

            if version == "0.0.0":
                v_match = re.search(r'Версия игры:[^<]*?(\d+[\.\d]*[a-zA-Z]*)', page_html, re.IGNORECASE)
                if not v_match:
                    v_match = re.search(r'v\.?(\d+(?:\.\d+)+)', page_html, re.IGNORECASE)
                if not v_match:
                    v_match = re.search(r'v\.?(\d+)', page_html, re.IGNORECASE)
                if v_match:
                    version = v_match.group(1)
                else:
                    version = extract_version(best_title)

            return {"url": best_url, "version": version, "title": best_title}
        except Exception as e:
            print(f"FreeTP search error: {e}")
            return None

    async def download_fix(self, article_url: str, dest_dir: Path) -> Optional[Path]:
        """Downloads the fix .exe from the given article URL."""
        try:
            resp = await self._client.get(article_url)
            resp.raise_for_status()
            page_html = resp.content.decode('cp1251', errors='replace')

            # Find download link - typically a torrent or direct link
            _DOWNLOAD_RE = re.compile(r'href=["\']([^"\']*(?:download|torrent|fix)[^"\']*)["\']', re.IGNORECASE)
            matches = _DOWNLOAD_RE.findall(page_html)
            if not matches:
                return None

            # Prefer torrent files
            download_url = None
            for m in matches:
                if m.endswith('.torrent'):
                    download_url = m
                    break
            if not download_url:
                download_url = matches[0]

            if not download_url.startswith('http'):
                from urllib.parse import urljoin
                download_url = urljoin(article_url, download_url)

            # Download the file
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / Path(download_url).name

            async with self._client.stream("GET", download_url, timeout=60.0) as resp:
                resp.raise_for_status()
                with open(dest_file, "wb") as f:
                    async for chunk in resp.aiter_bytes(8192):
                        f.write(chunk)

            return dest_file

        except Exception as e:
            print(f"FreeTP download error: {e}")
            return None


freetp_api = FreeTPClient()