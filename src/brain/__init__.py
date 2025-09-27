# src/brain/__init__.py — Smart v4 (Arabic normalize + fuzzy Wikipedia + math fixes)

import re
import math
import urllib.parse
from datetime import datetime
from typing import List, Optional

# Math
from sympy import symbols, Eq, sympify, solve  # noqa: F401

# Search & summarize
from duckduckgo_search import DDGS
import httpx
from bs4 import BeautifulSoup
from readability import Document
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser

# Fuzzy match
from rapidfuzz import fuzz

# Cache
from diskcache import Cache
cache = Cache("/tmp/bassam_cache")

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

memory_log: List[dict] = []

# ---------------------------
# Normalization utilities
# ---------------------------
AR_NUMS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
MATH_CHARS = {
    "×": "*", "÷": "/", "−": "-", "–": "-", "—": "-",
    "٫": ".", "،": ",", "’": "'", "“": '"', "”": '"'
}
MATH_WORDS = [
    (r"\bالجذر\b", "sqrt"),
    (r"\bجذر\b", "sqrt"),
    (r"\bأس\b", "**"),
    (r"\bتكامل\b", "integrate"),
    (r"\bاشتقاق\b|\bاشتق\b", "diff"),
    (r"\bجيب\b", "sin"),
    (r"\bجيب التمام\b", "cos"),
    (r"\bظل\b", "tan"),
]

STOPWORDS = set("""
ما من منْ منَ ماذا اين أين متى لماذا كيف كم هل على عن في الى إلى بأن أن إن كان تكون هو هي هم هن هذا هذه تلك ذلك هناك هنا
""".split())

def strip_diacritics(s: str) -> str:
    return re.sub(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]", "", s)

def normalize_ar(s: str) -> str:
    s = s or ""
    s = strip_diacritics(s)
    s = s.replace("ـ", "")  # تطويل
    s = s.translate(AR_NUMS)
    for k, v in MATH_CHARS.items():
        s = s.replace(k, v)
    # حروف ألف موحدة
    s = re.sub("[إأآا]", "ا", s)
    s = re.sub("ى", "ي", s)
    s = re.sub("ؤ", "و", s)
    s = re.sub("ئ", "ي", s)
    s = re.sub("ة", "ه", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def arabic_math_hints(s: str) -> str:
    t = s
    for pat, rep in MATH_WORDS:
        t = re.sub(pat, rep, t)
    # كلمات ربط شائعة
    t = re.sub(r"\bيساوي\b", "=", t)
    return t

def keywords(s: str) -> str:
    toks = [w for w in re.split(r"\W+", s) if w]
    toks = [w for w in toks if w not in STOPWORDS]
    return " ".join(toks[:8])  # مختصر

# ---------------------------
# Entry point
# ---------------------------
def safe_run(query: str) -> str:
    raw_q = (query or "").strip()
    if not raw_q:
        return "اكتب سؤالك أولًا."

    q = normalize_ar(raw_q)
    memory_log.append({"t": datetime.utcnow().isoformat(), "q": q})

    # Math?
    if looks_like_math(q):
        return solve_math(arabic_math_hints(q))

    # Wikipedia (fuzzy)
    wiki = wiki_smart(q)
    if wiki:
        return wiki

    # Search + summarize
    return search_and_summarize(q)

# ---------------------------
# Math
# ---------------------------
MATH_HINT = (
    "تلميح: اكتب بصيغة بايثون مثل: x**2, sqrt(x), sin(x), pi. "
    "للاشتقاق: diff(expr, x) — للتكامل: integrate(expr, x) — "
    "للمعادلات: x**2-4=0."
)

def looks_like_math(q: str) -> bool:
    patterns = [
        r"[0-9\+\-\*/\^\(\)=]", r"\bpi\b", r"sqrt\(",
        r"sin\(|cos\(|tan\(", r"diff\(", r"integrate\(",
        r"اشتق|تكامل|معادله|حل|ناتج|قيمة"
    ]
    return any(re.search(p, q) for p in patterns)

def solve_math(q: str) -> str:
    x, y, z = symbols("x y z")
    try:
        if "=" in q:
            left, right = q.split("=", 1)
            expr = sympify(left) - sympify(right)
            sols = solve(Eq(expr, 0))
            return f"✅ حل المعادله: {sols}\n\n{MATH_HINT}"

        res = sympify(q).evalf()
        return f"✅ الناتج: {res}\n\n{MATH_HINT}"
    except Exception as e:
        return f"⚠️ لم أفهم المعادله ({e}).\n{MATH_HINT}"

# ---------------------------
# Wikipedia (fuzzy search -> summary)
# ---------------------------
def wiki_smart(query: str) -> Optional[str]:
    # كوّن استعلام مركز
    core = keywords(query) or query
    for lang in ("ar", "en"):
        title = wiki_best_title(core, lang=lang)
        if not title and lang == "ar":  # جرّب الاستعلام الأصلي دون تبسيط
            title = wiki_best_title(query, lang=lang)
        if title:
            summ = wiki_summary_by_title(title, lang=lang)
            if summ:
                return summ
    return None

def wiki_best_title(q: str, lang="ar") -> Optional[str]:
    api = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": q,
        "srlimit": 10,
        "format": "json"
    }
    try:
        with httpx.Client(timeout=12.0, headers={"User-Agent": USER_AGENT}) as client:
            r = client.get(api, params=params)
            r.raise_for_status()
            items = r.json().get("query", {}).get("search", [])
            if not items:
                return None
            # اختَر العنوان الأقرب نصيًا
            best = max(
                items,
                key=lambda it: fuzz.partial_ratio(q.lower(), it.get("title", "").lower())
            )
            score = fuzz.partial_ratio(q.lower(), best.get("title", "").lower())
            return best["title"] if score >= 55 else None
    except Exception:
        return None

