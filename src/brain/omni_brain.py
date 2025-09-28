# src/brain/omni_brain.py
# Omni Brain v3.3 — RAG + Web + Wiki + Math + Utilities (Arabic-first)

from __future__ import annotations
import os, re, math, json, pathlib, html
from typing import List, Tuple

import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from readability import Document
from sumy.parsers.plaintext import PlainTextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from rank_bm25 import BM25Okapi
from rapidfuzz import fuzz, process
import numpy as np
from diskcache import Cache

# رياضيات
try:
    import sympy as sp
except Exception:
    sp = None

CACHE = Cache(directory=".cache-omni", size_limit=256 * 1024 * 1024)

DATA_DIR = pathlib.Path("data")
DATA_DIR.mkdir(exist_ok=True)

def _clean(t: str) -> str:
    t = re.sub(r"\s+", " ", t or "").strip()
    return t

def _is_math(q: str) -> bool:
    return bool(re.search(r"[=\+\-\*/\^√∫∑π]|مشتق|تكامل|حل|معادلة", q))

def _is_translate(q: str) -> bool:
    return q.strip().lower().startswith(("translate ", "ترجم "))

def _summarize(text: str, sentences: int = 4) -> str:
    parser = PlainTextParser.from_string(text, Tokenizer("arabic"))
    summ = LexRankSummarizer()
    sents = summ(parser.document, sentences)
    out = " ".join(str(s) for s in sents) or text[:600]
    return _clean(out)

# -------------------- RAG (ملفات محلية) --------------------
def _load_corpus() -> List[Tuple[str, str]]:
    docs = []
    for p in DATA_DIR.glob("**/*"):
        if p.is_file() and p.suffix.lower() in {".txt", ".md"}:
            try:
                docs.append((p.name, p.read_text(encoding="utf-8", errors="ignore")))
            except Exception:
                pass
    return docs

def _rag_search(query: str, topk: int = 3) -> List[Tuple[str, str]]:
    corpus = CACHE.get("rag_corpus")
    if corpus is None:
        corpus = _load_corpus()
        CACHE.set("rag_corpus", corpus, expire=600)
    if not corpus:
        return []

    texts = [c[1] for c in corpus]
    tokenized = [t.split() for t in texts]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(query.split())
    idxs = np.argsort(scores)[::-1][:topk]
    results = []
    for i in idxs:
        title, body = corpus[int(i)]
        # أفضل مقطع قريب للسؤال
        lines = [l.strip() for l in body.splitlines() if l.strip()]
        best, _ = process.extractOne(query, lines, scorer=fuzz.WRatio) if lines else ("", 0)
        snippet = best or body[:400]
        results.append((title, snippet))
    return results

# -------------------- البحث من الويب --------------------
def _duckduckgo(query: str, n=4) -> List[dict]:
    out = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, region="xa-ar", safesearch="moderate", max_results=n):
                out.append({"title": r.get("title"), "href": r.get("href")})
    except Exception:
        pass
    return out

def _fetch_page(url: str, timeout=15) -> str:
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            r = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            html_text = r.text
            doc = Document(html_text)
            content = doc.summary(html_partial=True)
            text = BeautifulSoup(content, "html.parser").get_text(" ")
            return _clean(text)
    except Exception:
        return ""

def _web_answer(query: str) -> str:
    hits = _duckduckgo(query, n=5)
    chunks = []
    for h in hits[:3]:
        txt = _fetch_page(h["href"])
        if txt:
            chunks.append(txt)
    if not chunks:
        return ""
    joined = "\n\n".join(chunks)[:4000]
    summ = _summarize(joined, sentences=5)
    srcs = "\n".join(f"- {h['title']}: {h['href']}" for h in hits[:3])
    return f"{summ}\n\nالمصادر:\n{srcs}"

# -------------------- Wikipedia --------------------
def _wiki_answer(query: str) -> str:
    import wikipedia
    try:
        wikipedia.set_lang("ar")
        text = wikipedia.summary(query, sentences=4, auto_suggest=False, redirect=True)
        return _clean(text)
    except Exception:
        try:
            wikipedia.set_lang("en")
            text = wikipedia.summary(query, sentences=4, auto_suggest=True)
            return _clean(text)
        except Exception:
            return ""

