# main.py — Bassam App (RAG + Web Search + Summarization + واجهة إدخال مباشرة)
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os, re, time, logging, requests
from typing import List, Dict, Any, Optional
from readability import Document
from bs4 import BeautifulSoup

# ---------- الإعدادات ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("bassam")

# ---------- التلخيص (Sumy) ----------
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

# ---------- البحث في DuckDuckGo ----------
try:
    from duckduckgo_search import DDGS
except Exception:
    DDGS = None

# ---------- الدماغ / RAG / المهارات ----------
RAG_AVAILABLE = False
BRAIN_AVAILABLE = False
SKILLS_AVAILABLE = False

rag_retrieve = None
brain_answer = None
list_skills = None

try:
    from rag.retriever import retrieve as rag_retrieve
    RAG_AVAILABLE = True
except Exception as e:
    log.info(f"RAG retriever not found: {e}")

try:
    from brain.omni_brain import answer as brain_answer
    BRAIN_AVAILABLE = True
except Exception as e:
    log.info(f"Brain not found: {e}")

try:
    from skills.registry import list_skills
    SKILLS_AVAILABLE = True
except Exception as e:
    log.info(f"Skills registry not found: {e}")

# ---------- إنشاء التطبيق ----------
app = FastAPI(title="Bassam App", version="3.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- الدوال المساعدة ----------
def clean_text(t: str) -> str:
    try:
        t = BeautifulSoup(t or "", "lxml").get_text(" ")
        return re.sub(r"\s+", " ", t).strip()
    except Exception:
        return (t or "").strip()

def summarize_text(text: str, sentences: int = 5, lang: str = "arabic") -> str:
    try:
        parser = PlaintextParser.from_string(text, Tokenizer(lang))
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
    hits = []
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
    parts = []
    for ch in chunks:
        ch = clean_text(ch)
        if ch:
            parts.append(summarize_text(ch, sentences_each))
    joined = "\n".join(parts)
    return summarize_text(joined, final_sentences) if joined else ""

def rag_pipeline(query: str, top_k: int = 5) -> Dict[str, Any]:
    out = {"used": False, "contexts": []}
    if not RAG_AVAILABLE or not rag_retrieve:
        return out
    try:
        docs = rag_retrieve(query, top_k=top_k) or []
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
        return brain_answer(query, contexts)
    except Exception as e:
        log.info(f"brain_pipeline error: {e}")
        return None

def smart_answer(query: str, k: int = 5) -> Dict[str, Any]:
    rag = rag_pipeline(query, top_k=k)
    contexts = rag["contexts"] if rag["used"] else []

    brain_out = brain_pipeline(query, contexts) if contexts else None

    web = None
    if not brain_out:
        web = web_pipeline(query, max_results=k)
        web_texts = [it["text"] for it in web["items"] if it.get("text")]
        brain_out = summarize_many(web_texts, 3, 6) or "لم أجد محتوى كافيًا للإجابة."

    if rag["used"] and not web and not brain_out:
        rag_texts = [c["text"] for c in contexts]
        brain_out = summarize_many(rag_texts, 3, 6)

    return {"answer": brain_out}

# ---------- المسارات ----------
@app.get("/healthz")
def healthz():
    return {"status": "ok", "time": int(time.time())}

# ✅ واجهة المستخدم التفاعلية
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html dir="rtl" lang="ar">
      <head>
        <meta charset="utf-8">
        <title>🧠 Bassam الذكي</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
          body{font-family:system-ui,Segoe UI,Tahoma;max-width:900px;margin:40px auto;padding:0 16px;line-height:1.8;background:#0b1220;color:#e7edf7}
          .row{display:flex;gap:8px}
          input[type=text]{flex:1;padding:12px 14px;border:1px solid #334;border-radius:12px;background:#1a2235;color:#e7edf7}
          button{padding:12px 16px;border:1px solid #334;border-radius:12px;background:#1f3a6d;color:#fff;cursor:pointer}
          button:hover{background:#2954a3}
          #answer{margin-top:18px;padding:16px;border:1px solid #334;border-radius:12px;background:#141b2e;white-space:pre-wrap;line-height:1.7}
          #status{color:#9bb0c8;margin-top:10px}
        </style>
      </head>
      <body>
        <h2>🧠 Bassam App — مساعد عربي ذكي</h2>
        <form id="ask-form" class="row">
          <input id="q" name="q" type="text" placeholder="اكتب سؤالك هنا..." required autofocus />
          <button type="submit">اسأل</button>
        </form>
        <div id="status"></div>
        <div id="answer" hidden></div>

        <script>
          const form = document.getElementById('ask-form');
          const input = document.getElementById('q');
          const status = document.getElementById('status');
          const answer = document.getElementById('answer');

          form.addEventListener('submit', async (e) => {
            e.preventDefault();
            status.textContent = '⏳ جارٍ المعالجة...';
            answer.hidden = true;
            try {
              const res = await fetch(`/ask?q=${encodeURIComponent(input.value)}`);
              const data = await res.json();
              if (data.answer) {
                answer.textContent = data.answer;
                answer.hidden = false;
                status.textContent = '';
              } else {
                status.textContent = '❗️لم يتم العثور على إجابة.';
              }
            } catch (err) {
              status.textContent = '⚠️ حدث خطأ أثناء الاتصال بالخادم.';
            }
          });
        </script>
      </body>
    </html>
    """

@app.get("/ask")
def api_ask(q: str):
    result = smart_answer(q)
    return JSONResponse(result)

# ---------- تشغيل محلي ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
