from typing import List, Dict, Optional
import time, re, requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from readability import Document
from duckduckgo_search import DDGS
from .arabic_text import is_arabic, strip_html_preserve_lines
from .utils import dedup_by_url

HEADERS = {"User-Agent": "Mozilla/5.0 (BassamBot)"}

PREFERRED_AR_SITES = [
    "ar.wikipedia.org", "wikipedia.org", "mawdoo3.com", "aljazeera.net",
    "alarabiya.net", "bbc.com/arabic", "almrsal.com"
]

# ---------- web search ----------

def ddg_web(query: str, max_results: int = 10) -> List[Dict]:
    hits: List[Dict] = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results, region="wt-wt", safesearch="moderate"):
                if not r: continue
                url = r.get("href") or r.get("url")
                title = r.get("title") or ""; body = r.get("body") or ""
                if url: hits.append({"title": title, "url": url, "snippet": body})
    except Exception:
        pass
    return hits

def score_hit(hit: Dict, query: str) -> float:
    url = hit["url"]; host = urlparse(url).netloc.lower(); s = 0.0
    if any(site in host for site in PREFERRED_AR_SITES): s += 2.0
    if is_arabic((hit.get("title","") + hit.get("snippet",""))): s += 1.0
    if re.search(re.escape(query), (hit.get("title","") + hit.get("snippet","")), re.I): s += 0.5
    return s

# ---------- fetch & clean ----------

def fetch_clean(url: str, timeout: int = 12) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        html_doc = r.text
        doc = Document(html_doc)
        article_html = doc.summary()
        text = strip_html_preserve_lines(article_html)
        if len(text) < 300:
            soup = BeautifulSoup(html_doc, "html.parser")
            text = strip_html_preserve_lines(str(soup))
        return text[:12000]
    except Exception:
        return ""

# ---------- deep search (with mini-RAG from data/) ----------

def _gather_passages(hits: List[Dict], top_k: int = 6) -> List[Dict]:
    passages = []
    for h in hits[:top_k]:
        txt = fetch_clean(h["url"])
        if not txt: continue
        passages.append({"url": h["url"], "text": txt})
    return passages

import os, glob

def _rag_local(query: str, folder: str = "data") -> List[Dict]:
    if not os.path.isdir(folder): return []
    out = []
    for p in glob.glob(os.path.join(folder, "*.txt")) + glob.glob(os.path.join(folder, "*.md")):
        try:
            t = open(p, "r", encoding="utf-8", errors="ignore").read()
            if query.lower() in t.lower():
                out.append({"url": f"file://{p}", "text": t[:8000]})
        except Exception:
            pass
    return out[:4]

def deep_search(query: str, max_sources: int = 6, force_lang: Optional[str] = None) -> Dict:
    t0 = time.time()
    hits = ddg_web(query, max_results=max_sources*2)
    hits = sorted(hits, key=lambda h: score_hit(h, query), reverse=True)
    hits = dedup_by_url(hits)

    passages = _gather_passages(hits, top_k=max_sources)
    passages = (passages + _rag_local(query))[:max_sources+4]

    sources = []
    for h in hits[:max_sources]:
        host = urlparse(h["url"]).netloc
        sources.append({
            "title": h.get("title",""), "url": h["url"], "site": host,
            "lang": "ar" if is_arabic(h.get("title","")+h.get("snippet","")) else "non-ar",
            "score": round(score_hit(h, query), 2)
        })

    return {"t0": t0, "detected_lang": force_lang or ("ar" if is_arabic(query) else "xx"),
            "sources": sources, "passages": passages}
