# src/brain/__init__.py — نواة بسام الذكي (Smart V3)

import re
import math
from datetime import datetime
from typing import List
from sympy import symbols, Eq, sympify, solve, diff, integrate, sin, cos, tan, exp, log

from diskcache import Cache
from sumy.summarizers.lsa import LsaSummarizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from rapidfuzz import fuzz

from .registry import connector_duckduckgo, connector_wikipedia, fetch_text

cache = Cache("/tmp/bassam_cache")
memory_log: List[dict] = []

# ---------------------- نقطة تشغيل الذكاء ----------------------
def safe_run(query: str) -> str:
    memory_log.append({"time": datetime.now(), "query": query})
    q = (query or "").strip()

    if not q:
        return "✍️ اكتب سؤالك أولاً."

    # محاولة فهم نوع السؤال
    if looks_like_math(q):
        return solve_math(q)
    else:
        return smart_search(q)

# ========== دوال التحليل ==========
def looks_like_math(q: str) -> bool:
    patterns = [
        r"[0-9\+\-\*/\^\(\)]", r"\bpi\b", r"sqrt\(", r"sin\(|cos\(|tan\(",
        r"diff\(", r"integrate\(", r"=\s*0", r"x\s*\*\*"
    ]
    return any(re.search(p, q) for p in patterns)

# ========== الذكاء الرياضي ==========
def solve_math(q: str) -> str:
    x, y, z = symbols("x y z")
    try:
        if "=" in q:
            left, right = q.split("=", 1)
            expr = sympify(left) - sympify(right)
            sols = solve(Eq(expr, 0))
            return f"✅ الحل: {sols}"
        if q.strip().startswith(("diff(", "integrate(")):
            res = sympify(q)
            return f"✅ الناتج الرمزي: {res}"
        res = sympify(q).evalf()
        return f"✅ الناتج: {res}"
    except Exception as e:
        return f"⚠️ لم أفهم المعادلة ({e})."

# ========== الذكاء البحثي والتلخيص ==========
def smart_search(query: str) -> str:
    key = f"smart::{query}"
    cached = cache.get(key)
    if cached:
        return cached

    results = []

    # 1. ويكيبيديا
    results.extend(connector_wikipedia(query))

    # 2. DuckDuckGo
    results.extend(connector_duckduckgo(query))

    # تنظيف النتائج
    cleaned = []
    seen = set()
    for r in results:
        text = (r.get("snippet") or "").strip()
        if not text:
            continue
        if any(fuzz.ratio(text, c.get("snippet", "")) > 80 for c in cleaned):
            continue
        cleaned.append(r)
        seen.add(text)

    if not cleaned:
        return "🔍 لم أجد نتائج دقيقة، حاول بصيغة مختلفة."

    # دمج وتلخيص
    texts = [r["snippet"] for r in cleaned]
    summary = summarize_texts(texts)
    src_lines = "\n".join([f"- {r['title']} ({r['url']})" for r in cleaned[:5]])

    answer = f"🤖 بسام وجد لك هذه الخلاصة:\n{summary}\n\n🔗 المصادر:\n{src_lines}"
    cache.set(key, answer, expire=3600)
    return answer

# ========== التلخيص ==========
def summarize_texts(texts: List[str], sentences: int = 4) -> str:
    joined = "\n\n".join(texts)
    parser = PlaintextParser.from_string(joined, Tokenizer("arabic"))
    summarizer = LsaSummarizer()
    sents = summarizer(parser.document, sentences)
    return " ".join(str(s) for s in sents)
