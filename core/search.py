# core/search.py — نسخة مطورة (بحث عميق + فتح الروابط الأصلية مباشرة)
from typing import List, Dict, Optional
import requests, re
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import urllib.parse

# تهيئة بسيطة
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
}

def _norm_item(title: str, url: str, snippet: str = "") -> Dict:
    """تنسيق موحد للنتائج"""
    return {
        "title": (title or url or "").strip(),
        "url": url.strip(),
        "snippet": (snippet or "").strip()
    }

def _clean_duckduckgo_url(u: str) -> str:
    """تحويل روابط DuckDuckGo إلى الروابط الأصلية"""
    if "duckduckgo.com/l/?" in u and "uddg=" in u:
        try:
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(u).query)
            return urllib.parse.unquote(parsed.get("uddg", [""])[0])
        except Exception:
            return u
    return u

def _ddg_api(q: str, max_results: int = 12) -> List[Dict]:
    """بحث عبر واجهة DuckDuckGo المجانية"""
    out = []
    try:
        with DDGS() as ddg:
            for r in ddg.text(q, region="xa-ar", safesearch="moderate", max_results=max_results):
                t = (r.get("title") or "").strip()
                u = (r.get("href") or r.get("url") or "").strip()
                s = (r.get("body") or r.get("snippet") or "").strip()
                u = _clean_duckduckgo_url(u)
                if u:
                    out.append(_norm_item(t, u, s))
    except Exception:
        pass
    return out

def _ddg_html_fallback(q: str, max_results: int = 12) -> List[Dict]:
    """خطة بديلة تكشط نتائج DuckDuckGo مباشرة"""
    out = []
    try:
        url = "https://duckduckgo.com/html/?q=" + requests.utils.quote(q)
        r = requests.get(url, headers=UA, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.select("a.result__a")[:max_results]:
            title = a.get_text(" ", strip=True)
            href = a.get("href") or ""
            href = _clean_duckduckgo_url(href)
            snippet = ""
            body = a.find_parent("div", class_="result__body")
            if body:
                s2 = body.select_one(".result__snippet")
                if s2:
                    snippet = s2.get_text(" ", strip=True)
            if href:
                out.append(_norm_item(title, href, snippet))
    except Exception:
        pass
    return out

def _wiki_summary(q: str) -> Optional[Dict]:
    """جلب ملخص من ويكيبيديا العربية أو الإنجليزية"""
    try:
        for lang in ("ar", "en"):
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(q.replace(" ", "_"))
            r = requests.get(url, headers=UA, timeout=8)
            if r.status_code == 200:
                data = r.json()
                title = data.get("title") or q
                extract = data.get("extract") or ""
                page = data.get("content_urls", {}).get("desktop", {}).get("page") or data.get("source") or ""
                if page:
                    return _norm_item(title, page, extract)
    except Exception:
        pass
    return None

def deep_search(q: str, include_prices: bool = False) -> List[Dict]:
    """بحث عام + موسع"""
    queries = [
        q,
        f"{q} site:wikipedia.org",
        f"{q} site:mawdoo3.com",
        f"{q} site:youtube.com",
        f"{q} site:aljazeera.net",
        f"{q} site:bbc.com/ar",
        f"{q} site:cnn.com"
    ]

    if include_prices:
        queries += [f"{q} site:amazon.ae", f"{q} site:noon.com", f"{q} site:aliexpress.com"]

    results, seen = [], set()

    def push(items: List[Dict]):
        for it in items:
            u = it.get("url")
            if not u or u in seen:
                continue
            seen.add(u)
            if not it.get("snippet"):
                it["snippet"] = it.get("title") or ""
            results.append(it)

    for sub in queries:
        res = _ddg_api(sub, max_results=8)
        if not res:
            res = _ddg_html_fallback(sub, max_results=8)
        push(res)

    # في حال النتائج قليلة جدًا
    if len(results) < 5:
        w = _wiki_summary(q)
        if w:
            push([w])

    return results[:30]

def people_search(name: str) -> List[Dict]:
    """بحث عن أشخاص أو حسابات"""
    engines = [
        "facebook.com", "twitter.com", "instagram.com", "youtube.com",
        "linkedin.com", "t.me", "threads.net", "github.com", "snapchat.com", "tikTok.com"
    ]
    out, seen = [], set()
    for site in engines:
        q = f'{name} site:{site}'
        a = _ddg_api(q, max_results=6) or _ddg_html_fallback(q, max_results=6)
        for it in a:
            u = _clean_duckduckgo_url(it.get("url") or "")
            if u and u not in seen:
                seen.add(u)
                it["url"] = u
                out.append(it)
    return out[:30]
