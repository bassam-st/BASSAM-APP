# src/brain/__init__.py — نواة بسام الذكي (Smart v2 مع محادثة خفيفة)

import re
from datetime import datetime
from typing import List

# رياضيات
from sympy import symbols, Eq, sympify, solve  # noqa: F401

# بحث واستخلاص
from duckduckgo_search import DDGS
import httpx
from bs4 import BeautifulSoup
from readability import Document
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser

# اقتباس جُمل جواب
from rank_bm25 import BM25Okapi
from rapidfuzz import fuzz

# كاش وذاكرة جلسات
from diskcache import Cache
cache = Cache('/tmp/bassam_cache')
sessions = Cache('/tmp/bassam_sessions')

memory_log: List[dict] = []

# -----------------------------
# نقطة دخول عامة (سؤال واحد)
# -----------------------------
def safe_run(query: str) -> str:
    memory_log.append({"time": datetime.now(), "query": query})
    q = (query or "").strip()
    if not q:
        return "اكتب سؤالك أولاً."

    if looks_like_math(q):
        return solve_math(q)

    return search_and_summarize(q)


# -----------------------------
# محادثة خفيفة
# -----------------------------
def chat_run(session_id: str, message: str) -> str:
    hist = sessions.get(session_id, [])
    msg = rewrite_followup(message, hist[-1]["user"] if hist else "")
    ans = safe_run(msg)
    hist.append({"user": message, "expanded": msg, "bot": ans})
    sessions.set(session_id, hist[-8:], expire=60*60)  # آخر 8 تبادلات/ساعة
    return ans

def rewrite_followup(m, last_q):
    m = (m or "").strip()
    if not last_q:
        return m
    # متابعة قصيرة → نُرجعها لسؤال كامل
    if len(m) < 6 or re.match(r"^(ومتى|وأين|وكيف|لماذا|من|كم|هذا|هذه|هو|هي)\b", m):
        return f"{last_q} — متابعة: {m}"
    return m


# ========= رياضيات =========
MATH_HINT = (
    "تلميح: اكتب بصيغة بايثون-سيمبولية مثل: x**2, sqrt(x), sin(x), pi. "
    "للاشتقاق: diff(x**3, x)  — للتكامل: integrate(sin(x), x). "
    "للمعادلات: اكتب مثلاً x**2-4=0."
)

def looks_like_math(q: str) -> bool:
    patterns = [
        r"[0-9\+\-\*/\^\(\)]", r"\bpi\b", r"sqrt\(", r"sin\(|cos\(|tan\(",
        r"diff\(", r"integrate\(", r"=\s*0", r"x\s*\*\*", r"اشتق|تكامل|معادلة"
    ]
    return any(re.search(p, q) for p in patterns)

def solve_math(q: str) -> str:
    x, y, z = symbols('x y z')
    try:
        if "=" in q:
            left, right = q.split("=", 1)
            expr = sympify(left) - sympify(right)
            sols = solve(Eq(expr, 0))
            return f"✅ حل المعادلة: {sols}\n\n{MATH_HINT}"

        if q.strip().startswith(("diff(", "integrate(")):
            res = sympify(q)
            return f"✅ الناتج الرمزي: {res}\n\n{MATH_HINT}"

        res = sympify(q).evalf()
        return f"✅ الناتج: {res}\n\n{MATH_HINT}"
    except Exception as e:
        return f"⚠️ لم أفهم المعادلة ({e}).\n{MATH_HINT}"


# ========= بحث + تلخيص + اقتباس =========
def search_and_summarize(query: str) -> str:
    key = f"srch::{query}"
    cached = cache.get(key)
    if cached:
        return cached

    try:
        # 1) بحث DDG
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=6))

        # محاولة ويكيبيديا العربية لو النتائج ضعيفة
        if not results:
            with DDGS() as ddgs:
                results = list(ddgs.text(f"site:ar.wikipedia.org {query}", max_results=5))

        if not results:
            return "😕 لم أعثر على نتائج مناسبة."

        # 2) سحب النصوص من أول 3 روابط مناسبة
        texts, sources = [], []
        for r in results:
            url = r.get("href") or r.get("url")
            if not url:
                continue
            txt = fetch_clean_text(url)
            if txt and len(txt.split()) > 80:
                texts.append(txt)
                sources.append((r.get("title", "مصدر"), url))
            if len(texts) >= 3:
                break

        if not texts:
            return "😕 لم أستطع استخراج نصوص مفيدة من النتائج."

        # 3) اقتباس جمل “تشبه الجواب”
        qa = extract_answer_like(query, texts)

        # 4) تلخيص عام
        summary = summarize_texts(texts, sentences=4)

        # 5) صياغة نهائية + مصادر
        src_lines = "\n".join([f"- {t}: {u}" for t, u in sources])
        head = "🧠 إجابة مختصرة:\n" + qa if qa.strip() else "📌 خلاصة سريعة:"
        body = summary if qa.strip() else summary
        final = f"{head}\n\n{body}\n\n🔗 مصادر:\n{src_lines}"

        cache.set(key, final, expire=60*30)  # 30 دقيقة
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


def extract_answer_like(question: str, texts: List[str]) -> str:
    sents = []
    for t in texts:
        sents += re.split(r"(?<=[.!؟])\s+", t)
    sents = [s.strip() for s in sents if 20 <= len(s) <= 300]
    if not sents:
        return ""

    bm = BM25Okapi([s.split() for s in sents])
    top = bm.get_top_n(question.split(), sents, n=14)

    scored = sorted(
        ((s, fuzz.token_set_ratio(question, s)) for s in top),
        key=lambda x: x[1], reverse=True
    )[:7]

    best = [s for s, score in scored if score >= 40][:5]
    return ("\n• " + "\n• ".join(best)) if best else ""
