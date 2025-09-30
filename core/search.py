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
