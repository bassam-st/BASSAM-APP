# core/search.py
# بحث عميق مجاني: DuckDuckGo + Google/Bing (scrape خفيف) + Wikipedia
from typing import List, Dict, Optional
import time, random, re
import requests
from bs4 import BeautifulSoup
from .utils import dedup_by_url

# ====== إعدادات HTTP خفيفة ======
_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15",
]
def _headers():
    return {"User-Agent": random.choice(_UAS), "Accept-Language": "ar,en;q=0.8"}

def _norm(url: str) -> str:
    if not url: return ""
    return url.split("&ved=")[0].split("&ei=")[0]

def _clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

# ====== DuckDuckGo (المصدر الأساسي) ======
def _ddg_text(q: str, max_results: int = 10) -> List[Dict]:
    try:
        from duckduckgo_search import DDGS
        out: List[Dict] = []
        with DDGS() as ddgs:
            for r in ddgs.text(q, region="xa-ar", max_results=max_results):
                out.append({
                    "title": r.get("title") or r.get("href") or "",
                    "url": r.get("href") or "",
                    "snippet": r.get("body") or "",
                    "engine": "ddg",
                })
        return out
    except Exception:
        return []

# ====== Google (HTML خفيف – قد يفشل أحيانًا؛ لا يكسر التطبيق) ======
def _google_text(q: str, max_results: int = 8) -> List[Dict]:
    try:
        url = "https://www.google.com/search"
        params = {"q": q, "num": str(max_results), "hl": "ar", "safe": "active"}
        r = requests.get(url, params=params, headers=_headers(), timeout=10)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        out: List[Dict] = []
        for a in soup.select("a[href]"):
            # الروابط داخل النتائج غالبًا داخل H3
            h3 = a.find("h3")
            if not h3: 
                continue
            href = a["href"]
            if not href.startswith("http"):
                continue
            out.append({
                "title": _clean_text(h3.get_text()),
                "url": _norm(href),
                "snippet": "",
                "engine": "google",
            })
            if len(out) >= max_results:
                break
        return out
    except Exception:
        return []

# ====== Bing (HTML خفيف) ======
def _bing_text(q: str, max_results: int = 8) -> List[Dict]:
    try:
        url = "https://www.bing.com/search"
        params = {"q": q, "count": str(max_results), "setlang": "ar"}
        r = requests.get(url, params=params, headers=_headers(), timeout=10)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        out: List[Dict] = []
        for h2 in soup.select("li.b_algo h2"):
            a = h2.find("a", href=True)
            if not a: 
                continue
            out.append({
                "title": _clean_text(a.get_text()),
                "url": _norm(a["href"]),
                "snippet": "",
                "engine": "bing",
            })
            if len(out) >= max_results:
                break
        return out
    except Exception:
        return []

# ====== Wikipedia (API رسمي مجاني) ======
def _wiki_hits(q: str, max_results: int = 5, lang: str = "ar") -> List[Dict]:
    try:
        api = f"https://{lang}.wikipedia.org/w/api.php"
        params = {"action":"query","list":"search","format":"json","srsearch":q,"srlimit":str(max_results)}
        r = requests.get(api, params=params, headers=_headers(), timeout=10)
        js = r.json()
        hits = js.get("query", {}).get("search", [])
        out: List[Dict] = []
        for h in hits:
            title = h.get("title","")
            url = f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"
            out.append({"title": title, "url": url, "snippet": _clean_text(h.get("snippet","")), "engine": "wikipedia"})
        return out
    except Exception:
        return []

# ====== تجميع النتائج مع إزالة التكرار ======
def deep_search(q: str, include_prices: bool = False, limit_per_engine: int = 8) -> List[Dict]:
    """
    بحث متعدد المحركات (مجاني). دائمًا يعتمد DDG، ويحاول Google/Bing/ويكيبيديا
    بدون كسر التطبيق إذا فشل أحدها.  include_prices يضيف استعلامات تسوّق بسيطة.
    """
    q = _clean_text(q)
    results: List[Dict] = []

    # DDG دائمًا أولًا (أكثر ثباتًا)
    results += _ddg_text(q, max_results=limit_per_engine)

    # محركات أخرى (لا نعوّل عليها – فقط تعزيز)
    results += _google_text(q, max_results=limit_per_engine // 2)
    results += _bing_text(q, max_results=limit_per_engine // 2)
    results += _wiki_hits(q, max_results=5)

    # بحث أسعار اختياري (بسيط – عبر DDG)
    if include_prices:
        for shop_q in [
            f"site:alibaba.com {q}",
            f"site:aliexpress.com {q}",
            f"site:amazon.com {q}",
            f"site:noon.com {q}",
            f"site:souq.com {q}",
        ]:
            results += _ddg_text(shop_q, max_results=4)

    # إزالة التكرار
    results = dedup_by_url(results)
    return results[:30]

# ====== بحث أشخاص / يوزرات (روابط بروفايل) ======
def people_search(name: str, max_results: int = 25) -> List[Dict]:
    name = _clean_text(name)
    # نستخدم DDG مع فلترة نطاقات السوشيال + بعض المواقع العامة
    patterns = [
        f'site:twitter.com "{name}"',
        f'site:x.com "{name}"',
        f'site:instagram.com "{name}"',
        f'site:tiktok.com "{name}"',
        f'site:facebook.com "{name}"',
        f'site:linkedin.com "{name}"',
        f'site:youtube.com "{name}"',
        f'site:github.com "{name}"',
        f'site:about.me "{name}"',
    ]
    out: List[Dict] = []
    for p in patterns:
        out += _ddg_text(p, max_results=5)
        time.sleep(0.2)  # لطّف الطلبات قليلاً

    out = dedup_by_url(out)
    return out[:max_results]
