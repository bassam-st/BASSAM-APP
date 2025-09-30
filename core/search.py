# -*- coding: utf-8 -*-
# core/search.py — بحث ويب عميق مبسّط لـ "بسام الذكي"

from typing import List, Dict
from duckduckgo_search import DDGS
import httpx, re

from .utils import dedup_by_url, clean_html, normalize_text

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124 Safari/537.36"
)

def _fetch_url_snippet(url: str, timeout: float = 8.0) -> str:
    """يجلب مقتطفًا بسيطًا من الصفحة عند الحاجة (Fallback)."""
    try:
        with httpx.Client(headers={"User-Agent": UA}, timeout=timeout, follow_redirects=True) as c:
            r = c.get(url)
            if r.status_code != 200:
                return ""
            # خذ أول 1200 حرف بعد تنظيف HTML
            txt = clean_html(r.text)
            return txt[:1200]
    except Exception:
        return ""


def ddg_web(query: str, max_results: int = 8) -> List[Dict]:
    """بحث نصي من DuckDuckGo مع هيكلة قياسية للنتائج."""
    out: List[Dict] = []
    q = normalize_text(query)
    try:
        with DDGS() as ddgs:
            for hit in ddgs.text(q, max_results=max_results, safesearch="moderate", region="wt-wt"):
                title = hit.get("title") or ""
                url = hit.get("href") or hit.get("url") or ""
                snippet = hit.get("body") or ""
                if not url:
                    continue
                out.append({
                    "title": title.strip(),
                    "url": url.strip(),
                    "snippet": snippet.strip(),
                })
    except Exception:
        pass

    # لو المقتطفات فاضية، حاول نجيب مقطع صغير من الصفحة
    for h in out:
        if not h["snippet"]:
            h["snippet"] = _fetch_url_snippet(h["url"])
    return dedup_by_url(out)


def _price_domains() -> List[str]:
    return [
        "amazon.com", "aliexpress.com", "temu.com", "noon.com", "jumia.com",
        "souq.com", "ebay.com", "walmart.com", "bestbuy.com", "newegg.com",
        "alibaba.com", "rakuten.com", "cartlow.com", "namshi.com",
    ]


def deep_search(
    query: str,
    include_prices: bool = False,
    include_images: bool = False,
    max_results: int = 8,
) -> List[Dict]:
    """
    بحث عميق مبسّط:
    - يبدأ بنتائج نصية من DDG
    - لو include_prices=True يضيف نتائج من مواقع تسوّق
    - include_images لا يغيّر الشكل هنا (الصور تُدار من الواجهة لاحقًا)
    """
    results = ddg_web(query, max_results=max_results)

    # أسعار (نبحث على نطاقات متاجر)
    if include_prices:
        price_q = f'{query} price OR سعر OR buy'
        domains = _price_domains()
        # نستعلم عدّة مرات بتصفية النطاقات
        with DDGS() as ddgs:
            for dom in domains[:6]:  # يكفي 6 نطاقات لتقليل الوقت
                try:
                    for hit in ddgs.text(
                        f'site:{dom} {price_q}',
                        max_results=3,
                        safesearch="moderate",
                        region="wt-wt",
                    ):
                        url = (hit.get("href") or hit.get("url") or "").strip()
                        if not url:
                            continue
                        results.append({
                            "title": (hit.get("title") or "").strip(),
                            "url": url,
                            "snippet": (hit.get("body") or "").strip(),
                        })
                except Exception:
                    pass

    # تنظيف وتوحيد الشكل
    out: List[Dict] = []
    for h in results:
        if not h.get("url"):  # حماية
            continue
        out.append({
            "title": (h.get("title") or "").strip()[:200],
            "url": h["url"].strip(),
            "snippet": clean_html((h.get("snippet") or "").strip())[:600],
        })
    return dedup_by_url(out)
