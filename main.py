# main.py — Bassam App (RAG + Web Search + Summarization) — Ready for Render
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os, re, time, logging, requests
from typing import List, Dict, Any, Optional

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("bassam")

# ---------- Summarization (sumy) ----------
from sumy.parsers.plaintext import PlainTextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

# ---------- Readability helpers ----------
from readability import Document
from bs4 import BeautifulSoup

# ---------- Web Search (DuckDuckGo) ----------
try:
    from duckduckgo_search import DDGS
except Exception:
    DDGS = None

# ---------- Optional: Local RAG / Brain / Skills ----------
RAG_AVAILABLE = False
BRAIN_AVAILABLE = False
SKILLS_AVAILABLE = False

rag_retrieve = None
brain_answer = None
list_skills = None

try:
    # توقع واجهة: retrieve(query: str, top_k: int = 5) -> List[Dict{title,url,text,score?}]
    from rag.retriever import retrieve as rag_retrieve
    RAG_AVAILABLE = True
    log.info("RAG retriever loaded.")
except Exception as e:
    log.info(f"RAG retriever not found: {e}")

try:
    # توقع واجهة: answer(query: str, context: List[Dict]) -> str
    from brain.omni_brain import answer as brain_answer
    BRAIN_AVAILABLE = True
    log.info("Brain (omni_brain) loaded.")
except Exception as e:
    log.info(f"Brain not found: {e}")

try:
    # توقع واجهة: list_skills() -> List[str] (اختياري)
    from skills.registry import list_skills
    SKILLS_AVAILABLE = True
    log.info("Skills registry loaded.")
except Exception as e:
    log.info(f"Skills registry not found: {e}")

