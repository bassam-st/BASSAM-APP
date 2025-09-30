# core/search.py  — بحث مجاني مع عمق اختياري
from typing import List, Dict, Optional, Tuple
import os, re, time, hashlib, json
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # /src
CACHE_DIR = os.path.join(ROOT_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", "ignore")).hexdigest()

def _cache_path(url: str) -> str:
    return os.path.join(CACHE_DIR, f"{_hash(url)}.json")

def _domain(u: str) -> str:
    try:
        return urlparse(u).netloc or ""
    except Exception:
        return ""

def _looks_like_article(url: str) -> bool:
    if any(url.lower().endswith(ext) for ext in (".jpg", ".png", ".gif", ".webp", ".svg", ".css", ".js")):
        return False
    if url.startswith("mailto:") or url.startswith("javascript:"):
        return False
    return True

def _clean_text(html: str) -> Tuple[str, List[str], str]:
    """يرجع (نص_نظيف, روابط_داخلية, عنوان)."""
    soup = BeautifulSoup(html or "", "lxml")
    for bad in soup(["script", "style", "noscript", "iframe"]):
        bad.extract()
    title = (soup.title.string.strip() if soup.title and soup.title.string else "")[:200]
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if _looks_like_article(href):
            links.append(href)
    return text, links, title

def _get(url: str, timeout: float) -> Optional[str]:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout, allow_redirects=True)
        if r.status_code == 200 and r.text:
            return r.text
    except Exception:
        return None
    return None

def _fetch_page(url: str, deadline: float) -> Dict:
    """يجلب الصفحة مع كاش بسيط (صلاحية 3 أيام)."""
    url = url.strip()
    cp = _cache_path(url)
    # read cache
    try:
        if os.path.exists(cp) and (time.time() - os.path.getmtime(cp) < 3 * 24 * 3600):
            with open(cp, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass

    left = max(0.5, deadline - time.time())
    html = _get(url, timeout=left)
    if not html:
        return {}

    text, links, title = _clean_text(html)
    out = {
        "url": url,
        "title": title or url,
        "snippet": text[:800],
        "links": links[:200],
    }
    try:
        with open(cp, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)
    except Exception:
        pass
    return out

# ============ محركات مجانية ============

def _ddg_html(q: str, max_results: int = 12) -> List[Dict]:
    """DuckDuckGo HTML (مجاني)."""
    url = "https://duckduckgo.com/html/"
    params = {"q": q, "kl": "xa-ar", "ia": "web"}
    try:
        r = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=8)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        items = []
        for a in soup.select("a.result__a"):
            href = a.get("href", "")
            if not href or not href.startswith("http"):
                continue
            title = a.get_text(" ", strip=True)
            items.append({"title": title, "url": href})
            if len(items) >= max_results:
                break
        return items
    except Exception:
        return []

def _bing_html(q: str, max_results: int = 12) -> List[Dict]:
    """Bing HTML (مجاني)."""
    try:
        url = "https://www.bing.com/search"
        r = requests.get(url, params={"q": q}, headers={"User-Agent": USER_AGENT}, timeout=8)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        items = []
        for h2 in soup.select("li.b_algo h2"):
            a = h2.find("a")
            if not a: 
                continue
            href = a.get("href", "")
            if not href or not href.startswith("http"):
                continue
            title = a.get_text(" ", strip=True)
            items.append({"title": title, "url": href})
            if len(items) >= max_results:
                break
        return items
    except Exception:
        return []

def _seed_results(q: str, include_prices: bool, limit: int = 12) -> List[Dict]:
    q2 = q
    if include_prices:
        # إشارات للمتاجر (تزيد احتمال روابط أسعار)
        q2 = f"{q} site:amazon.com OR site:aliexpress.com OR site:ebay.com OR site:noon.com OR site:alibaba.com"
    seeds = _ddg_html(q2, max_results=limit)
    if len(seeds) < 5:  # احتياط
        seeds += _bing_html(q2, max_results=limit - len(seeds))
    # إزالة التكرار
    seen, out = set(), []
    for it in seeds:
        u = it.get("url")
        if u and u not in seen:
            seen.add(u)
            out.append(it)
    return out[:limit]

# ============ البحث العميق ============

def deep_search(
    q: str,
    include_prices: bool = False,
    depth: int = 1,
    max_pages: int = 10,
    per_site_internal: int = 2,
    time_budget_sec: float = 9.0,
) -> List[Dict]:
    """
    depth=1: يقرأ الصفحات الأساسية فقط.
    depth=2: من كل صفحة يزور حتى رابطين داخليين مهمّين من نفس النطاق.
    """
    q = (q or "").strip()
    if not q:
        return []

    deadline = time.time() + time_budget_sec
    seeds = _seed_results(q, include_prices, limit=max_pages)
    results: List[Dict] = []
    visited = set()

    # كلمات الاستعلام لمطابقة الروابط الداخلية
    q_words = [w for w in re.findall(r"\w+", q.lower()) if len(w) > 2]

    def push(item: Dict):
        u = item.get("url")
        if u and u not in visited:
            visited.add(u)
            results.append({"title": item.get("title") or u, "url": u, "snippet": item.get("snippet", "")})

    # المرحلة 1: الصفحات الأساسية
    for it in seeds:
        if time.time() > deadline or len(results) >= max_pages:
            break
        url = it["url"]
        page = _fetch_page(url, deadline)
        if not page:
            continue
        push(page)

        # المرحلة 2: عمق داخلي (اختياري)
        if depth >= 2:
            base = url
            base_dom = _domain(base)
            picked = 0
            for href in page.get("links", []):
                if picked >= per_site_internal:
                    break
                try:
                    abs_url = urljoin(base, href)
                except Exception:
                    continue
                if _domain(abs_url) != base_dom:
                    continue
                if not _looks_like_article(abs_url):
                    continue
                # فلترة بسيطة بالاستعلام
                if q_words and not any(w in abs_url.lower() for w in q_words):
                    continue
                if time.time() > deadline or len(results) >= max_pages:
                    break
                sub = _fetch_page(abs_url, deadline)
                if not sub:
                    continue
                push(sub)
                picked += 1

    return results[:max_pages]

# ============ بحث الأشخاص/اليوزرات ============

_SOCIAL_SITES = [
    "site:twitter.com", "site:x.com", "site:instagram.com", "site:facebook.com",
    "site:t.me", "site:linkedin.com", "site:youtube.com", "site:snapchat.com",
    "site:github.com", "site:tikTok.com", "site:threads.net"
]

def people_search(name: str, limit: int = 20) -> List[Dict]:
    if not name:
        return []
    q = f'{name} {" OR ".join(_SOCIAL_SITES)}'
    seeds = _ddg_html(q, max_results=limit)
    if len(seeds) < 5:
        seeds += _bing_html(q, max_results=limit - len(seeds))
    # إزالة التكرار
    seen, out = set(), []
    for it in seeds:
        u = it.get("url")
        if u and u not in seen:
            seen.add(u)
            out.append({"title": it.get("title") or u, "url": u})
    return out[:limit]
