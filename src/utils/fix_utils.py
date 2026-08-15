"""
Shared utilities for fix providers (OnlineFix, FreeTP, Ryuu).
Eliminates code duplication across providers.
"""
import re
import html as html_lib


# Extracts versions like v1.8.6, 1.8.6, build 1234
_VERSION_RE = re.compile(r"(?:v\.?|version|build)?\s*(\d+(?:\.\d+)*[a-zA-Z]*)", re.IGNORECASE)


def extract_version(text: str) -> str:
    """Extracts version string from text. Returns '0.0.0' if not found."""
    matches = _VERSION_RE.findall(text)
    if matches:
        return matches[-1]
    return "0.0.0"


def normalize_string(s: str) -> str:
    """Keeps only alphanumeric characters for comparison."""
    return re.sub(r"[\W_]+", "", s.lower())


def score_title_match(query: str, title: str) -> int:
    """
    Calculates relevance score for title matching.
    Exact match: 1000, Prefix match: 500-len, Contains: 100-len, No match: 0.
    """
    clean_q = normalize_string(query)
    clean_t = normalize_string(html_lib.unescape(title))

    # Remove common Russian suffixes from FreeTP/OnlineFix titles
    for suffix in [
        "игратьпосетииинтернетуонлайн",
        "игратьпосетибесплатноонлайн",
        "игратьпосети",
        "посетииинтернетуонлайн",
        "посети",
        "online",
    ]:
        clean_t = clean_t.replace(suffix, "")

    if clean_t == clean_q:
        return 1000  # Exact match!
    if clean_t.startswith(clean_q):
        return 500 - len(clean_t)
    if clean_q in clean_t:
        return 100 - len(clean_t)
    return 0


def search_match(query: str, url: str, title: str) -> bool:
    """
    Checks if all query words appear in URL slug or title.
    Used for fallback broad matching.
    """
    q_words = [normalize_string(w) for w in query.split()]
    q_words = [w for w in q_words if w]
    if not q_words:
        return False
    slug_words = {normalize_string(w) for w in url.rsplit("/", 1)[-1].replace(".html", "").split("-")}
    title_words = {normalize_string(w) for w in re.split(r"[\W_]+", html_lib.unescape(title))}
    return all(w in slug_words or w in title_words for w in q_words)