# ---------- FastAPI ----------
app = FastAPI(title="Bassam App", version="3.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ---------- Utils ----------
def clean_text(t: str) -> str:
    try:
        t = BeautifulSoup(t or "", "lxml").get_text(" ")
        t = re.sub(r"\s+", " ", t).strip()
        return t
    except Exception:
        return (t or "").strip()

def summarize_text(text: str, sentences: int = 5, lang: str = "arabic") -> str:
    try:
        parser = PlainTextParser.from_string(text, Tokenizer(lang))
        summarizer = TextRankSummarizer()
        summary = summarizer(parser.document, sentences)
        out = "\n".join(str(s) for s in summary).strip()
        return out if out else text
    except Exception as e:
        log.warning(f"summarize_text error: {e}")
        return text

def fetch_readable(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; BassamBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        doc = Document(resp.text)
        article_html = doc.summary()
        article_text = clean_text(article_html)
        if len(article_text) < 400:
            article_text = clean_text(resp.text)
        return article_text
    except Exception as e:
        log.info(f"fetch_readable fail {url}: {e}")
        return ""

def ddg_search(q: str, max_results: int = 5) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    if not DDGS:
        return hits
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(q, region="xa-ar", max_results=max_results):
                hits.append(r)
    except Exception as e:
        log.info(f"DDG search error: {e}")
    return hits

def summarize_many(chunks: List[str], sentences_each: int = 3, final_sentences: int = 6) -> str:
    # لخص كل جزء ثم لخص المُلخصات
    partials = []
    for ch in chunks:
        ch = clean_text(ch)
        if ch:
            partials.append(summarize_text(ch, sentences_each))
    joined = "\n".join(partials)
    return summarize_text(joined, final_sentences) if joined else ""

# ---------- Strategy: smart answer ----------
def rag_pipeline(query: str, top_k: int = 5) -> Dict[str, Any]:
    out = {"used": False, "contexts": [], "answer": ""}
    if not RAG_AVAILABLE or not rag_retrieve:
        return out
    try:
        docs = rag_retrieve(query, top_k=top_k) or []
        # توقع كل doc: {title, url, text, score?}
        contexts = []
        for d in docs:
            title = d.get("title") or ""
            url = d.get("url") or ""
            text = d.get("text") or ""
            if not text:
                continue
            contexts.append({"title": title, "url": url, "text": text[:8000]})
        out["used"] = len(contexts) > 0
        out["contexts"] = contexts
        return out
    except Exception as e:
        log.info(f"rag_pipeline error: {e}")
        return out

def web_pipeline(query: str, max_results: int = 5) -> Dict[str, Any]:
    hits = ddg_search(query, max_results=max_results)
    items = []
    for h in hits:
        url = h.get("href") or h.get("url")
        title = h.get("title") or ""
        snippet = h.get("body") or h.get("snippet") or ""
        text = fetch_readable(url) if url else ""
        items.append({"title": title, "url": url, "snippet": snippet, "text": text})
    return {"items": items}

def brain_pipeline(query: str, contexts: List[Dict[str, Any]]) -> Optional[str]:
    if not BRAIN_AVAILABLE or not brain_answer:
        return None
    try:
        return brain_answer(query, contexts)  # يُفترض أن يولد جوابًا مستندًا للسياق
    except Exception as e:
        log.info(f"brain_pipeline error: {e}")
        return None

def smart_answer(query: str, k: int = 5) -> Dict[str, Any]:
    # 1) RAG
    rag = rag_pipeline(query, top_k=k)
    contexts = rag["contexts"] if rag["used"] else []

    # 2) Brain (إن وجد)
    brain_out = brain_pipeline(query, contexts) if contexts else None

    # 3) إن لم يتوفر brain أو لا يوجد سياق كافٍ، نلجأ للويب
    web = None
    if not brain_out:
        web = web_pipeline(query, max_results=k)
        web_texts = [it["text"] for it in web["items"] if it.get("text")]
        combined = summarize_many(web_texts, sentences_each=3, final_sentences=6)
        brain_out = combined or "لم أجد محتوى كافيًا للإجابة."

    # 4) إن توفر سياق RAG بدون Brain، نعطي ملخصًا يستند إلى السياقات
    if rag["used"] and not web and not brain_out:
        rag_texts = [c["text"] for c in contexts]
        brain_out = summarize_many(rag_texts, sentences_each=3, final_sentences=6)

    return {
        "answer": brain_out,
        "rag_used": rag["used"],
        "rag_contexts": [{"title": c["title"], "url": c["url"]} for c in contexts],
        "web_used": web is not None,
        "web_sources": [{"title": i["title"], "url": i["url"]} for i in (web["items"] if web else [])],
    }

# ---------- Routes ----------
@app.get("/healthz")
def healthz():
    return {"status": "ok", "time": int(time.time())}

@app.get("/", response_class=HTMLResponse)
def home():
    skills_html = ""
    if SKILLS_AVAILABLE and callable(list_skills):
        try:
            sk = list_skills() or []
            skills_html = "<p><b>Skills:</b> " + ", ".join(sk) + "</p>"
        except Exception:
            pass
    return f"""
    <html dir="rtl" lang="ar">
      <head><meta charset="utf-8"><title>Bassam App</title>
      <style>body{{font-family:system-ui,Segoe UI,Tahoma;max-width:900px;margin:40px auto;padding:0 16px;line-height:1.8}}</style>
      </head>
      <body>
        <h2>👋 أهلاً بك في Bassam App (v3.1)</h2>
        <ul>
          <li><code>/healthz</code> — فحص الصحة</li>
          <li><code>/ask?q=ما هو RAG</code> — إجابة ذكية (RAG + ويب)</li>
          <li><code>/search?q=الذكاء الاصطناعي</code> — بحث ويب + تلخيص</li>
          <li><code>/summarize?text=...&sentences=5</code> — تلخيص نص</li>
        </ul>
        <p>RAG: {"✅" if RAG_AVAILABLE else "❌"} • Brain: {"✅" if BRAIN_AVAILABLE else "❌"} • Skills: {"✅" if SKILLS_AVAILABLE else "❌"}</p>
        {skills_html}
      </body>
    </html>
    """

@app.get("/summarize")
def api_summarize(
    text: str = Query(..., description="النص المطلوب تلخيصه"),
    sentences: int = Query(5, ge=1, le=15),
    lang: str = Query("arabic")
):
    text = clean_text(text)
    summary = summarize_text(text, sentences, lang)
    return JSONResponse({"summary": summary, "sentences": sentences, "lang": lang})

@app.get("/search")
def api_search(
    q: str = Query(..., description="كلمات البحث"),
    max_results: int = Query(5, ge=1, le=10),
    summarize_sentences: int = Query(4, ge=1, le=10)
):
    results = []
    hits = ddg_search(q, max_results=max_results) if DDGS else []
    for h in hits:
        url = h.get("href") or h.get("url")
        title = h.get("title") or ""
        snippet = h.get("body") or h.get("snippet") or ""
        page_text = fetch_readable(url) if url else ""
        summary = summarize_text(page_text, summarize_sentences) if page_text else ""
        results.append({
            "title": title, "url": url,
            "snippet": snippet, "summary": summary, "chars": len(page_text)
        })
    if not results and not DDGS:
        return JSONResponse({"error": "duckduckgo_search not available"}, status_code=500)
    return JSONResponse({"query": q, "results": results})

@app.get("/ask")
def api_ask(
    q: str = Query(..., description="سؤالك/مهمتك"),
    k: int = Query(5, ge=1, le=10)
):
    out = smart_answer(q, k)
    return JSONResponse({"query": q, **out})

# ---------- Local run ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
