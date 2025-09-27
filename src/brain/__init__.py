# -*- coding: utf-8 -*-
"""
العقل v9 — Bassam Brain
- عربي، محادثي
- رياضيات عبر sympy
- بحث عام عبر DuckDuckGo + جلب النصوص وتلخيصها
- ويكيبيديا (عربي أولاً؛ إنجليزي ثم ترجمة للعربية عند الحاجة)
- سوشيال/نقاشات: يجلب نتائج Reddit/YouTube/Stackexchange عبر DuckDuckGo ثم يقرأ صفحة المصدر (إن أمكن)
- ترجمة تلقائية للعربية عند الحاجة
- تصحيح وتوسيع بسيط لعبارات البحث
"""

from __future__ import annotations

import re
import math
from datetime import datetime
from typing import List, Tuple, Dict, Optional

# ========= رياضيات =========
from sympy import symbols, Eq, sympify, solve, diff, integrate, sin, cos, tan, exp, log  # noqa: F401

# ========= بحث وقراءة =========
from duckduckgo_search import DDGS
import httpx
from bs4 import BeautifulSoup
from readability import Document

# ========= تلخيص =========
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser

# ========= ترجمة =========
try:
    # غير رسمية لكنها تعمل مجانًا في أغلب الوقت
    from googletrans import Translator  # type: ignore
except Exception:
    Translator = None  # سنتعامل مع عدم وجودها

# ========= ويكيبيديا =========
import wikipedia

# ========= تحسين صياغة =========
from rapidfuzz import process, fuzz

# ========= كاش خفيف =========
from diskcache import Cache
cache = Cache('/tmp/bassam_cache')

# سجل بسيط للجلسة
memory_log: List[dict] = []

# إعداد ويكيبيديا
wikipedia.set_rate_limiting(True)
wikipedia.set_lang("ar")

# =========================================
# نقطة الدخول
# =========================================
def safe_run(query: str) -> str:
    """
    يأخذ سؤال المستخدم ويعيد إجابة عربية محادثية قدر الإمكان.
    """
    memory_log.append({"time": datetime.now(), "query": query})
    q = (query or "").strip()
    if not q:
        return "✍️ اكتب سؤالك أولاً."

    # هل رياضيات؟
    if looks_like_math(q):
        return _answer_math(q)

    # غير رياضيات → بحث وفهم
    # طبّق تحسين/تصحيح بسيط للصياغة
    q_norm = normalize_query(q)

    # جرّب كاش
    ck = f"brainv9::{q_norm}"
    cached = cache.get(ck)
    if cached:
        return cached

    # 1) ويكيبيديا أولاً (سريعة ومفيدة للأسئلة التعريفية)
    wiki_text = fetch_wikipedia(q_norm)
    parts: List[str] = []
    sources: List[Tuple[str, str]] = []

    if wiki_text:
        parts.append(wiki_text["text"])
        sources.append(("ويكيبيديا", wiki_text["url"]))

    # 2) بحث ويب عام (يشمل سوشيال عبر النتائج)
    web_summary, web_sources = web_search_and_summarize(q_norm, want_social=True, max_results=6)
    if web_summary:
        parts.append(web_summary)
        sources.extend(web_sources)

    # 3) دمج وتجميل + ترجمة للعربية إذا لزم
    if not parts:
        final = "🔎 لم أعثر على نتائج دقيقة، جرّب أن تصيغ سؤالك بجملة أوضح أو أضف كلمات مفتاحية."
        cache.set(ck, final, expire=60*10)
        return final

    merged = "\n\n".join(parts)
    merged_ar = ensure_arabic(merged)

    sources_txt = "\n".join([f"- {t}: {u}" for (t, u) in dedup_sources(sources)][:8])
    answer = (
        f"💬 **خلاصة مختصرة:**\n{merged_ar}\n\n"
        f"🔗 **مصادر (مختارة):**\n{sources_txt}"
    )

    cache.set(ck, answer, expire=60*30)
    return answer


