# core/search.py — محرك البحث الأساسي المجاني (بدون مفاتيح مدفوعة)

from typing import List, Dict, Optional
import re, requests
try:
    from duckduckgo_search import DDGS
except Exception:
    DDGS = None


def deep_search(query: str, include_prices: bool = False, max_results: int = 20) -> List[Dict]:
    results: List[Dict] = []

    # DuckDuckGo via ddgs
    if DDGS:
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, region="xa-ar", max_results=max_results):
                    results.append({"title": r.get("title"), "url": r.get("href"), "snippet": r.get("body")})
        except Exception as e:
            print(f"[DDGS ERROR] {e}")

    # Fallback: HTML endpoint
    if not results:
        try:
            url = f"https://duckduckgo.com/html/?q={query}"
            headers = {"User-Agent": "Mozilla/5.0"}
            html = requests.get(url, headers=headers, timeout=12).text
            for link, title in re.findall(r'<a rel="nofollow" class="result__a" href="(.*?)">(.*?)</a>', html):
                results.append({"title": re.sub(r"<.*?>", "", title), "url": link, "snippet": ""})
        except Exception as e:
            print(f"[Fallback Search ERROR] {e}")

    if include_prices:
        price_q = f"{query} site:alibaba.com OR site:noon.com OR site:amazon.com"
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(price_q, region="xa-ar", max_results=10):
                    results.append({"title": r.get("title"), "url": r.get("href"), "snippet": r.get("body")})
        except Exception as e:
            print(f"[PRICE SEARCH ERROR] {e}")

    return results


def people_search(name: str, max_results: int = 15) -> List[Dict]:
    results: List[Dict] = []
    keywords = [
        f"{name} site:twitter.com",
        f"{name} site:facebook.com",
        f"{name} site:linkedin.com",
        f"{name} site:instagram.com",
        f"{name} site:youtube.com",
    ]
    try:
        with DDGS() as ddgs:
            for q in keywords:
                for r in ddgs.text(q, region="xa-ar", max_results=max_results):
                    results.append({"title": r.get("title"), "url": r.get("href"), "snippet": r.get("body")})
    except Exception as e:
        print(f"[PEOPLE SEARCH ERROR] {e}")

    return results
