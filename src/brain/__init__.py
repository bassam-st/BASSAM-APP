# src/brain/__init__.py — نواة بسام الذكي (Smart v2)

import re
import math
from datetime import datetime
from typing import List, Tuple

# رياضيات
from sympy import symbols, Eq, sympify, solve, diff, integrate, sin, cos, tan, exp, log  # noqa: F401

# بحث وتلخيص
from duckduckgo_search import DDGS
import httpx
from bs4 import BeautifulSoup
from readability import Document
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser

# كاش خفيف
from diskcache import Cache
cache = Cache('/tmp/bassam_cache')

memory_log: List[dict] = []

# -----------------------------
# نقطة دخول العقل
# -----------------------------
def safe_run(query: str) -> str:
    memory_log.append({"time": datetime.now(), "query": query})

    q = (query or "").strip()
    if not q:
        return "اكتب سؤالك أولاً."

    # 1) إن كان رياضيات -> حاول الحل
    if looks_like_math(q):
        return solve_math(q)

    # 2) وإلا: بحث + تلخيص
    return search_and_summarize(q)


# ========= رياضيات =========
MATH_HINT = (
    "تلميح: اكتب بصيغة بايثون-سيمبولية مثل: x**2, sqrt(x), sin(x), pi. "
    "للاشتقاق اكتب: diff(x**3, x)  — وللتكامل: integrate(sin(x), x). "
    "للمعادلات: حل x**2-4=0."
)

def looks_like_math(q: str) -> bool:
    patterns = [
        r"[0-9\+\-\*/\^\(\)]", r"\bpi\b", r"sqrt\(", r"sin\(|cos\(|tan\(",
        r"diff\(", r"integrate\(", r"=\s*0", r"x\s*\*\*",
        r"اشتق|تكامل|معادلة"
    ]
    return any(re.search(p, q) for p in patterns)

def solve_math(q: str) -> str:
    x, y, z = symbols('x y z')
    try:
        # إذا فيها مساواة: حاول حل معادلة
        if "=" in q:
            left, right = q.split("=", 1)
            expr = sympify(left) - sympify(right)
            sols = solve(Eq(expr, 0))
            return f"✅ حل المعادلة: {sols}\n\n{MATH_HINT}"

        # اشتقاق/تكامل أو تقييم عددي
        if q.strip().startswith(("diff(", "integrate(")):
            res = sympify(q)
            return f"✅ الناتج الرمزي: {res}\n\n{MATH_HINT}"

        # تقييم عددي
        res = sympify(q).evalf()
        return f"✅ الناتج: {res}\n\n{MATH_HINT}"
    except Exception as e:
        return f"⚠️ لم أفهم المعادلة ({e}).\n{MATH_HINT}"


# ========= بحث + تلخيص =========
def search_and_summarize(query: str) -> str:
    key = f"srch::{query}"
    cached = cache.get(key)
    if cached:
        return cached

    try:
        # 1) ابحث في DuckDuckGo
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "😕 لم أعثر على نتائج مناسبة."

        # 2) حمّل 2–3 مصادر وأخرج متن الصفحة
        texts, sources = [], []
        for r in results[:3]:
            url = r.get("href") or r.get("url")
            if not url:
                continue
            txt = fetch_clean_text(url)
            if txt and len(txt.split()) > 80:
                texts.append(txt)
                sources.append((r.get("title", "مصدر"), url))

        if not texts:
            return "😕 لم أستطع استخراج نصوص مفيدة من النتائج."

        # 3) لخّص النصوص معاً
        summary = summarize_texts(texts, sentences=4)

        # 4) أضف المصادر
        src_lines = "\n".join([f"- {t}: {u}" for t, u in sources])
        final = f"📌 خلاصة سريعة:\n{summary}\n\n🔗 مصادر:\n{src_lines}"
        cache.set(key, final, expire=60*30)  # نص ساعة
        return final

    except Exception as e:
        return f"حدث خطأ أثناء البحث: {e}"


def fetch_clean_text(url: str) -> str:
    try:
        with httpx.Client(timeout=15.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            r = client.get(url, follow_redirects=True)
            r.raise_for_status()
        doc = Document(r.text)
        html = doc.summary()
        soup = BeautifulSoup(html, "lxml")
        # نظّف
        for tag in soup(["script", "style", "header", "footer", "nav"]):
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