# =========================================
# رياضيات
# =========================================
MATH_HINT = (
    "تلميح: اكتب بصيغة بايثون-سيمبولية مثل: x**2, sqrt(x), sin(x), pi. "
    "للاشتقاق: diff(x**3, x) — للتكامل: integrate(sin(x), x) — "
    "للمعادلات: مثل x**2 - 4 = 0."
)

def looks_like_math(q: str) -> bool:
    patterns = [
        r"[0-9\+\-\*/\^\(\)]", r"\bpi\b", r"sqrt\(", r"sin\(|cos\(|tan\(",
        r"diff\(", r"integrate\(", r"=\s*0", r"x\s*\*\*", r"اشتق|تفاضل|تكامل|معادلة|حل"
    ]
    return any(re.search(p, q) for p in patterns)

def _answer_math(q: str) -> str:
    x, y, z = symbols('x y z')
    try:
        if "=" in q:
            left, right = q.split("=", 1)
            expr = sympify(left) - sympify(right)
            sols = solve(Eq(expr, 0))
            return f"✅ حل المعادلة: {sols}\n\n{MATH_HINT}"

        if q.strip().startswith(("diff(", "integrate(")):
            res = sympify(q)
            return f"✅ ناتج رمزي: {res}\n\n{MATH_HINT}"

        res = sympify(q).evalf()
        return f"✅ الناتج: {res}\n\n{MATH_HINT}"
    except Exception as e:
        return f"⚠️ لم أفهم المعادلة ({e}).\n{MATH_HINT}"


# =========================================
# تحسين/تصحيح السؤال
# =========================================
_COMMON_FIXES = {
    "من هو": "من هو",
    "ما هو": "ما هو",
    "اورما": "أورما",
    "بن لادن": "أسامة بن لادن",
    "تعزيز القوه": "تعزيز القوة",
}

def normalize_query(q: str) -> str:
    q = " ".join(q.split())  # مسافات طبيعية
    # بدائيات تصحيح شائعة
    for k, v in _COMMON_FIXES.items():
        if k in q:
            q = q.replace(k, v)
    # إن كان قصيراً جدًا، وسّعه قليلاً
    if len(q) < 4:
        q = f"ما المقصود بـ {q}؟"
    return q


# =========================================
# ويكيبيديا
# =========================================
def fetch_wikipedia(q: str) -> Optional[Dict[str, str]]:
    try:
        # عربي أولاً
        wikipedia.set_lang("ar")
        titles = wikipedia.search(q)
        if titles:
            page = wikipedia.page(titles[0], auto_suggest=False, preload=False)
            summary = wikipedia.summary(page.title, sentences=3, auto_suggest=False)
            return {"text": f"📚 من ويكيبيديا: {summary}", "url": page.url}

        # إنجليزي ثم ترجمة
        wikipedia.set_lang("en")
        titles = wikipedia.search(q)
        if titles:
            page = wikipedia.page(titles[0], auto_suggest=False, preload=False)
            summary = wikipedia.summary(page.title, sentences=3, auto_suggest=False)
            return {"text": f"📚 من ويكيبيديا (مترجم): {translate_to_ar(summary)}", "url": page.url}
    except Exception:
        pass
    finally:
        wikipedia.set_lang("ar")
    return None


# =========================================
# بحث ويب + تلخيص + سوشيال
# =========================================
SOCIAL_SITES = ["reddit.com", "stackexchange.com", "stackoverflow.com", "medium.com", "quora.com", "youtube.com", "x.com", "twitter.com"]

