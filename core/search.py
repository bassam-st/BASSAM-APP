# core/search.py — البحث العميق في المواقع والناس (مجاني عبر DuckDuckGo)
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import re

# ============== البحث العام (عبر DuckDuckGo) ==============
def deep_search(query: str, include_prices: bool = False, max_results: int = 25):
    """
    بحث عميق في الإنترنت من DuckDuckGo بدون مفاتيح مدفوعة.
    """
    try:
        results = []
        q = query.strip()

        # مواقع مرجّحة حسب نوع البحث
        queries = [
            q,
            f"{q} site:wikipedia.org",
            f"{q} site:mawdoo3.com",
            f"{q} site:bbc.com",
            f"{q} site:aljazeera.net",
            f"{q} site:cnn.com",
            f"{q} site:stackoverflow.com",  # مفيد للبرمجة
            f"{q} site:youtube.com",
        ]

        # عند تفعيل الأسعار
        if include_prices:
            queries += [
                f"{q} site:noon.com",
                f"{q} site:amazon.ae",
                f"{q} site:amazon.sa",
                f"{q} site:alibaba.com",
                f"{q} site:souq.com",
            ]

        # تنفيذ البحث
        with DDGS() as ddg:
            for sub_q in queries:
                hits = ddg.text(sub_q, max_results=max_results)
                for h in hits:
                    url = h.get("href") or h.get("url")
                    title = h.get("title")
                    body = h.get("body")
                    if url and url not in [r["url"] for r in results]:
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": body,
                        })

        return results

    except Exception as e:
        print(f"[deep_search ERROR] {e}")
        return []


# ============== البحث عن أشخاص / يوزرات ==============
def people_search(name: str, max_results: int = 30):
    """
    بحث عن الأشخاص أو اليوزرات عبر DuckDuckGo
    """
    try:
        results = []
        q = name.strip()

        people_queries = [
            f"{q} site:facebook.com",
            f"{q} site:twitter.com",
            f"{q} site:instagram.com",
            f"{q} site:youtube.com",
            f"{q} site:tiktok.com",
            f"{q} site:linkedin.com",
            f"{q} site:wikipedia.org",
            f"{q} site:telegram.me",
            f"{q} site:threads.net",
            f"{q} site:github.com",
        ]

        with DDGS() as ddg:
            for sub_q in people_queries:
                hits = ddg.text(sub_q, max_results=max_results)
                for h in hits:
                    url = h.get("href") or h.get("url")
                    title = h.get("title")
                    body = h.get("body")
                    if url and url not in [r["url"] for r in results]:
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": body,
                        })

        return results

    except Exception as e:
        print(f"[people_search ERROR] {e}")
        return []
