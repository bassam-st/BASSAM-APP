# core/search.py — محرك البحث الأساسي المجاني (بدون مفاتيح مدفوعة)

from typing import List, Dict, Optional
import time, re, requests

try:
    from duckduckgo_search import DDGS
except Exception:
    DDGS = None


# ====== البحث عبر DuckDuckGo ======
def deep_search(query: str, include_prices: bool = False, max_results: int = 20) -> List[Dict]:
    """بحث مجاني باستخدام DuckDuckGo"""
    results = []

    # نتحقق من وجود مكتبة DDGS
    if DDGS:
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, region="xa-ar", max_results=max_results):
                    results.append({
                        "title": r.get("title"),
                        "url": r.get("href"),
                        "snippet": r.get("body")
                    })
        except Exception as e:
            print(f"[DDGS ERROR] {e}")

    # احتياطي: استخدام API مجاني بسيط من HTMLDuckDuckGo إذا لم تعمل المكتبة
    if not results:
        try:
            url = f"https://duckduckgo.com/html/?q={query}"
            headers = {"User-Agent": "Mozilla/5.0"}
            html = requests.get(url, headers=headers, timeout=10).text
            for match in re.findall(r'<a rel="nofollow" class="result__a" href="(.*?)">(.*?)</a>', html):
                link, title = match
                results.append({
                    "title": re.sub(r"<.*?>", "", title),
                    "url": link,
                    "snippet": ""
                })
        except Exception as e:
            print(f"[Fallback Search ERROR] {e}")

    # خيار البحث عن الأسعار
    if include_prices:
        price_query = f"{query} site:alibaba.com OR site:noon.com OR site:amazon.com"
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(price_query, region="xa-ar", max_results=10):
                    results.append({
                        "title": r.get("title"),
                        "url": r.get("href"),
                        "snippet": r.get("body")
                    })
        except Exception as e:
            print(f"[PRICE SEARCH ERROR] {e}")

    return results


# ====== البحث عن الأشخاص أو اليوزرات ======
def people_search(name: str, max_results: int = 15) -> List[Dict]:
    """بحث بسيط عن أشخاص أو حسابات"""
    results = []
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
                    results.append({
                        "title": r.get("title"),
                        "url": r.get("href"),
                        "snippet": r.get("body")
                    })
    except Exception as e:
        print(f"[PEOPLE SEARCH ERROR] {e}")

    return results
