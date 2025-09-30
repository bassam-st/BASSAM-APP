# core/search.py — Meta search (DDG + Google + Bing + Brave) with graceful fallback
from typing import List, Dict, Optional
import os, hashlib
import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"

def _clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script","style","noscript"]):
        tag.decompose()
    return " ".join(soup.get_text(" ").split())

def _fetch_snippet(url: str, timeout: float = 8.0) -> str:
    try:
        with httpx.Client(headers={"User-Agent": UA}, timeout=timeout, follow_redirects=True) as c:
            r = c.get(url)
        if r.status_code >= 400 or not r.text:
            return ""
        return _clean_text(r.text)[:600]
    except Exception:
        return ""

def _dedup(items: List[Dict]) -> List[Dict]:
    seen = set()
    out = []
    for it in items:
        u = (it.get("url") or "").strip()
        if not u:
            continue
        key = hashlib.md5(u.encode("utf-8")).hexdigest()
        if key in seen: 
            continue
        seen.add(key)
        out.append(it)
    return out

# ---------------------------
# 1) DuckDuckGo (free)
# ---------------------------
def _ddg_search(query: str, max_results: int = 8) -> List[Dict]:
    out: List[Dict] = []
    try:
        with DDGS() as ddgs:
            for h in ddgs.text(query, region="wt-wt", safesearch="moderate", max_results=max_results):
                url = h.get("href") or h.get("url") or ""
                title = h.get("title") or h.get("source") or url
                snippet = h.get("body") or ""
                if not snippet:
                    snippet = _fetch_snippet(url)
                if url:
                    out.append({"title": title, "url": url, "snippet": snippet})
    except Exception as e:
        print(f"[DDG ERROR] {e}")
    return out

# ---------------------------
# 2) Google via Serper.dev (optional API)
#    set env: SERPER_API_KEY=xxxxxxxx
# ---------------------------
def _google_serper(query: str, max_results: int = 8) -> List[Dict]:
    key = os.getenv("SERPER_API_KEY", "").strip()
    if not key:
        return []
    url = "https://google.serper.dev/search"
    try:
        payload = {"q": query, "num": max_results, "gl": "sa", "hl": "ar"}
        headers = {"X-API-KEY": key, "Content-Type": "application/json", "User-Agent": UA}
        r = httpx.post(url, json=payload, headers=headers, timeout=12.0)
        r.raise_for_status()
        data = r.json()
        items = data.get("organic", []) or []
        out = []
        for it in items[:max_results]:
            link = it.get("link")
            title = it.get("title") or link
            snippet = it.get("snippet") or _fetch_snippet(link)
            if link:
                out.append({"title": title, "url": link, "snippet": snippet})
        return out
    except Exception as e:
        print(f"[GOOGLE SERPER ERROR] {e}")
        return []

# ---------------------------
# 3) Bing (optional API)
#    set env: BING_API_KEY=xxxxxxxx
# ---------------------------
def _bing_search(query: str, max_results: int = 8) -> List[Dict]:
    key = os.getenv("BING_API_KEY", "").strip()
    if not key:
        return []
    endpoint = "https://api.bing.microsoft.com/v7.0/search"
    try:
        params = {"q": query, "mkt": "ar-SA", "count": max_results}
        headers = {"Ocp-Apim-Subscription-Key": key, "User-Agent": UA}
        r = httpx.get(endpoint, params=params, headers=headers, timeout=12.0)
        r.raise_for_status()
        web = (r.json() or {}).get("webPages", {}).get("value", [])
        out = []
        for it in web[:max_results]:
            link = it.get("url")
            title = it.get("name") or link
            snippet = it.get("snippet") or _fetch_snippet(link)
            if link:
                out.append({"title": title, "url": link, "snippet": snippet})
        return out
    except Exception as e:
        print(f"[BING ERROR] {e}")
        return []

# ---------------------------
# 4) Brave Search (optional API)
#    set env: BRAVE_API_KEY=xxxxxxxx
# ---------------------------
def _brave_search(query: str, max_results: int = 8) -> List[Dict]:
    key = os.getenv("BRAVE_API_KEY", "").strip()
    if not key:
        return []
    endpoint = "https://api.search.brave.com/res/v1/web/search"
    try:
        headers = {"Accept": "application/json", "X-Subscription-Token": key, "User-Agent": UA}
        params = {"q": query, "count": max_results, "country": "sa", "safesearch": "moderate"}
        r = httpx.get(endpoint, headers=headers, params=params, timeout=12.0)
        r.raise_for_status()
        web = (r.json() or {}).get("web", {}).get("results", [])
        out = []
        for it in web[:max_results]:
            link = it.get("url")
            title = it.get("title") or link
            snippet = (it.get("description") or "")[:600]
            if not snippet and link:
                snippet = _fetch_snippet(link)
            if link:
                out.append({"title": title, "url": link, "snippet": snippet})
        return out
    except Exception as e:
        print(f"[BRAVE ERROR] {e}")
        return []

# ---------------------------
# Public entry
# ---------------------------
def deep_search(query: str, include_prices: bool = False, include_images: bool = False) -> List[Dict]:
    """
    يبحث في عدة محركات (حسب المتاح):
    - DuckDuckGo (دائمًا)
    - Google (Serper) اختياري
    - Bing اختياري
    - Brave اختياري
    ويرجع: [{"title","url","snippet"}]
    """
    query = (query or "").strip()
    if not query:
        return []

    q = query
    if include_prices:
        q = f"{query} site:amazon.com OR site:aliexpress.com OR site:noon.com OR site:souq.com"

    results: List[Dict] = []
    # تشغيل المتوفر — ترتيب يمزج جوجل/بينغ/بريف مع DDG
    results += _google_serper(q, 6)
    results += _bing_search(q, 6)
    results += _brave_search(q, 6)
    # دائمًا DDG (مجانًا)
    results += _ddg_search(q, 8)

    return _dedup(results)
