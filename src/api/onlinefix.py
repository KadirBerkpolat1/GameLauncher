"""
Online-Fix.Me entegrasyonu.

online-fix.me'de resmi bir API yoktur; fixlerin indirme linkleri oyun
sayfalarinda degil, ayri bir "hosters" servisinde durur. Akis:

 1. DLE search ile oyun URL'sini bul (oyun adiyla arama)
 2. Oyun sayfasindan https://hosters.online-fix.me:2053/<OyunAdi> linkini cek
 3. Hosters sayfasina Referer header'i ile git (referer'siz 401 doner)
 4. Sayfadaki data-links JSON'larindan "Fix"/"Repair" iceren dosyayi sec
 5. Hoster tipine gore direkt indirme linkini coz (Pixeldrain/GoFile/FileDitch)
 6. Arsviyi indir (parola her zaman: online-fix.me)

Not: Hosters sayfasinda is_dangerous=true isaretli hosterlar (VikingFile,
Rootz vb.) ucuncu taraf reklam/risk tasir; bunlar otomatik atlanir.
"""
import html
import json
import logging
import re
import asyncio
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import quote, urlparse

import httpx

from src.utils.fix_utils import (
    extract_version,
    normalize_string,
    score_title_match,
    search_match,
)

logger = logging.getLogger(__name__)

ONLINEFIX_BASE = "https://online-fix.me"
HOSTERS_BASE = "https://hosters.online-fix.me:2053"
SEARCH_URL = ONLINEFIX_BASE + "/index.php?do=search&subaction=search&story={query}"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

ARCHIVE_PASSWORD = "online-fix.me"

# Hosters sayfasindaki secim onceligi. Pixeldrain API'si stabil ve
# is_dangerous degil; gofile bazi klasorlerde premium ister.
HOSTER_PRIORITY = ["pixeldrain.com", "fileditch", "gofile.io"]

_BLOCK_RE = re.compile(
    r'<div\s+class="option[^"]*"\s+data-links=\'([^\']+)\'\s+data-id="\d+"[^>]*>([^<]+)</div>',
    re.DOTALL,
)
_LINKS_FALLBACK_RE = re.compile(r"data-links='([^']+)'")
_SEARCH_ITEM_RE = re.compile(
    r'<a href="(https://online-fix\.me/games/[^"]+\.html)"><h2 class="title">\s*(.*?)\s*</h2></a>',
    re.S,
)
_HOSTER_LINK_RE = re.compile(r'href="(https://hosters\.online-fix\.me:2053/[^"]+)"')
_GAME_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S)


class OnlineFixError(Exception):
    """Base exception for Online-Fix.Me errors."""


class OnlineFixNotFoundError(OnlineFixError):
    """Oyun veya fix bulunamadi."""


class OnlineFixBlockedError(OnlineFixError):
    """Hoster indirme icin kilitli (premium gerekiyor vb.)."""


