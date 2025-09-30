# core/search.py
from typing import List, Dict, Optional
import time, re, requests
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}

def _norm_item(title: str, url: str, snippet: str = "") -> Dict:
    return {"title": (title or url or "").strip(), "url": url.strip(), "snippet": (snippet or "").strip()}

def _ddg_api(q: str, max_results: int = 12) -> List[Dict]:
    out = []
    try:
        with DDGS() as ddg:
            for r in ddg.text(q, region="xa-ar", safesearch="moderate", max_results=max_results):
                t = (r.get("title") or "").strip()
                u = (r.get("href") or r.get("url") or "").strip()
                s = (r.get("body") or r.get("snippet") or "").strip()
                if u:
                    out.append(_norm_item(t, u, s))
    except Exception:
        pass
    return out

def _ddg_html_fallback(q: str, max_results: int = 12) -> List[Dict]:
    """يكشط صفحة نتائج DuckDuckGo كخطة بديلة عند فشل الـ API."""
    out = []
    try:
        url = "https://duckduckgo.com/html/?q=" + requests.utils.quote(q)
        r = requests.get(url, headers=UA, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a.result__a")[:max_results]:
            title = a.get_text(" ", strip=True)
            href = a.get("href") or ""
            # المقتطف
            snip_el = a.find_parent("div", class_="result__body")
            snippet = ""
            if snip_el:
                s2 = snip_el.select_one(".result__snippet")
                if s2:
                    snippet = s2.get_text(" ", strip=True)
            if href:
                out.append(_norm_item(title, href, snippet))
    except Exception:
        pass
    return out

def _wiki_summary(q: str) -> Optional[Dict]:
    """محاولة جلب ملخص من ويكيبيديا العربية/الإنجليزية (بدون مكتبات إضافية)."""
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
    queries = [q]
    # نوسّع الاستعلام بمصادر مفيدة
    queries += [
        f"{q} site:wikipedia.org",
        f"{q} site:mawdoo3.com",
        f"{q} site:youtube.com",
        f"{q} site:aljazeera.net",
    ]
    if include_prices:
        queries += [f"{q} site:amazon.ae", f"{q} site:noon.com", f"{q} site:souq.com"]

    seen, results = set(), []

    def push(items: List[Dict]):
        for it in items:
            u = it.get("url")
            if not u or u in seen: 
                continue
            seen.add(u)
            # ضمن وجود snippet
            if not it.get("snippet"):
                it["snippet"] = it.get("title") or ""
            results.append(it)

    for sub in queries:
        a = _ddg_api(sub, max_results=8)
        if not a:  # خطة بديلة
            a = _ddg_html_fallback(sub, max_results=8)
        push(a)

    # لو ما زالت النتائج قليلة، جرّب ملخص ويكيبيديا على نص السؤال بدون قيود
    if len(results) < 5:
        w = _wiki_summary(q)
        if w:
            push([w])

    return results[:30]

def people_search(name: str) -> List[Dict]:
    engines = [
        "facebook.com", "twitter.com", "instagram.com", "youtube.com",
        "linkedin.com", "t.me", "threads.net", "github.com"
    ]
    out, seen = [], set()
    for site in engines:
        q = f'{name} site:{site}'
        a = _ddg_api(q, max_results=6) or _ddg_html_fallback(q, max_results=6)
        for it in a:
            u = it.get("url")
            if u and u not in seen:
                seen.add(u)
                out.append(it)
    return out[:30]
