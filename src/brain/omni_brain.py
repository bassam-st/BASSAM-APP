# src/brain/omni_brain.py
# النسخة المتقدمة: أدوات محلية + RAG + Gemini + ويب + ذاكرة مستخدم

import os, re, math, json, time
from datetime import datetime
from dateutil import parser as dateparser
from typing import List, Dict, Optional

import numpy as np
import httpx
from bs4 import BeautifulSoup
from readability import Document
from duckduckgo_search import DDGS
from diskcache import Cache
from wikipedia import summary as wiki_summary

from sympy import sympify, diff, integrate

# ✅ Sumy الصحيح
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

# ✅ ذاكرة المستخدم
from src.memory.memory import remember, recall

# ✅ RAG
import faiss
from sentence_transformers import SentenceTransformer
from src.rag.indexer import is_ready as rag_cache_ready
from src.rag.retriever import query_index as rag_file_query

# ===== إعدادات عامة =====
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
cache = Cache(".cache")

# Gemini (اختياري)
USE_GEMINI = bool(os.getenv("GEMINI_API_KEY"))
if USE_GEMINI:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    GEMINI = genai.GenerativeModel("gemini-1.5-flash")
else:
    GEMINI = None

# ===== RAG Embeddings =====
try:
    RAG_MODEL_NAME = os.getenv("RAG_EMB_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    RAG_EMB = SentenceTransformer(RAG_MODEL_NAME)
except Exception:
    RAG_EMB = None

# ===== تلخيص محلي =====
def summarize_text(text: str, max_sentences: int = 5) -> str:
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("arabic"))
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

# ===== أدوات محلية (رياضيات + عملات + تواريخ) =====
MATH_PAT = re.compile(r"[=+\-*/^()]|sin|cos|tan|log|sqrt|∫|dx|dy|d/dx|مشتقة|تكامل", re.I)
CURRENCY = {"USD":1.0, "EUR":0.92, "SAR":3.75, "AED":3.67, "YER":250.0}

def answer_math(q: str) -> Optional[str]:
    if not MATH_PAT.search(q):
        return None
    try:
        s = q.replace("^", "**")
        expr = sympify(s)
        return f"الناتج التقريبي: {expr.evalf()}"
    except Exception:
        if q.strip().startswith("مشتقة "):
            t = q.split("مشتقة ",1)[1]
            try:
                return f"مشتقة {t} = {diff(sympify(t))}"
            except:
                return "لم أفهم التعبير للمشتقة."
        if q.strip().startswith("تكامل "):
            t = q.split("تكامل ",1)[1]
            try:
                return f"تكامل {t} = {integrate(sympify(t))}"
            except:
                return "لم أفهم التعبير للتكامل."
        return None

def answer_units_dates(q: str) -> Optional[str]:
    m = re.search(r"(\d+[\.,]?\d*)\s*(USD|EUR|SAR|AED|YER)\s*(?:->|الى|إلى|to)\s*(USD|EUR|SAR|AED|YER)", q, re.I)
    if m:
        amount = float(m.group(1).replace(",", "."))
        src, dst = m.group(2).upper(), m.group(3).upper()
        usd = amount / CURRENCY[src]
        out = usd * CURRENCY[dst]
        return f"تقريبًا: {amount} {src} ≈ {round(out,2)} {dst}"
    return None

# ===== ويكيبيديا =====
def answer_wikipedia(q: str) -> Optional[str]:
    try:
        s = wiki_summary(q, sentences=3, auto_suggest=False, redirect=True)
        return s
    except Exception:
        return None

# ===== RAG =====
def answer_rag(q: str, k: int = 4) -> Optional[str]:
    try:
        if RAG_EMB and rag_cache_ready():
            index = cache.get("rag:index")
            chunks = cache.get("rag:chunks")
            metas = cache.get("rag:metas")
            if index and chunks and metas:
                qv = RAG_EMB.encode([q], convert_to_numpy=True, normalize_embeddings=True)
                D, I = index.search(qv, k)
                picks = [i for i in I[0] if 0 <= i < len(chunks)]
                if picks:
                    ctx = "\n\n".join(chunks[i] for i in picks)
                    summ = summarize_text(ctx, max_sentences=6)
                    return f"{summ}\n\n(من ملفاتك المحلية)"
    except Exception:
        return None
    return None

# ===== Gemini =====
def answer_gemini(q: str) -> Optional[str]:
    if not GEMINI:
        return None
    try:
        resp = GEMINI.generate_content("أجب بالعربية الواضحة والودية:\n" + q)
        return resp.text.strip()
    except Exception:
        return None

# ===== ويب + تلخيص محلي =====
def answer_from_web(q: str) -> str:
    key = f"web:{q}"
    c = cache.get(key)
    if c:
        return c
    hits = ddg_text(q, n=5)
    contexts = []
    for h in hits:
        url = h.get("href") or h.get("url")
        if not url:
            continue
        txt = fetch_clean(url)
        if txt:
            contexts.append(txt)
    if not contexts:
        return "لم أجد نتائج كافية الآن، حاول بصيغة مختلفة."
    blob = "\n\n".join(contexts)
    summ = summarize_text(blob, max_sentences=5)
    ans = f"{summ}\n\n🔗 تم الاعتماد على نتائج من الويب."
    cache.set(key, ans, expire=3600)
    return ans

# ===== الموجه الرئيسي =====
def omni_answer(q: str) -> str:
    q = q.strip()
    if not q:
        return "اكتب سؤالك أولًا."

    a = answer_math(q)
    if a:
        return a

    a = answer_units_dates(q)
    if a:
        return a

    a = answer_wikipedia(q)
    if a:
        return a

    a = answer_rag(q)
    if a:
        return a

    a = answer_gemini(q)
    if a:
        return a

    return answer_from_web(q)
