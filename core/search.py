# core/search.py — بحث مجاني عبر DuckDuckGo + جلب نص مبسط للصفحات
from typing import List, Dict, Optional
import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

_HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

def _fetch_snippet(url: str, timeout: float = 8.0) -> str:
    """يجلب نصًا قصيرًا من الصفحة (للتلخيص)، بدون تعمق."""
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout, headers=_HEADERS) as c:
            r = c.get(url)
        if r.status_code != 200 or "text/html" not in r.headers.get("content-type",""):
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        # نلتقط وصف/عناوين وفق بساطة
        og = soup.select_one('meta[name="description"], meta[property="og:description"]')
        if og and og.get("content"):
            return og["content"].strip()
        # وإلا نلتقط فقرات أولى
        p = soup.find("p")
        return (p.get_text(" ", strip=True) if p else "")[:500]
    except Exception:
        return ""

def _ddg(q: str, max_results: int = 12) -> List[Dict]:
    out: List[Dict] = []
    with DDGS() as ddgs:
        for hit in ddgs.text(q, region="xa-ar", max_results=max_results):
            url = hit.get("href") or hit.get("url")
            title = hit.get("title") or url
            if not url:
                continue
            out.append({"title": title, "url": url})
    return out

def deep_search(q: str, include_prices: bool = False) -> List[Dict]:
    """بحث عام — DuckDuckGo فقط (مجاني)."""
    q2 = q.strip()
    if include_prices:
        q2 += " أسعار site:amazon.com OR site:aliexpress.com OR site:noon.com"
    hits = _ddg(q2, max_results=15)
    # أضف مقتطف لكل نتيجة ليساعد على التلخيص في backend
    for h in hits:
        h["snippet"] = _fetch_snippet(h["url"])
    return hits

def people_search(name: str) -> List[Dict]:
    """بحث أشخاص/يوزرات — نعطي محركات مقترحة."""
    query = f'{name} site:twitter.com OR site:facebook.com OR site:instagram.com OR site:tiktok.com OR site:linkedin.com'
    hits = _ddg(query, max_results=20)
    return hits
