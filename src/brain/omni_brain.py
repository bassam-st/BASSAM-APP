# src/brain/omni_brain.py
# النسخة الخفيفة (v3.1 Lite): بدون FAISS / Sentence Transformers — تعمل في Render المجاني

import os, re, math, json, time
from datetime import datetime
from dateutil import parser as dateparser
from typing import List, Dict, Optional

import httpx
from bs4 import BeautifulSoup
from readability import Document
from duckduckgo_search import DDGS
from diskcache import Cache
from wikipedia import summary as wiki_summary
from sympy import sympify, diff, integrate

# ✅ Sumy الصحيح
from sumy.parsers.text import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

# ✅ مسترجع خفيف من مجلد docs (BM25 فقط) — يُستورد عند التشغيل
from src.rag.retriever import query_index as rag_file_query

# ===== إعدادات عامة =====
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
cache = Cache(".cache")

# ✅ RAG Switch (تشغيل/إيقاف عبر المتغير البيئي)
RAG_ENABLED = os.getenv("BASSAM_RAG", "off").lower() in {"1", "true", "on", "yes"}

# ✅ Gemini (اختياري)
USE_GEMINI = bool(os.getenv("GEMINI_API_KEY"))
if USE_GEMINI:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    GEMINI = genai.GenerativeModel("gemini-1.5-flash")
else:
    GEMINI = None

# ===== مساعدات نصية =====
AR = lambda s: re.sub(r"\s+", " ", (s or "").strip())

# ===== تلخيص محلي =====
def summarize_text(text: str, max_sentences: int = 5) -> str:
    try:
        parser = PlainTextParser.from_string(text, Tokenizer("arabic"))
        summ = TextRankSummarizer()
        sents = summ(parser.document, max_sentences)
        return " ".join(str(s) for s in sents)
    except Exception:
        return text[:700]

# ===== بحث الويب =====
def ddg_text(q: str, n: int = 5) -> List[Dict]:
    with DDGS() as ddgs:
        return list(ddgs.text(q, region="xa-ar", safesearch="moderate", max_results=n) or [])

def fetch_clean(url: str, timeout: int = 12) -> str:
    try:
        r = httpx.get(url, headers=UA, timeout=timeout, follow_redirects=True)
        r.raise_for_status()
        doc = Document(r.text)
        html_clean = doc.summary()
        text = BeautifulSoup(html_clean, "lxml").get_text("\n", strip=True)
        return text[:8000]
    except Exception:
        return ""

# ===== أدوات محلية =====
MATH_PAT = re.compile(r"[=+\-*/^()]|sin|cos|tan|log|sqrt|∫|dx|dy|مشتقة|تكامل", re.I)
CURRENCY = {"USD": 1.0, "EUR": 0.92, "SAR": 3.75, "AED": 3.67, "YER": 250.0}

def answer_math(q: str) -> Optional[str]:
    if not MATH_PAT.search(q):
        return None
    try:
        expr = sympify(q.replace("^", "**"))
        return f"🔹 الناتج التقريبي: {expr.evalf()}"
    except Exception:
        if "مشتقة" in q:
            try:
                term = q.split("مشتقة", 1)[1].strip()
                return f"مشتقة {term} = {diff(sympify(term))}"
            except:
                return "⚠️ لم أفهم التعبير الرياضي للمشتقة."
        if "تكامل" in q:
            try:
                term = q.split("تكامل", 1)[1].strip()
                return f"تكامل {term} = {integrate(sympify(term))}"
            except:
                return "⚠️ لم أفهم التعبير للتكامل."
        return None

def answer_units_dates(q: str) -> Optional[str]:
    m = re.search(r"(\d+[\.,]?\d*)\s*(USD|EUR|SAR|AED|YER)\s*(?:->|الى|إلى|to)\s*(USD|EUR|SAR|AED|YER)", q, re.I)
    if m:
        amount = float(m.group(1).replace(",", "."))
        src, dst = m.group(2).upper(), m.group(3).upper()
        out = (amount / CURRENCY[src]) * CURRENCY[dst]
        return f"💱 تقريبًا: {amount} {src} ≈ {round(out,2)} {dst}"
    return None

