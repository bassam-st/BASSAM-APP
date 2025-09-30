# core/search.py — بحث مجاني مع كاش ومقتطفات عميقة خفيفة
from typing import List, Dict, Optional
import os, re, time, json, hashlib
import requests
from urllib.parse import urlparse, quote
from bs4 import BeautifulSoup

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# مسارات للكاش
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # /src
CACHE_DIR = os.path.join(ROOT_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", "ignore")).hexdigest()

def _cache_get(key: str) -> Optional[dict]:
    p = os.path.join(CACHE_DIR, f"{_hash(key)}.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _cache_set(key: str, obj: dict) -> None:
    try:
        p = os.path.join(CACHE_DIR, f"{_hash(key)}.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
    except Exception:
        pass

def _norm_item(title: str, url: str, snippet: str = "") -> Dict:
    return {
        "title": (title or url or "").strip(),
        "url": (url or "").strip(),
        "snippet": (snippet or "").strip()
    }

def _fetch(url: str, timeout: int = 12) -> Optional[str]:
    """يجلب HTML مع كاش بسيط."""
    if not url:
        return None
    ck = f"GET::{url}"
    hit = _cache_get(ck)
    if hit and isinstance(hit, dict) and "text" in hit and (time.time() - hit.get("ts", 0) < 3600*12):
        return hit["text"]
    try:
        r = requests.get(url, headers=UA, timeout=timeout)
        if r.status_code == 200 and r.text:
            _cache_set(ck, {"ts": time.time(), "text": r.text})
            return r.text
    except Exception:
        pass
    return None

# ============ محرك البحث (DuckDuckGo HTML) ============
def _ddg_html(q: str, max_results: int = 12) -> List[Dict]:
    out = []
    try:
        url = "https://duckduckgo.com/html/?q=" + quote(q)
        html = _fetch(url)
        if not html:
            return out
        soup = BeautifulSoup(html, "html.parser")
        # CSS قد يتغيّر أحيانًا — لكنه ثابت غالبًا
        for res in soup.select("div.result")[:max_results]:
            a = res.select_one("a.result__a")
            if not a:
                continue
            title = a.get_text(" ", strip=True)
            href = a.get("href") or ""
            snippet = ""
            sn = res.select_one(".result__snippet")
            if sn:
                snippet = sn.get_text(" ", strip=True)
            if href:
                out.append(_norm_item(title, href, snippet))
    except Exception:
        pass
    return out

# ============ تحسين المقتطف من الصفحة نفسها ============
_BAD_EXT = (".jpg",".jpeg",".png",".gif",".webp",".svg",".css",".js",".ico",".pdf",".zip",".mp4",".mov",".avi",".webm")

def _looks_like_article(url: str) -> bool:
    u = (url or "").lower()
    if any(u.endswith(ext) for ext in _BAD_EXT):
        return False
    if u.startswith("mailto:") or u.startswith("javascript:"):
        return False
    dn = urlparse(u).netloc
    return bool(dn)

def _best_snippet_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # meta description أولا
    md = soup.find("meta", attrs={"name":"description"}) or soup.find("meta", attrs={"property":"og:description"})
    if md and md.get("content"):
        desc = md.get("content").strip()
        if len(desc) > 60:
            return desc

    # أول 2-3 فقرات مفيدة
    ps = []
    for p in soup.find_all("p"):
        t = p.get_text(" ", strip=True)
        if len(t) >= 60:
            ps.append(t)
        if len(ps) >= 3:
            break
    if ps:
        return " ".join(ps)

    # fallback: عنوان الصفحة
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    return title

def _enrich(items: List[Dict], max_pages: int = 6) -> List[Dict]:
    """يحسّن snippet بجلب الصفحة لأول N روابط سريعة فقط."""
    enriched = []
    for it in items:
        if len(enriched) >= max_pages:
            enriched.append(it)
            continue
        url = it.get("url") or ""
        if not _looks_like_article(url):
            enriched.append(it)
            continue
        html = _fetch(url, timeout=10)
        if not html:
            enriched.append(it)
            continue
        try:
            better = _best_snippet_from_html(html)
            if better and (len(better) > len(it.get("snippet",""))):
                it = dict(it)
                it["snippet"] = better[:800]
        except Exception:
            pass
        enriched.append(it)
    return enriched

# ============ ويكيبيديا مختصر ============
def _wiki_summary(q: str) -> Optional[Dict]:
    try:
        for lang in ("ar","en"):
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/" + quote(q.replace(" ","_"))
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

# ============ البحث العام ============
def deep_search(q: str, include_prices: bool = False) -> List[Dict]:
    """يرجع قائمة روابط + مقتطفات محسّنة. مجانية بالكامل."""
    queries = [q]
    # توسيع الاستعلام بمواقع موثوقة (يمكن تعديلها)
    queries += [
        f"{q} site:wikipedia.org",
        f"{q} site:mawdoo3.com",
        f"{q} site:aljazeera.net",
        f"{q} site:youtube.com",
    ]
    if include_prices:
        queries += [
            f"{q} site:amazon.ae",
            f"{q} site:noon.com",
            f"{q} site:aliexpress.com",
            f"{q} site:ebay.com",
        ]

    seen, results = set(), []
    def push(items: List[Dict]):
        for it in items:
            u = it.get("url")
            if not u or u in seen:
                continue
            seen.add(u)
            if not it.get("snippet"):
                it["snippet"] = it.get("title") or ""
            results.append(it)

    for sub in queries:
        hits = _ddg_html(sub, max_results=10)
        push(hits)

    # تحسين المقتطف لأول نتائج (يشبه "عمق خفيف")
    results = _enrich(results, max_pages=8)

    # في حال النتائج قليلة جدًا — أضف ويكيبيديا مباشرةً
    if len(results) < 5:
        w = _wiki_summary(q)
        if w:
            results.insert(0, w)

    return results[:30]

# ============ البحث عن أشخاص / يوزرات ============
_SOCIAL_SITES = [
    "twitter.com", "x.com", "instagram.com", "facebook.com",
    "t.me", "youtube.com", "linkedin.com", "threads.net", "github.com"
]

def people_search(name: str) -> List[Dict]:
    q_norm = re.sub(r"\s+", " ", name.strip().lower())
    q_tokens = set(re.findall(r"[a-zA-Z0-9_\u0600-\u06FF]+", q_norm))

    def score(item: Dict) -> float:
        title = (item.get("title") or "").lower()
        url   = (item.get("url") or "").lower()
        text  = f"{title} {url}"
        tokens = set(re.findall(r"[a-zA-Z0-9_\u0600-\u06FF]+", text))
        overlap = len(q_tokens & tokens)
        bonus = 0
        if q_norm and q_norm in title: bonus += 2
        if q_norm and q_norm in url:   bonus += 1
        # أوزان خفيفة لمنصات أهم
        site_bonus = 0
        if any(s in url for s in ("twitter.com","x.com","instagram.com")): site_bonus += 1
        if any(s in url for s in ("linkedin.com","github.com")):           site_bonus += 1
        return overlap + bonus + 0.5*site_bonus

    out, seen = [], set()
    # نبحث مباشرة داخل الدومينات المعروفة
    for site in _SOCIAL_SITES:
        subq = f"{name} site:{site}"
        hits = _ddg_html(subq, max_results=8)
        for it in hits:
            u = it.get("url")
            if u and u not in seen:
                seen.add(u)
                if not it.get("snippet"):
                    it["snippet"] = it.get("title") or ""
                out.append(it)

    # إضافة بحث عام واحد (بدون site) ثم ترشيح الروابط التي تبدو كحسابات
    general = _ddg_html(name, max_results=10)
    for it in general:
        u = (it.get("url") or "").lower()
        if any(s in u for s in _SOCIAL_SITES) and u not in seen:
            seen.add(u)
            out.append(it)

    out.sort(key=score, reverse=True)
    return out[:30]
