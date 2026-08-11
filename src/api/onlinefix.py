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


def _normalize(s: str) -> str:
    """Arama/karsilastirma icin sadece alfanumerik karakterler birakir."""
    return re.sub(r"[\W_]+", "", s.lower())


def _search_match(query: str, url: str, title: str) -> bool:
    """
    Sorgu kelimelerinin tamaminin slug veya baslik kelimelerinde gecip
    gecmedigini kontrol eder. Boylece DLE'nin alakasiz sonuclari ("R.E.P.O."
    icin "report" iceren oyunlar gibi) elenir, cok kelimeli oyun adlari
    ("Hollow Knight") ise bulunur.
    """
    q_words = [_normalize(w) for w in query.split()]
    q_words = [w for w in q_words if w]
    if not q_words:
        return False
    slug_words = {_normalize(w) for w in url.rsplit("/", 1)[-1].replace(".html", "").split("-")}
    title_words = {_normalize(w) for w in re.split(r"[\W_]+", html.unescape(title))}
    return all(w in slug_words or w in title_words for w in q_words)


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

        Ornek:
            search_game("PEAK") -> [
                {"title": "PEAK", "url": "https://online-fix.me/games/adventures/17801-peak-po-seti.html"},
                ...
            ]

        DLE noktali sorgularda ("R.E.P.O." gibi) alakasiz sonuclar doner ve
        arama buyuk/kucuk harfe duyarlidir; bu yuzden oncelikle ham sorgu
        gonderilir, sonuclar _search_match ile slug/baslik uzerinden filtrelenir.
        Ilk deneme sonucsuz kalirsa normalize (temiz) sorgu ile bir kez daha denenir.
        """
        # DLE buyuk/kucuk harfe duyarlidir ve noktali sorgulari ("R.E.P.O.")
        # cozemediginde sonuclari bos gosterir; temiz buyuk harf sorgu
        # ("REPO") ise dogru sonucu bulur. Site ardisik aramalari
        # rate-limit'ledigi icin once en cok isabet eden temiz sorgu denenir;
        # olmazsa ham sorgu (cok kelimeli oyunlar icin) denenecektir.
        attempts: List[str] = []
        clean = _normalize(query).upper()
        if clean:
            attempts.append(clean)
        if query != clean:
            attempts.append(query)
        items: List[Dict] = []
        for idx, attempt in enumerate(attempts):
            if idx > 0:
                await asyncio.sleep(3.0)
            url = SEARCH_URL.format(query=quote(attempt))
            client = self._get_client()
            try:
                resp = await client.get(url, headers={"Referer": ONLINEFIX_BASE + "/"})
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise OnlineFixError(f"Search failed HTTP {e.response.status_code}") from e
            except httpx.RequestError as e:
                raise OnlineFixError(f"Search network error: {e}") from e

            items = self._parse_search_items(resp.text)
            items = [it for it in items if _search_match(query, it["url"], it["title"])]
            if items:
                break
        return items[:limit]

    def _parse_search_items(self, html_text: str) -> List[Dict]:
        items: List[Dict] = []
        seen = set()
        for url_match, title in _SEARCH_ITEM_RE.findall(html_text):
            if url_match in seen:
                continue
            seen.add(url_match)
            items.append({"title": html.unescape(title).strip(), "url": url_match})
        return items

    # ------------------------------------------------------------------ #
    # 2. Oyun sayfasindan baslik + hosters linkini bulma
    # ------------------------------------------------------------------ #
    async def get_game_page(self, game_url: str) -> Dict:
        """
        Oyun sayfasini ceker; {'title', 'hoster_link'} dondurur.

        title, sayfanin <title> etiketidir ve arayuzde oyun eslesmesini
        dogrulamak icin kullanilir (yanlis fix cekme riskine karsi).
        """
        client = self._get_client()
        try:
            resp = await client.get(game_url, headers={"Referer": ONLINEFIX_BASE + "/"})
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise OnlineFixError(f"Game page failed HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise OnlineFixError(f"Game page network error: {e}") from e

        title = ""
        m = _GAME_TITLE_RE.search(resp.text)
        if m:
            title = html.unescape(m.group(1)).strip()

        links = _HOSTER_LINK_RE.findall(resp.text)
        return {
            "title": title,
            "hoster_link": links[0] if links else None,
        }

    async def get_hoster_link(self, game_url: str) -> Optional[str]:
        """get_game_page'in kisa yolu: sadece hosters baglantisini dondurur."""
        page = await self.get_game_page(game_url)
        return page.get("hoster_link")

    # ------------------------------------------------------------------ #
    # 3. Hosters sayfasindan data-links parse
    # ------------------------------------------------------------------ #
    async def get_fix_entries(self, game_name: str) -> List[Dict]:
        """
        Hosters sayfasini ceker ve tum dosya seceneklerini dondurur.

        Her kayit: {"file_name", "direct_link", "id", "is_dangerous", "hoster"}
        Referer zorunludur; referer'siz istek 401 "Not Authorized" doner.
        """
        url = f"{HOSTERS_BASE}/{quote(game_name)}"
        client = self._get_client()
        try:
            resp = await client.get(url, headers={"Referer": ONLINEFIX_BASE + "/"})
            if resp.status_code in (401, 403):
                raise OnlineFixNotFoundError(
                    f"Hoster sayfasi erisime kapali ({resp.status_code}): {game_name}"
                )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise OnlineFixError(f"Hoster page failed HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise OnlineFixError(f"Hoster page network error: {e}") from e

        blocks = _BLOCK_RE.findall(resp.text)
        # Attribute sirasi farkliysa fallback: hoster adi bilinmez olur.
        if not blocks:
            blocks = [(links, "?") for links in _LINKS_FALLBACK_RE.findall(resp.text)]

        entries: List[Dict] = []
        for links_json, hoster in blocks:
            try:
                links = json.loads(links_json)
            except json.JSONDecodeError:
                continue
            for link in links:
                if not isinstance(link, dict) or not link.get("direct_link"):
                    continue
                entries.append({
                    "file_name": link.get("file_name", ""),
                    "direct_link": link.get("direct_link", ""),
                    "id": link.get("id"),
                    "is_dangerous": bool(link.get("is_dangerous", False)),
                    "hoster": hoster.strip(),
                })
        return entries

    # ------------------------------------------------------------------ #
    # 4. Fix dosyasini secme
    # ------------------------------------------------------------------ #
    @staticmethod
    def pick_fix(entries: List[Dict]) -> Optional[Dict]:
        """
        Fix arsvini secer:
        - file_name icinde "fix" veya "repair" gecenler onceliklidir
        - is_dangerous olanlar atlanir
        - birden fazla aday varsa HOSTER_PRIORITY sirayla kullanilir
        """
        candidates = [
            e for e in entries
            if not e.get("is_dangerous")
            and re.search(r"fix|repair", e.get("file_name", ""), re.IGNORECASE)
        ]
        if not candidates:
            candidates = [e for e in entries if not e.get("is_dangerous")]
        if not candidates:
            return None

        def rank(entry: Dict) -> int:
            host = urlparse(entry.get("direct_link", "")).netloc
            for i, pref in enumerate(HOSTER_PRIORITY):
                if pref in host:
                    return i
            return len(HOSTER_PRIORITY)

        candidates.sort(key=rank)
        return candidates[0]

    # ------------------------------------------------------------------ #
    # 5. Hoster direkt link cozumu
    # ------------------------------------------------------------------ #
    @staticmethod
    async def resolve_direct(entry: Dict) -> Tuple[str, Optional[Dict]]:
        """
        Hoster baglantisini dogrudan indirilebilir URL'ye cevirir.
        (url, cookies) dondurur; cookies indirme sirasinda gerekiyorsa eklenir.
        """
        raw = entry.get("direct_link", "")
        host = urlparse(raw).netloc.lower()

        if "pixeldrain.com" in host:
            # https://pixeldrain.com/u/{id} -> https://pixeldrain.com/api/file/{id}
            match = re.search(r"/u/([A-Za-z0-9]+)", raw)
            if not match:
                raise OnlineFixError(f"Pixeldrain link cozulemedi: {raw}")
            return f"https://pixeldrain.com/api/file/{match.group(1)}", None

        if "gofile.io" in host:
            return await OnlineFixClient._resolve_gofile(raw)

        if "fileditch" in host:
            return raw, None

        # Bilinmeyen hoster: linki oldugu gibi dene.
        return raw, None

    @staticmethod
    async def _resolve_gofile(gofile_url: str) -> Tuple[str, Optional[Dict]]:
        """
        GoFile klasor linkini direkt dosya linkine cevirir.
        Guest token olusturur, klasor icerigini listeler ve ilk dosyayi secer.
        Premium-kilitli klasorlerde OnlineFixBlockedError firlatir.
        """
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            try:
                acc = await client.post(
                    "https://api.gofile.io/accounts",
                    json={},
                    headers={"User-Agent": USER_AGENT},
                )
                acc.raise_for_status()
                token = acc.json().get("data", {}).get("token", "")
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                raise OnlineFixBlockedError(f"GoFile token alinamadi: {e}") from e

            match = re.search(r"/d/([A-Za-z0-9]+)", gofile_url)
            if not match:
                raise OnlineFixError(f"GoFile link cozulemedi: {gofile_url}")
            content_id = match.group(1)

            try:
                resp = await client.get(
                    f"https://api.gofile.io/contents/{content_id}",
                    headers={
                        "User-Agent": USER_AGENT,
                        "Authorization": f"Bearer {token}",
                    },
                )
                if resp.status_code == 401:
                    raise OnlineFixBlockedError(
                        "GoFile klasoru erisime kapali (premium gerektiriyor olabilir)."
                    )
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise OnlineFixBlockedError(f"GoFile icerik hatasi: {e}") from e
            except httpx.RequestError as e:
                raise OnlineFixError(f"GoFile icerik network hatasi: {e}") from e

            data = resp.json().get("data", {})
            children = data.get("children", {})
            files = [c for c in children.values() if c.get("type") == "file"]
            if not files:
                raise OnlineFixNotFoundError("GoFile klasorunde dosya bulunamadi.")

            target = sorted(files, key=lambda f: f.get("size", 0))[0]
            server = data.get("server", "")
            name = target.get("name", "file")
            if server:
                return f"https://{server}.gofile.io/download/{content_id}/{quote(name)}", None
            return target.get("link", ""), None

    # ------------------------------------------------------------------ #
    # 6. Indirme
    # ------------------------------------------------------------------ #
    async def download(
        self,
        url: str,
        dest_path: str,
        cookies: Optional[Dict] = None,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """
        Dosyayi streaming olarak indirir. progress_cb(downloaded, total)
        olarak cagrilir. Bitince dest_path'i dondurur.
        """
        import os

        headers = {"Referer": HOSTERS_BASE + "/"}
        client = self._get_client()
        try:
            async with client.stream("GET", url, headers=headers, cookies=cookies) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                downloaded = 0
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(1024 * 256):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_cb:
                            progress_cb(downloaded, total)
        except httpx.HTTPStatusError as e:
            raise OnlineFixError(f"Download failed HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise OnlineFixError(f"Download network error: {e}") from e

        if os.path.getsize(dest_path) < 10 * 1024:
            raise OnlineFixError("Indirilen dosya gecersiz (10KB alti). Hoster engellemis olabilir.")
        return dest_path


# Global instance for easy access across the application
onlinefix_api = OnlineFixClient()
