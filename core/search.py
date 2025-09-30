# core/search.py
# ------------------------------------------------------------
# بحث عميق + بحث أشخاص/يوزرات (مجاني وثابت على Render)
# يعتمد DuckDuckGo + (اختياري) requests/BeautifulSoup لجلب مقتطفات
# ------------------------------------------------------------
from typing import List, Dict, Optional
import time, re, urllib.parse

from duckduckgo_search import DDGS

# اختياري: إن لم تتوفر هذه الحزم سيعمل الكود بدون جلب مقتطفات إضافية
try:
    import requests
    from bs4 import BeautifulSoup
except Exception:
    requests = None
    BeautifulSoup = None

# دوال مساعدة من core/utils.py (موجود عندك)
from .utils import dedup_by_url

# ----------------- أدوات داخلية خفيفة -----------------

def _clean_text(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip()

def _tokens(s: str) -> List[str]:
    return re.findall(r"[A-Za-z\u0600-\u06FF0-9_]+", s.lower())

def _token_score(query: str, text: str) -> float:
    """
    قياس بسيط للتشابه (تقاطع الكلمات) — سريع وخفيف.
    """
    if not query or not text:
        return 0.0
    q = set(_tokens(query))
    t = set(_tokens(text))
    if not q or not t:
        return 0.0
    inter = len(q & t)
    return inter / (len(q) ** 0.7)

def _ddg_text(query: str, max_results: int = 6, region: str = "wt-wt", safesearch: str = "moderate") -> List[Dict]:
    """
    غلاف لنتائج DuckDuckGo (نرجع title/url/snippet)
    """
    out: List[Dict] = []
    try:
        with DDGS(timeout=8) as ddgs:
            for r in ddgs.text(query, region=region, safesearch=safesearch, max_results=max_results):
                url = r.get("href") or r.get("url") or ""
                if not url:
                    continue
                out.append({
                    "title": _clean_text(r.get("title") or ""),
                    "url": url,
                    "snippet": _clean_text(r.get("body") or r.get("snippet") or "")
                })
    except Exception:
        pass
    return out

def _domain(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return ""

def _fetch_snippet(url: str, timeout: int = 8) -> str:
    """
    محاولة جلب مقتطف قصير من الصفحة نفسها — اختياري
    لن يوقف التطبيق لو requests/bs4 غير متوفرين.
    """
    if not requests or not BeautifulSoup:
        return ""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (BassamBot; +https://example.com)"}
        r = requests.get(url, timeout=timeout, headers=headers)
        if r.status_code != 200 or not r.text:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        # meta description أولاً
        m = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if m and m.get("content"):
            return _clean_text(m.get("content"))
        # وإلا أول فقرة نصية
        p = soup.find("p")
        if p:
            return _clean_text(p.get_text(" "))
    except Exception:
        pass
    return ""

# ----------------- بحث عام عميق -----------------

_TRUSTED_BOOST = {
    # مصادر عامة موثوقة
    "wikipedia.org": 12,
    "britannica.com": 9,
    "stanford.edu": 9, "mit.edu": 9, "harvard.edu": 9, ".edu": 6,
    ".gov": 9,
    "nature.com": 8, "science.org": 8, "arxiv.org": 7,
    "bbc.com": 7, "reuters.com": 7, "apnews.com": 6, "nytimes.com": 6,
    "aljazeera.net": 7, "arabic.cnn.com": 6,
    # أسواق (لما نطلب أسعار)
    "amazon.com": 10, "amazon.sa": 10, "amazon.ae": 10,
    "alibaba.com": 10, "aliexpress.com": 9,
    "noon.com": 8, "jumia.com": 7, "souq.com": 7,
}

def _domain_boost(url: str, include_prices: bool) -> int:
    d = _domain(url)
    score = 0
    for key, val in _TRUSTED_BOOST.items():
        if key.startswith("."):
            if d.endswith(key):
                score = max(score, val)
        else:
            if key in d:
                score = max(score, val)
    # لو ما نبغى أسعار، لا نرفع أسواق
    if not include_prices and any(k in d for k in ["amazon", "alibaba", "aliexpress", "noon", "souq", "jumia"]):
        score = 0
    return score

def deep_search(query: str, include_prices: bool = False, max_results: int = 36) -> List[Dict]:
    """
    بحث عام قوي:
    - يصنع استعلامات متعددة (عام + موسوعات + أسئلة/كيف + أسواق إن طُلِب)
    - يجمع نتائج كثيرة ثم يرتبها: (تشابه الكلمات + أولوية الدومين) مع إزالة التكرارات
    - يحاول استكمال المقتطف عند الحاجة
    """
    q = _clean_text(query)
    if not q:
        return []

    queries: List[str] = [
        q,
        f"{q} معلومات",
        f"{q} شرح",
        f"{q} تعريف",
        f"{q} ماذا يعني",
        f"site:wikipedia.org {q}",
        f"site:britannica.com {q}",
        f"site:stackoverflow.com {q}";  # مفيد للبرمجة
    ]

    # أسئلة/كيف/أفضل
    if len(_tokens(q)) <= 6:
        queries += [f"ما هو {q}", f"كيف {q}", f"أفضل {q}"]

    # أسواق — فقط إذا طلب المستخدم
    if include_prices:
        markets = ["amazon.com", "amazon.sa", "amazon.ae", "alibaba.com", "aliexpress.com", "noon.com", "jumia.com", "souq.com"]
        for m in markets:
            queries.append(f"site:{m} {q}")

    results: List[Dict] = []
    for i, qq in enumerate(queries):
        # لكل استعلام نأخذ كمية صغيرة لتجنب الحظر
        batch = _ddg_text(qq, max_results=6)
        results.extend(batch)
        time.sleep(0.15)

    # إزالة التكرار
    results = dedup_by_url(results)

    # اكتمال المقتطفات (اختياري) — فقط لعدد قليل من الأعلى لاحقاً
    for r in results[:12]:
        if not r.get("snippet"):
            sn = _fetch_snippet(r["url"])
            if sn:
                r["snippet"] = sn

    # ترتيب ذكي
    def _score(item: Dict) -> float:
        title = item.get("title") or ""
        snip = item.get("snippet") or ""
        sim = 1.0 * _token_score(q, f"{title} {snip}")
        dom_bonus = 0.6 * _domain_boost(item.get("url") or "", include_prices)
        title_bonus = 0.4 if _token_score(q, title) > 0 else 0.0
        return sim + dom_bonus + title_bonus

    results = sorted(results, key=_score, reverse=True)
    return results[:max_results]

# ----------------- بحث أشخاص / يوزرات -----------------

_SOCIAL_ORDER = [
    "twitter.com", "x.com", "instagram.com", "tiktok.com", "facebook.com",
    "linkedin.com", "youtube.com", "github.com", "snapchat.com",
    "pinterest.com", "twitch.tv", "threads.net", "medium.com", "about.me"
]

def people_search(name: str, max_results: int = 40) -> List[Dict]:
    """
    بحث مركّز للأشخاص/اليوزرات:
    - يبني استعلامات لكل منصات السوشيال
    - لو كاتب @username يتعامل معها كيوزر مباشرة
    - يزيل التكرار ويرتب بحيث الأقرب للمطلوب أعلى
    """
    name = _clean_text(name)
    if not name:
        return []

    patterns: List[str] = []
    if name.startswith("@"):
        uname = name[1:]
        for d in _SOCIAL_ORDER:
            patterns.append(f"site:{d} {uname}")
            patterns.append(f"site:{d} \"{uname}\"")
    else:
        q_name = f"\"{name}\"" if " " in name and not name.startswith("\"") else name
        for d in _SOCIAL_ORDER:
            patterns.append(f"site:{d} {q_name}")
            patterns.append(f"site:{d} profile {q_name}")
            patterns.append(f"site:{d} @{name}")

    out: List[Dict] = []
    for p in patterns:
        out += _ddg_text(p, max_results=4)
        time.sleep(0.12)

    out = dedup_by_url(out)

    # ترجيح حسب المنصة + تطابق الاسم/اليوزر
    def _rank(item: Dict) -> float:
        url = (item.get("url") or "").lower()
        title = item.get("title") or ""
        snip = item.get("snippet") or ""

        # أولوية المنصّات
        base = len(_SOCIAL_ORDER) + 5
        for i, d in enumerate(_SOCIAL_ORDER):
            if d in url:
                base = i  # كلما أقل كان أفضل
                break

        # لو كان المستخدم كتب @يوزر وظهر حرفياً في المسار -> مكافأة كبيرة
        bonus = 0.0
        if name.startswith("@"):
            uname = name[1:].lower()
            if f"/{uname}" in url or uname in url:
                bonus += 6.0

        # تشابه الاسم في العنوان/المقتطف
        sim = 5.0 * _token_score(name, f"{title} {snip}")

        # نحول “أولوية المنصّات” إلى قيمة كبيرة (مقلوبة) ثم نضيف البونص والتشابه
        return -(base) + bonus + sim

    out = sorted(out, key=_rank, reverse=True)
    return out[:max_results]
