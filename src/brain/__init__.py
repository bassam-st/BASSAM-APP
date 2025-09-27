# src/brain/__init__.py — نواة بسام الذكي Smart v2

import re
import math
from datetime import datetime
from typing import List
from sympy import symbols, Eq, sympify, solve, diff, integrate, sin, cos, tan, exp, log
from duckduckgo_search import DDGS
import httpx
from bs4 import BeautifulSoup
from readability import Document
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from diskcache import Cache

# كاش للسرعة
cache = Cache('/tmp/bassam_cache')
memory_log: List[dict] = []

def safe_run(query: str) -> str:
    """المعالجة الذكية — رياضيات أو بحث أو تلخيص"""
    memory_log.append({"time": datetime.now(), "query": query})
    q = (query or "").strip()
    if not q:
        return "📝 اكتب سؤالك أولًا."

    if looks_like_math(q):
        return solve_math(q)
    return search_and_summarize(q)

# ========= رياضيات =========
def looks_like_math(q: str) -> bool:
    patterns = [
        r"[0-9\+\-\*/\^\(\)]", r"\bpi\b", r"sqrt\(", r"sin\(|cos\(|tan\(",
        r"diff\(", r"integrate\(", r"=\s*0", r"x\s*\*\*", r"اشتق|تكامل|حل|معادلة"
    ]
    return any(re.search(p, q) for p in patterns)

def solve_math(q: str) -> str:
    x, y, z = symbols('x y z')
    try:
        if "=" in q:
            left, right = q.split("=", 1)
            expr = sympify(left) - sympify(right)
            sols = solve(Eq(expr, 0))
            return f"✅ حل المعادلة: {sols}"

        if q.strip().startswith(("diff(", "integrate(")):
            res = sympify(q)
            return f"✅ الناتج الرمزي: {res}"

        res = sympify(q).evalf()
        return f"✅ الناتج العددي: {res}"
    except Exception as e:
        return f"⚠️ لم أفهم المسألة ({e})"

# ========= بحث + تلخيص =========
def search_and_summarize(query: str) -> str:
    key = f"srch::{query}"
    cached = cache.get(key)
    if cached:
        return cached

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "🔍 لم أجد نتائج دقيقة، حاول بصياغة مختلفة."

        texts, sources = [], []
        for r in results[:3]:
            url = r.get("href") or r.get("url")
            if not url:
                continue
            txt = fetch_text(url)
            if txt and len(txt.split()) > 80:
                texts.append(txt)
                sources.append((r.get("title", "مصدر"), url))

        if not texts:
            return "😕 لم أستطع استخراج نصوص مفيدة من النتائج."

        summary = summarize_texts(texts, sentences=4)
        src_lines = "\n".join([f"- {t}: {u}" for t, u in sources])
        final = f"📘 ملخص سريع:\n{summary}\n\n🔗 المصادر:\n{src_lines}"
        cache.set(key, final, expire=1800)
        return final
    except Exception as e:
        return f"⚠️ حدث خطأ أثناء البحث: {e}"

def fetch_text(url: str) -> str:
    try:
        with httpx.Client(timeout=15.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            r = client.get(url, follow_redirects=True)
            r.raise_for_status()
        doc = Document(r.text)
        html = doc.summary()
        soup = BeautifulSoup(html, "lxml")
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