class OnlineFixClient:
    """
    Async client for the Online-Fix.Me download flow.

    HubcapClient ile ayni deseni izler: lazy httpx client, acik hata tipleri.
    """

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT},
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ------------------------------------------------------------------ #
    # 1. Oyun URL'si bulma
    # ------------------------------------------------------------------ #
    async def search_game(self, query: str, limit: int = 10) -> List[Dict]:
        """
        DLE (DataLife Engine) search ile oyun arar.
        Donus: [{"url": "...", "title": "..."}, ...]
        """
        client = self._get_client()
        try:
            url = SEARCH_URL.format(query=quote(query))
            resp = await client.get(url)
            resp.raise_for_status()
            html_content = resp.text

            items = []
            for m in _SEARCH_ITEM_RE.finditer(html_content):
                url_match = m.group(1)
                title = html.unescape(m.group(2)).strip()
                if search_match(query, url_match, title):
                    items.append({"url": url_match, "title": title})
            return items[:limit]
        except httpx.HTTPError as e:
            logger.warning(f"OnlineFix search HTTP error: {e}")
            return []
        except Exception as e:
            logger.warning(f"OnlineFix search error: {e}")
            return []

    # ------------------------------------------------------------------ #
    # 2. Oyun sayfasindan hosters linki cekme
    # ------------------------------------------------------------------ #
    async def get_game_page(self, game_url: str) -> Dict:
        """Oyun sayfasini ceker, hosters linkini ve versiyonu cikarir."""
        client = self._get_client()
        try:
            resp = await client.get(game_url, headers={"Referer": ONLINEFIX_BASE})
            resp.raise_for_status()
            html_content = resp.text

            # Hosters linki
            hoster_match = _HOSTER_LINK_RE.search(html_content)
            hoster_url = hoster_match.group(1) if hoster_match else None

            # Versiyon
            version = "0.0.0"
            title_match = _GAME_TITLE_RE.search(html_content)
            if title_match:
                version = extract_version(title_match.group(1))

            return {"hoster_link": hoster_url, "version": version}
        except Exception as e:
            logger.warning(f"Failed to parse game page {game_url}: {e}")
            return {"hoster_link": None, "version": "0.0.0"}

    # ------------------------------------------------------------------ #
    # 3. Hosters sayfasindan fix secimi
    # ------------------------------------------------------------------ #
    async def get_fix_entries(self, game_name: str) -> List[Dict]:
        """Hosters sayfasindaki bloklari ceker ve oncelik siralar."""
        client = self._get_client()
        url = f"{HOSTERS_BASE}/{game_name}"
        try:
            # Referer ZORUNLU, yoksaydi 401 doner
            resp = await client.get(url, headers={"Referer": ONLINEFIX_BASE})
            resp.raise_for_status()
            html_content = resp.text

            entries = []
            for m in _BLOCK_RE.finditer(html_content):
                links_json = m.group(1)
                label = m.group(2).strip()
                # Accept all hosters (label is the hoster name like FileDitch, Pixeldrain, etc.)
                # The original filter looked for "fix" or "repair" in label but labels are hoster names
                try:
                    links = json.loads(html.unescape(links_json))
                except json.JSONDecodeError:
                    continue

                for link_data in links:
                    # JSON uses different keys: direct_link, file_name, id, is_dangerous
                    url = link_data.get("direct_link", link_data.get("url", ""))
                    host = urlparse(url).netloc.lower().replace("www.", "")
                    if any(h in host for h in HOSTER_PRIORITY):
                        entries.append({
                            "label": label,
                            "url": url,
                            "hoster": host,
                            "file_name": link_data.get("file_name", link_data.get("name", "")),
                            "file_size": link_data.get("size", link_data.get("id", 0)),
                        })
                        break  # only first good hoster per block
            # Sort by hoster priority
            priority_map = {h: i for i, h in enumerate(HOSTER_PRIORITY)}
            entries.sort(key=lambda e: priority_map.get(e["hoster"], 99))
            return entries
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise OnlineFixNotFoundError(f"Hosters page not found for {game_name}")
            raise
        except Exception as e:
            logger.warning(f"Failed to get fix entries: {e}")
            return []

    @staticmethod
    def pick_fix(entries: List[Dict]) -> Optional[Dict]:
        """Returns the highest priority fix entry."""
        return entries[0] if entries else None

    # ------------------------------------------------------------------ #
    # 4. Direct download link cozumu
    # ------------------------------------------------------------------ #
    async def resolve_direct(self, fix_entry: Dict) -> Tuple[str, Optional[Dict]]:
        """Hoster URL'sini cozer: Pixeldrain/GoFile/FileDitch -> direct link."""
        url = fix_entry["url"]
        host = fix_entry["hoster"]

        client = self._get_client()
        if "pixeldrain.com" in host:
            # https://pixeldrain.com/u/FILE_ID -> https://pixeldrain.com/api/file/FILE_ID
            file_id = url.rsplit("/", 1)[-1]
            return f"https://pixeldrain.com/api/file/{file_id}", None
        elif "gofile.io" in host:
            # https://gofile.io/d/CODE -> API call
            code = url.rsplit("/", 1)[-1]
            api_url = f"https://api.gofile.io/getContent?contentId={code}"
            resp = await client.get(api_url)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "ok":
                children = data.get("data", {}).get("contents", {})
                for child in children.values():
                    if child.get("type") == "file":
                        return child["link"], None
            raise OnlineFixBlockedError("GoFile link could not be resolved")
        elif "fileditch" in host:
            # FileDitch usually direct
            return url, None
        else:
            raise OnlineFixBlockedError(f"Unsupported hoster: {host}")

    async def download(self, direct_url: str, dest_path: str, cookies: Optional[Dict] = None) -> None:
        """Downloads the fix archive to dest_path."""
        client = self._get_client()
        async with client.stream("GET", direct_url, cookies=cookies, timeout=120.0) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                async for chunk in resp.aiter_bytes(8192):
                    f.write(chunk)


# Global instance for easy access across the application
onlinefix_api = OnlineFixClient()