def wiki_summary_by_title(title: str, lang="ar") -> Optional[str]:
    url = (
        f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
        f"{urllib.parse.quote(title)}"
    )
    try:
        with httpx.Client(timeout=12.0, headers={"User-Agent": USER_AGENT}) as client:
            r = client.get(url, follow_redirects=True)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            data = r.json()
            extract = data.get("extract")
            page_url = data.get("content_urls", {}).get("desktop", {}).get("page")
            title = data.get("title")
            if extract:
                src = f"\n\n🔗 مصدر: {page_url or f'ويكيبيديا ({lang})'}"
                return f"📌 {title}:\n{extract}{src}"
    except Exception:
        return None
    return None

# ---------------------------
# Web search + summarize
# ---------------------------
def search_and_summarize(query: str) -> str:
    key = f"srch::{query}"
    cached = cache.get(key)
    if cached:
        return cached

    try:
        with DDGS() as ddgs:
            results = list(
                ddgs.text(
                    query,
                    region="xa-ar",
                    safesearch="Off",
                    max_results=8,
                )
            )
        if not results:
            return "🔎 لم أعثر على نتائج واضحة. جرّب صياغة أقصر أو كلمة مفتاحيه أدق."

        texts, sources = [], []
        for r in results[:5]:
            url = r.get("href") or r.get("url")
            if not url:
                continue
            txt = fetch_clean_text(url)
            if txt and len(txt.split()) > 120:
                texts.append(txt)
                sources.append((r.get("title") or "مصدر", url))
            if len(texts) >= 3:
                break

        if not texts:
            return "وجدت نتائج، لكن لم أستطع استخراج نص واضح منها. جرّب سؤالًا أدق."

        summary = summarize_texts(texts, sentences=4)
        src_lines = "\n".join([f"- {t}: {u}" for t, u in sources])
        final = f"📌 خلاصة سريعه:\n{summary}\n\n🔗 مصادر:\n{src_lines}"
        cache.set(key, final, expire=60 * 30)
        return final
    except Exception as e:
        return f"⚠️ حدث خطأ أثناء البحث: {e}"

def fetch_clean_text(url: str) -> str:
    try:
        with httpx.Client(timeout=15.0, headers={"User-Agent": USER_AGENT}) as client:
            r = client.get(url, follow_redirects=True)
            r.raise_for_status()
        doc = Document(r.text)
        html = doc.summary()
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return text
    except Exception:
        return ""

def summarize_texts(texts: List[str], sentences: int = 4) -> str:
    joined = "\n\n".join(texts)
    parser = PlaintextParser.from_string(joined, Tokenizer("arabic"))
    summarizer = LsaSummarizer()
    sents = summarizer(parser.document, sentences)
    return " ".join(str(s) for s in sents)
