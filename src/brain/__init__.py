# src/brain/__init__.py — نواة بسام الذكي (Smart v3: Wikipedia + Search)

import re
import math
import urllib.parse
from datetime import datetime
from typing import List

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

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# =========================
# نقطة دخول العقل
# =========================
def safe_run(query: str) -> str:
    q = (query or "").strip()
    memory_log.append({"t": datetime.utcnow().isoformat(), "q": q})

    if not q:
        return "اكتب سؤالك أولًا."

    # 1) رياضيات؟
    if looks_like_math(q):
        return solve_math(q)

    # 2) ويكيبيديا أولًا (عربي ثم إنجليزي)
    wiki = wiki_summary(q)
    if wiki:
        return wiki

    # 3) بحث + تلخيص
    return search_and_summarize(q)


# ========= رياضيات =========
MATH_HINT = (
    "تلميح: اكتب بصيغة بايثون-سيمبولية مثل: x**2, sqrt(x), sin(x), pi. "
    "للاشتقاق: diff(x**3, x) — للتكامل: integrate(sin(x), x) — "
    "للمعادلات: مثل x**2-4=0."
)

def looks_like_math(q: str) -> bool:
    patterns = [
        r"[0-9\+\-\*/\^\(\)]",
        r"\bpi\b", r"sqrt\(",
        r"sin\(|cos\(|tan\(",
        r"diff\(", r"integrate\(",
        r"=\s*0", r"x\s*\*\*",
        r"اشتق|تكامل|معادلة|حل|ناتج|قيمة"
    ]
    return any(re.search(p, q) for p in patterns)

def solve_math(q: str) -> str:
    x, y, z = symbols("x y z")
    try:
        if "=" in q:
            left, right = q.split("=", 1)
            expr = sympify(left) - sympify(right)
            sols = solve(Eq(expr, 0))
            return f"✅ حل المعادلة: {sols}\n\n{MATH_HINT}"

        res = sympify(q).evalf()
        return f"✅ الناتج: {res}\n\n{MATH_HINT}"
    except Exception as e:
        return f"⚠️ لم أفهم المعادلة ({e}).\n{MATH_HINT}"


# ========= ويكيبيديا =========
def wiki_summary(query: str) -> str | None:
    """
    يحاول جلب ملخص قصير من ويكيبيديا العربية ثم الإنجليزية.
    """
    topic = query.strip()
    # جرّب إزالة علامات الاستفهام والكلمات الشائعة
    topic = re.sub(r"[؟?!]", "", topic)
    topic = re.sub(r"^(ما|من|أين|متى|كم|لماذا|كيف)\s+", "", topic).strip()

    if not topic:
        return None

    for lang in ("ar", "en"):
        url = (
            f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
            f"{urllib.parse.quote(topic)}"
        )
        try:
            with httpx.Client(
                timeout=15.0, headers={"User-Agent": USER_AGENT}
            ) as client:
                r = client.get(url, follow_redirects=True)
                if r.status_code == 404:
                    continue
                r.raise_for_status()
                data = r.json()
                extract = data.get("extract")
                title = data.get("title")
                page_url = data.get("content_urls", {}).get("desktop", {}).get("page")
                if extract:
                    src = f"\n\n🔗 مصدر: {page_url or f'ويكيبيديا ({lang})'}"
                    return f"📌 {title}:\n{extract}{src}"
        except Exception:
            continue
    return None


# ========= بحث + تلخيص =========
def search_and_summarize(query: str) -> str:
    key = f"srch::{query}"
    cached = cache.get(key)
    if cached:
        return cached

    try:
        # 1) بحث DDG
        with DDGS() as ddgs:
            results = list(
                ddgs.text(
                    query,
                    region="xa-ar",     # تفضيل محتوى عربي إن وُجد
                    safesearch="Off",
                    max_results=6,
                )
            )

        if not results:
            return "🧐 لم أعثر على نتائج مباشرة. جرّب صياغة أقصر أو كلمة مفتاحية أدق."

        # 2) حمّل 2–3 مصادر قابلة للاستخراج
        texts, sources = [], []
        for r in results[:4]:
            url = r.get("href") or r.get("url")
            if not url:
                continue
            txt = fetch_clean_text(url)
            if txt and len(txt.split()) > 120:
                texts.append(txt)
                title = r.get("title") or "مصدر"
                sources.append((title, url))
            if len(texts) >= 3:
                break

        if not texts:
            return "🔍 وجدت نتائج، لكن لم أستطع استخراج نص واضح منها. جرّب سؤالًا أقصر."

        # 3) لخص
        summary = summarize_texts(texts, sentences=4)

        # 4) مصادر
        src_lines = "\n".join([f"- {t}: {u}" for t, u in sources])
        final = f"📌 خلاصة سريعة:\n{summary}\n\n🔗 مصادر:\n{src_lines}"
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
