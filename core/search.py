# core/search.py — meta search + fetch + mini-RAG
from typing import List, Dict, Optional
import time, re, os, math, html, requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from readability import Document
from duckduckgo_search import DDGS

from .arabic_text import is_arabic, strip_html_preserve_lines
from .utils import dedup_by_url, clamp, simple_md_search

HEADERS = {"User-Agent": "Mozilla/5.0 (BassamBot; +bassam-app)"}

PREFERRED_AR_SITES = [
    "wikipedia.org", "ar.wikipedia.org", "mawdoo3.com", "aljazeera.net",
    "alarabiya.net", "cnn.com", "bbc.com/arabic", "almrsal.com",
]

def ddg_web(query: str, max_results: int = 10) -> List[Dict]:
    # نستخدم DDGS لأنه مجاني وخفيف
    hits: List[Dict] = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results, region="wt-wt", safesearch="moderate"):
                if not r: continue
                url = r.get("href") or r.get("url")
                title = r.get("title") or ""
                body  = r.get("body") or ""
                if url:
                    hits.append({"title": title, "url": url, "snippet": body})
    except Exception:
        pass
    return hits

def score_hit(hit: Dict, query: str) -> float:
    url = hit["url"]
    host = urlparse(url).netloc.lower()
    s = 0.0
    if any(site in host for site in PREFERRED_AR_SITES): s += 2.0
    if is_arabic(hit.get("title","") + hit.get("snippet","")): s += 1.0
    if re.search(re.escape(query), (hit.get("title","") + hit.get("snippet","")), re.I): s += 0.5
    return s

def fetch_clean(url: str, timeout: int = 12) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        html_doc = r.text
        # readability لاستخراج المقال
        doc = Document(html_doc)
        article_html = doc.summary()
        text = strip_html_preserve_lines(article_html)
        if len(text) < 400:
            # احتياط: نجمع نص الصفحة مباشرة
            soup = BeautifulSoup(html_doc, "html.parser")
            text = strip_html_preserve_lines(str(soup))
        return text[:12000]  # نحمي الذاكرة
    except Exception:
        return ""

def gather_passages(hits: List[Dict], top_k: int = 6) -> List[Dict]:
    passages = []
    for h in hits[:top_k]:
        txt = fetch_clean(h["url"])
        if not txt: continue
        passages.append({"url": h["url"], "text": txt})
    return passages

def rag_from_data_folder(query: str, folder: str = "data") -> List[Dict]:
    """بحث مفتاحي بسيط داخل ملفات ماركداون/تكست التي في data/"""
    if not os.path.isdir(folder): return []
    matches = simple_md_search(folder, query, max_files=30, max_chars=8000)
    return [{"url": f"file://{p}", "text": t} for p, t in matches]

def detect_lang(text: str) -> str:
    return "ar" if is_arabic(text) else "xx"

def deep_search(query: str, max_sources: int = 6, force_lang: Optional[str] = None) -> Dict:
    t0 = time.time()
    hits = ddg_web(query, max_results=max_sources*2)
    hits = sorted(hits, key=lambda h: score_hit(h, query), reverse=True)
    hits = dedup_by_url(hits)
    passages = gather_passages(hits, top_k=max_sources)

    # دمج RAG محلي
    local_passages = rag_from_data_folder(query)
    passages = (passages + local_passages)[:max_sources+4]

    sources = []
    for h in hits[:max_sources]:
        host = urlparse(h["url"]).netloc
        sources.append({
            "title": h.get("title",""),
            "url": h["url"],
            "site": host,
            "lang": "ar" if is_arabic(h.get("title","")+h.get("snippet","")) else "non-ar",
            "score": round(score_hit(h, query), 2)
        })

    return {
        "t0": t0,
        "detected_lang": force_lang or detect_lang(query),
        "sources": sources,
        "passages": passages,
        "tokens_used": 0
    }
