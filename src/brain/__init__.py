# src/brain/__init__.py — نواة بسام الذكي (Smart v2)

import re
from datetime import datetime
from typing import List, Tuple
from urllib.parse import quote

# رياضيات
from sympy import symbols, Eq, sympify, solve  # noqa: F401

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
cache = Cache("/tmp/bassam_cache")

memory_log: List[dict] = []

# -----------------------------
# نقطة الدخول
# -----------------------------
def safe_run(query: str) -> str:
    memory_log.append({"time": datetime.now(), "query": query})
    q = (query or "").strip()
    if not q:
        return "اكتب سؤالك أولًا."

    # إن بدا أنه سؤال رياضيات
    if looks_like_math(q):
        return solve_math(q)

    # وإلا: بحث + تلخيص مع احتياطي ويكيبيديا
    return search_and_summarize(q)


# ========= رياضيات =========
MATH_HINT = (
    "تلميح: اكتب بصيغة بايثون-سيمبولية مثل: x**2, sqrt(x), sin(x), pi. "
    "للاشتقاق: diff(x**3, x) — للتكامل: integrate(sin(x), x). "
    "للمعادلات: مثل x**2-4=0."
)

def looks_like_math(q: str) -> bool:
    patterns = [
        r"[0-9\+\-\*/\^\(\)]", r"\bpi\b", r"sqrt\(", r"sin\(|cos\(|tan\(",
        r"diff\(", r"integrate\(", r"=\s*0", r"x\s*\*\*", r"اشتق|تكامل|معادلة"
    ]
    return any(re.search(p, q) for p in patterns)

def solve_math(q: str) -> str:
    x, y, z = symbols("x y z")
    try:
        # إذا فيها مساواة -> حل معادلة
        if "=" in q:
            left, right = q.split("=", 1)
            expr = sympify(left) - sympify(right)
            sols = solve(Eq(expr, 0))
            return f"✅ حل المعادلة: {sols}\n\n{MATH_HINT}"

        # استدعاءات diff/integrate مباشرة
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
        # 1) بحث DDG باللغة العربية
        with DDGS() as ddgs:
            results = list(ddgs.text(
                query,
                max_results=8,
                region="xa-ar",
                safesearch="moderate",
                timelimit=None
            ))

        texts, sources = extract_texts_from_results(results)

        # 2) احتياطي: ويكيبيديا العربية
        if not texts:
            wk = wikipedia_fetch_ar(query)
            if wk:
                texts = [wk["extract"]]
                sources = [(wk["title"], wk["url"])]

        if not texts:
            return "😕 لم أستطع الوصول إلى مصادر مفيدة الآن. جرّب صياغة أقصر أو سؤالًا مختلفًا."

        # 3) لخّص
        summary = safe_summarize(texts, sentences=4)

        # 4) أضف المصادر
        src_lines = "\n".join([f"- {t}: {u}" for t, u in sources])
        final = f"📌 خلاصة سريعة:\n{summary}\n\n🔗 مصادر:\n{src_lines}"
        cache.set(key, final, expire=60*30)  # 30 دقيقة
        return final

    except Exception as e:
        return f"حدث خطأ أثناء البحث: {e}"


def extract_texts_from_results(results):
    texts, sources = [], []
    for r in (results or []):
        url = r.get("href") or r.get("url")
        if not url:
            continue
        txt = fetch_clean_text(url)
        if txt and len(txt.split()) >= 80:
            texts.append(txt)
            title = r.get("title") or "مصدر"
            sources.append((title, url))
        if len(texts) >= 3:
            break
    return texts, sources


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


def safe_summarize(texts: List[str], sentences: int = 4) -> str:
    """ملخّص مع آلية سقوط احتياطية."""
    try:
        joined = "\n\n".join(texts)
        parser = PlaintextParser.from_string(joined, Tokenizer("arabic"))
        summarizer = LsaSummarizer()
        sents = summarizer(parser.document, sentences)
        out = " ".join(str(s) for s in sents).strip()
        if out:
            return out
    except Exception:
        pass
    raw = " ".join(texts)
    return (raw[:800] + "…") if len(raw) > 800 else raw


def wikipedia_fetch_ar(query: str):
    """ملخص قصير من ويكيبيديا العربية عند الحاجة."""
    try:
        q = query.strip()
        url_search = (
            "https://ar.wikipedia.org/w/api.php"
            "?action=opensearch&limit=1&namespace=0&format=json&search=" + quote(q)
        )
        with httpx.Client(timeout=15.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            rs = client.get(url_search)
            rs.raise_for_status()
            data = rs.json()
        if not data or len(data) < 4 or not data[1]:
            return None

        title = data[1][0]
        page_url = data[3][0]

        url_extract = (
            "https://ar.wikipedia.org/w/api.php"
            "?action=query&prop=extracts&explaintext=1&exintro=1&format=json&titles=" + quote(title)
        )
        with httpx.Client(timeout=15.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            rexc = client.get(url_extract)
            rexc.raise_for_status()
            j = rexc.json()
        pages = j.get("query", {}).get("pages", {})
        if not pages:
            return None
        page = next(iter(pages.values()))
        extract = page.get("extract", "").strip()
        if not extract:
            return None
        return {"title": title, "url": page_url, "extract": extract}
    except Exception:
        return None