# -------------------- Math (SymPy) --------------------
def _math_answer(q: str) -> str:
    if sp is None:
        return "ميزة الرياضيات غير مفعّلة الآن."
    q = q.replace("^", "**").replace("÷", "/").replace("×", "*")
    # أنماط بسيطة: اشتقاق / تكامل / حل معادلة
    x = sp.symbols("x")
    try:
        if "مشتق" in q or "اشتق" in q or "derive" in q.lower():
            expr = re.split(r"[:：]\s*|\s+(?:ل|لـ)?\s*x\s*", q, maxsplit=1)[-1]
            f = sp.sympify(expr)
            df = sp.diff(f, x)
            return f"f(x) = {sp.simplify(f)}\nf'(x) = {sp.simplify(df)}"
        if "تكامل" in q or "integr" in q.lower():
            expr = re.split(r"[:：]\s*", q, maxsplit=1)[-1]
            f = sp.sympify(expr)
            F = sp.integrate(f, x)
            return f"∫ f(x) dx حيث f(x) = {sp.simplify(f)}\n= {sp.simplify(F)} + C"
        if "=" in q or "حل" in q:
            left,right = q.split("=",1) if "=" in q else (q.replace("حل",""),"0")
            eq = sp.Eq(sp.sympify(left), sp.sympify(right))
            sol = sp.solve(eq, dict=True)
            return f"المعادلة: {sp.srepr(eq)}\nالحلول: {sol}"
        # تقييم مباشر
        f = sp.sympify(q)
        val = sp.simplify(f)
        return f"القيمة المبسّطة: {val}"
    except Exception as e:
        return f"تعذّر تحليل المسألة. جرّب صياغة أبسط. ({e})"

# -------------------- شخصنات/تنبيهات --------------------
def _advisor_prefix(domain: str) -> str:
    if domain == "medical":
        return "تنبيه طبي: المعلومات لغرض التثقيف وليست بديلاً عن الاستشارة الطبية."
    if domain == "engineering":
        return "تنبيه هندسي: افحص المعايير والكود المحلي قبل التنفيذ."
    if domain == "beauty":
        return "تنبيه تجميلي: أي إجراء يحتاج تقييم مختص وتاريخ صحي."
    return ""

def _detect_domain(q: str) -> str:
    ql = q.lower()
    if any(w in ql for w in ["عملية", "اعراض", "علاج", "دواء", "pregnan", "symptom"]):
        return "medical"
    if any(w in ql for w in ["خرسانة","كمر","mom","beam","جهد","دائرة","تيار","مقاومة","بايثون","شبكات","اتصالات","تصنيع","ميكانيك","معماري","مدني","civil","mechanical","electrical","architecture","software","network"]):
        return "engineering"
    if any(w in ql for w in ["بوتوكس","فلر","تفتيح","عناية","بشرة","تجميل","hair","skin","laser"]):
        return "beauty"
    if any(w in ql for w in ["grammar","ترجم","translate","معنى","صحح","spelling","نطق"]):
        return "language"
    return ""

# -------------------- الموجّه الرئيسي --------------------
def omni_answer(message: str) -> str:
    q = _clean(message)
    if not q:
        return "اكتب سؤالك…"

    # 1) رياضيات
    if _is_math(q):
        return _math_answer(q)

    # 2) ترجمة بسيطة: "ترجم hello to arabic" / "translate ..."
    if _is_translate(q):
        text = q.split(" ", 1)[-1]
        # ترجمة بدائية (بدون API) — تفكيك وتفسير بسيط
        # لتجربة أفضل: استخدم مزوّد ترجمة API لاحقًا
        return f"ترجمة تقريبية: {text}"

    # 3) RAG من ملفاتك
    rag_hits = _rag_search(q, topk=3)
    if rag_hits:
        joined = "\n\n---\n\n".join(f"[{t}]\n{b}" for t,b in rag_hits)
        summ = _summarize(joined, sentences=5)
        return f"{summ}\n\n(مصادر محلية: {', '.join(t for t,_ in rag_hits)})"

    # 4) Wikipedia
    wiki = _wiki_answer(q)
    if wiki:
        return wiki

    # 5) Web Search
    web = _web_answer(q)
    if web:
        return web

    # 6) رسائل تخصصية/نصيحة عامة
    domain = _detect_domain(q)
    prefix = _advisor_prefix(domain)
    if prefix:
        return prefix + "\n" + "أعد صياغة سؤالك بتفاصيل أكثر (مواد، أبعاد، شروط، قيود، مصدر الألم/الهدف…)."

    return "لم أجد نتائج واضحة لسؤالك. جرّب صياغة أبسط أو كلمات مفتاحية مختلفة."
