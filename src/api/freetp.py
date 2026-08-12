"""
FreeTP.org Scraper API for fetching game versions and multiplayer fixes.
"""
import re
import httpx
import html as html_lib
from typing import Optional, Dict, Tuple
from pathlib import Path

FREETP_BASE = "https://freetp.org"

# Extracts versions like v1.8.6, 1.8.6, build 1234
_VERSION_RE = re.compile(r"(?:v\.?|version|build)?\s*(\d+(?:\.\d+)*[a-zA-Z]*)", re.IGNORECASE)


def _score_title_match(query: str, title: str) -> int:
    """Calculates relevance score. Exact title match yields highest score."""
    clean_q = re.sub(r"[\W_]+", "", query.lower())
    clean_t = re.sub(r"[\W_]+", "", html_lib.unescape(title).lower())

    for suffix in [
        "игратьпосетииинтернетуонлайн",
        "игратьпосетибесплатноонлайн",
        "игратьпосети",
        "посетииинтернетуонлайн",
        "посети",
        "online"
    ]:
        clean_t = clean_t.replace(suffix, "")

    if clean_t == clean_q:
        return 1000  # Exact match!
    if clean_t.startswith(clean_q):
        return 500 - len(clean_t)
    if clean_q in clean_t:
        return 100 - len(clean_t)
    return 0


class FreeTPClient:
    def __init__(self):
        self._client = httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=15.0,
            verify=False
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
            return matches[-1]
        return "0.0.0"

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
            candidates = []

            matches = re.finditer(
                r'<div class="heading">.*?<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a></div>',
                html,
                re.IGNORECASE | re.DOTALL
            )
            for m in matches:
                url = m.group(1)
                title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
                title = html_lib.unescape(title)
                score = _score_title_match(query, title)
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
            title_match = re.search(r'<title[^>]*>(.*?)</title>', page_html, re.IGNORECASE | re.DOTALL)
            if title_match:
                full_title = html_lib.unescape(title_match.group(1)).strip()
                version = self._extract_version(full_title)

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
                    version = self._extract_version(best_title)

            return {"url": best_url, "version": version, "title": best_title}
        except Exception as e:
            print(f"FreeTP search error: {e}")
            return None

    async def download_fix(self, article_url: str, dest_dir: Path) -> Optional[Path]:
        """Downloads the fix .exe from the given article URL."""
        try:
            resp = await self._client.get(article_url)
            html = resp.content.decode('cp1251', errors='replace')

            fix_link = None
            getfile_links = []
            matches = re.finditer(
                r'<a[^>]+href=["\'](/getfile-[^"\']+)["\'][^>]*>(.*?)</a>',
                html,
                re.IGNORECASE | re.DOTALL
            )
            for m in matches:
                href = m.group(1)
                text = re.sub(r'<[^>]+>', '', m.group(2)).strip().lower()
                getfile_links.append(href)
                if "fix" in text or "фикс" in text or "multiplayer" in text:
                    fix_link = href
                    break

            if not fix_link:
                if len(getfile_links) >= 2:
                    fix_link = getfile_links[1]
                elif len(getfile_links) == 1:
                    fix_link = getfile_links[0]
                else:
                    return None

            download_page_url = FREETP_BASE + fix_link if fix_link.startswith('/') else fix_link

            dp_resp = await self._client.get(download_page_url)
            dp_html = dp_resp.content.decode('cp1251', errors='replace')

            m = re.search(r'name="id"\s+value="(\d+)"', dp_html)
            if not m:
                return None

            file_id = m.group(1)
            download_url = f"{FREETP_BASE}/engine/download.php?id={file_id}"

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