# ===== Wikipedia =====
def answer_wikipedia(q: str) -> Optional[str]:
    try:
        return wiki_summary(q, sentences=3, auto_suggest=False, redirect=True)
    except Exception:
        return None

# ===== Beauty Coach =====
BEAUTY_PAT = re.compile(r"(بشرة|تفتيح|بياض|غسول|شعر|حب شباب|ترطيب|قشرة|رشاقة|رجيم)", re.I)
def beauty_coach(q: str) -> Optional[str]:
    if not BEAUTY_PAT.search(q):
        return None
    tips = [
        "🧼 اغسلي وجهك بغسول لطيف مرتين يوميًا.",
        "🧴 استخدمي مرطب مناسب لنوع بشرتك.",
        "🛡️ لا تنسي واقي الشمس صباحًا.",
        "💧 اشربي ماء كافٍ وحافظي على النوم المنتظم.",
    ]
    return "✨ نصيحة بسّام الجمالية:\n" + "\n".join(f"• {t}" for t in tips)

# ===== التحيات والمشاعر =====
def answer_empathy(q: str) -> Optional[str]:
    if any(w in q for w in ["مرحبا", "هلا", "السلام عليكم", "صباح الخير", "مساء الخير"]):
        return "👋 أهلاً وسهلاً! أنا بسّام الذكي، جاهز أساعدك اليوم ✨"
    if any(w in q for w in ["شكرا", "ثنكيو", "thank", "ممتاز"]):
        return "🙏 يسعدني أساعدك دائمًا!"
    return None

# ===== RAG الخفيف =====
def answer_rag(q: str, k: int = 4):
    if not RAG_ENABLED:
        return None
    try:
        hits = rag_file_query(q, top_k=k)
        if not hits or (len(hits) == 1 and "لم يتم إنشاء الفهرس" in hits[0][0]):
            return None
        ctx = "\n\n".join(snippet for _, snippet in hits if snippet)
        srcs = [fname for fname, _ in hits if fname]
        summ = summarize_text(ctx, max_sentences=6)
        return f"{AR(summ)}\n\n📚 المصادر (من ملفاتك):\n" + "\n".join(f"- {s}" for s in srcs)
    except Exception:
        return None

# ===== Gemini =====
def answer_gemini(q: str) -> Optional[str]:
    if not GEMINI:
        return None
    try:
        res = GEMINI.generate_content("أجب بالعربية باختصار ودقة:\n" + q)
        return (res.text or "").strip()
    except Exception:
        return None

# ===== بحث الويب =====
def answer_from_web(q: str) -> str:
    hits = ddg_text(q)
    texts, urls = [], []
    for h in hits:
        u = h.get("href") or h.get("url")
        if not u:
            continue
        t = fetch_clean(u)
        if t:
            texts.append(t)
            urls.append(u)
    if not texts:
        return "⚠️ لم أجد مصادر كافية، حاول إعادة الصياغة."
    summary = summarize_text("\n\n".join(texts), 6)
    return f"{AR(summary)}\n\n🌐 المصادر:\n" + "\n".join(f"- {u}" for u in urls[:5])

# ===== الموجه الرئيسي =====
def omni_answer(q: str) -> str:
    q = AR(q)
    if not q:
        return "✏️ اكتب سؤالك أولًا."

    # مشاعر
    a = answer_empathy(q)
    if a: return a

    # أدوات محلية
    for tool in (answer_math, answer_units_dates, beauty_coach, answer_wikipedia):
        a = tool(q)
        if a: return a

    # RAG
    a = answer_rag(q)
    if a: return a

    # Gemini
    a = answer_gemini(q)
    if a: return a

    # ويب
    return answer_from_web(q)