def web_search_and_summarize(query: str, want_social: bool = True, max_results: int = 6) -> Tuple[str, List[Tuple[str, str]]]:
    texts: List[str] = []
    sources: List[Tuple[str, str]] = []

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception:
        results = []

    if not results:
        return "", []

    # فضّل النتائج الغنية بالمحتوى
    for r in results:
        url = r.get("href") or r.get("url")
        title = r.get("title", "مصدر")
        if not url:
            continue

        # إذا أردنا سوشيال: أعطِ أولوية لمواقع النقاش
        if want_social and any(s in url for s in SOCIAL_SITES):
            txt = fetch_page_text(url, social=True)
        else:
            txt = fetch_page_text(url)

        if txt and len(txt.split()) >= 60:
            texts.append(txt)
            sources.append((title, url))

    if not texts:
        return "", []

    summary = summarize_texts(texts, sentences=5)
    return summary, sources


def fetch_page_text(url: str, social: bool = False) -> str:
    """
    تحميل الصفحة واستخراج نص نظيف بقدر الإمكان.
    - social=True: نحاول إبقاء الوصف/المحتوى القصير للمشاركات.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (BassamBot)"}
        with httpx.Client(timeout=20.0, headers=headers, follow_redirects=True) as client:
            r = client.get(url)
            r.raise_for_status()

        # لو يوتيوب: خذ الوصف على الأقل
        if "youtube.com" in url or "youtu.be" in url:
            soup = BeautifulSoup(r.text, "lxml")
            desc = soup.find("meta", {"name": "description"})
            if desc and desc.get("content"):
                return f"وصف فيديو يوتيوب: {desc['content']}"
            # احتياطي
            og_desc = soup.find("meta", {"property": "og:description"})
            if og_desc and og_desc.get("content"):
                return f"وصف فيديو يوتيوب: {og_desc['content']}"

        # مواقع نقاش: خذ فقرة المحتوى الرئيسية إن أمكن
        if social and ("reddit.com" in url or "stack" in url or "quora.com" in url or "medium.com" in url):
            soup = BeautifulSoup(r.text, "lxml")
            # وصف/مقتطفات عامة
            og_desc = soup.find("meta", {"property": "og:description"})
            if og_desc and og_desc.get("content"):
                return og_desc["content"]
            desc = soup.find("meta", {"name": "description"})
            if desc and desc.get("content"):
                return desc["content"]

        # عام: استخرج متن الصفحة عبر readability
        doc = Document(r.text)
        html = doc.summary()
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        # ترجمة للعربية إذا لزم
        text = ensure_arabic(text)
        return text
    except Exception:
        return ""


def summarize_texts(texts: List[str], sentences: int = 5) -> str:
    # اجمع النصوص
    joined = "\n\n".join(texts)
    try:
        parser = PlaintextParser.from_string(joined, Tokenizer("arabic"))
        summarizer = LsaSummarizer()
        sents = summarizer(parser.document, sentences)
        summary = " ".join(str(s) for s in sents)
        if len(summary.strip()) < 20:
            raise ValueError("summary too short")
        return summary
    except Exception:
        # احتياطي: خذ أول 700 حرف
        return (joined[:700] + "…") if len(joined) > 700 else joined


# =========================================
# ترجمة/لغة
# =========================================
def ensure_arabic(text: str) -> str:
    """إن كان النص غير عربي بوضوح، حاول ترجمته للعربية."""
    if is_arabic(text):
        return text
    return translate_to_ar(text)

def is_arabic(s: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", s))

def translate_to_ar(text: str) -> str:
    if not text:
        return text
    try:
        if Translator is None:
            return text  # لا يوجد مترجم مثبت
        tr = Translator()
        out = tr.translate(text, dest="ar")
        return out.text
    except Exception:
        return text  # إن فشلت الترجمة، أعده كما هو


# =========================================
# أدوات صغيرة
# =========================================
def dedup_sources(s: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    seen = set()
    out = []
    for t, u in s:
        if u in seen:
            continue
        seen.add(u)
        out.append((sanitize_title(t), u))
    return out

def sanitize_title(t: str) -> str:
    t = re.sub(r"\s+", " ", t or "").strip()
    if len(t) > 80:
        t = t[:77] + "…"
    return t
