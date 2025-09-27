# src/brain/registry.py
"""
سجل المصادر (connectors) لعقل بسام الذكي.
يسمح بجلب المعرفة من الويب، ويكيبيديا، ويوتيوب ورديت عند توفر المفاتيح.
"""

import httpx
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
from readability import Document

# ============== جلب النص من الإنترنت ==============
def fetch_text(url: str) -> str:
    """يحاول استخراج النص النظيف من أي صفحة"""
    try:
        with httpx.Client(timeout=15.0, headers={"User-Agent": "Mozilla/5.0"}) as c:
            r = c.get(url, follow_redirects=True)
            r.raise_for_status()
        doc = Document(r.text)
        html = doc.summary()
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "header", "footer", "nav"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return text
    except Exception:
        return ""


# ============== البحث عبر DuckDuckGo ==============
def connector_duckduckgo(query: str, max_results: int = 5):
    """بحث ويب عام"""
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            url = r.get("href") or r.get("url")
            if not url:
                continue
            title = r.get("title") or "مصدر"
            snippet = r.get("body") or ""
            results.append({"title": title, "url": url, "snippet": snippet})
    return results


# ============== بحث ويكيبيديا (عربي وإنجليزي) ==============
def connector_wikipedia(query: str):
    """يحاول جلب محتوى من ويكيبيديا"""
    urls = [
        f"https://ar.wikipedia.org/wiki/{query.replace(' ', '_')}",
        f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}"
    ]
    results = []
    for url in urls:
        text = fetch_text(url)
        if text and len(text.split()) > 80:
            results.append({"title": "ويكيبيديا", "url": url, "snippet": text[:300]})
    return results
