# main.py — Bassam الذكي v3.4 (Self-Learning + RAG + Math)
from fastapi import FastAPI, Request, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

import os, json, time, re
from typing import List, Dict, Any

# === نصي وتلخيص ===
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from readability import Document
from sumy.parsers.plaintext import PlainTextParser        # ✅ تم التصحيح هنا
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

# === رياضيات ===
from sympy import symbols, sympify, diff, integrate, simplify, sin, cos, tan, log, exp

# === فهرسة RAG محلية (BM25) ===
from rank_bm25 import BM25Okapi

DATA_DIR = "data"
NOTES_DIR = os.path.join(DATA_DIR, "notes")
LEARN_PATH = os.path.join(NOTES_DIR, "learned.jsonl")
USAGE_PATH = os.path.join(DATA_DIR, "usage_stats.json")

app = FastAPI(title="Bassam الذكي 🤖", version="3.4")

# ------------------ الواجهة ------------------
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
except Exception:
    templates = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ------------------ مساعدة ------------------
def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(NOTES_DIR, exist_ok=True)
    if not os.path.exists(LEARN_PATH):
        open(LEARN_PATH, "a", encoding="utf-8").close()
    if not os.path.exists(USAGE_PATH):
        with open(USAGE_PATH, "w", encoding="utf-8") as f:
            json.dump({"requests": 0, "last_time": int(time.time())}, f)

_ensure_dirs()

def _read_md_txt_files() -> List[Dict[str, str]]:
    docs = []
    for root, _, files in os.walk(DATA_DIR):
        for fn in files:
            if fn.endswith(".md") or fn.endswith(".txt"):
                path = os.path.join(root, fn)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        docs.append({"file": path, "text": f.read()})
                except:
                    pass
    try:
        with open(LEARN_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)
                text = f"س: {obj.get('question','')}\nج: {obj.get('answer','')}\nوسوم:{','.join(obj.get('tags',[]))}"
                docs.append({"file": "learned", "text": text})
    except:
        pass
    return docs

def _tokenize_ar(s: str) -> List[str]:
    return re.findall(r"[\w\u0600-\u06FF]+", s.lower())

BM25_INDEX = None
BM25_CORPUS = []
BM25_DOCS: List[Dict[str, str]] = []

def build_index():
    global BM25_INDEX, BM25_CORPUS, BM25_DOCS
    BM25_DOCS = _read_md_txt_files()
    BM25_CORPUS = [_tokenize_ar(d["text"]) for d in BM25_DOCS]
    BM25_INDEX = BM25Okapi(BM25_CORPUS) if BM25_CORPUS else None
    return len(BM25_DOCS)

build_index()

# ------------------ ذكاء ------------------
def summarize_text(text: str, max_sentences: int = 3) -> str:
    try:
        try:
            parser = PlainTextParser.from_string(text, Tokenizer("arabic"))
        except Exception:
            parser = PlainTextParser.from_string(text, Tokenizer("english"))
        summ = TextRankSummarizer()
        sents = summ(parser.document, max_sentences)
        return " ".join(str(s) for s in sents) if sents else text[:400]
    except Exception:
        return text[:400]

def web_search(query: str):
    try:
        with DDGS() as ddgs:
            res = ddgs.text(query, region="xa-ar", max_results=3)
            return [{"title": r["title"], "link": r["href"], "snippet": r["body"]} for r in res]
    except Exception:
        return []

def rag_bm25(query: str, k: int = 3):
    if not BM25_INDEX:
        return []
    toks = _tokenize_ar(query)
    scores = BM25_INDEX.get_scores(toks)
    pairs = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:k]
    results = []
    for idx, sc in pairs:
        if sc < 1.0:
            continue
        doc = BM25_DOCS[idx]
        snippet = doc["text"][:600]
        results.append({"file": doc["file"], "score": float(sc), "snippet": snippet})
    return results

def solve_math(expr: str):
    try:
        x = symbols('x')
        parsed = sympify(expr)
        return {
            "input": str(parsed),
            "simplified": str(simplify(parsed)),
            "derivative": str(diff(parsed, x)),
            "integral": str(integrate(parsed, x)),
        }
    except Exception as e:
        return {"error": f"تعذر تحليل المعادلة: {e}"}

# ------------------ واجهات ------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if templates:
        return templates.TemplateResponse("index.html", {"request": request, "version": "v3.4"})
    return HTMLResponse("<h2>بسّام الذكي v3.4 يعمل ✅</h2>")

@app.get("/healthz")
def healthz():
    return {"status": "ok", "version": "3.4", "docs_indexed": len(BM25_DOCS)}

@app.get("/ask")
def ask(q: str = Query(..., description="سؤالك")):
    q = (q or "").strip()
    if not q:
        return {"error": "أدخل سؤالك"}

    if any(tok in q for tok in ["sin", "cos", "tan", "log", "exp", "^"]) or "مشتقة" in q or "تكامل" in q:
        return {"type": "math", "result": solve_math(q)}

    rag = rag_bm25(q, k=3)
    if rag:
        s = summarize_text(rag[0]["snippet"], 3)
        return {"type": "rag", "hits": rag, "summary": s}

    web = web_search(q)
    if web:
        for item in web:
            item["summary"] = summarize_text(item["snippet"], 2)
        return {"type": "web", "results": web}

    return {"msg": "لم أجد نتائج حول سؤالك."}

# ------------------ تشغيل ------------------
if __name__ == "__main__":
    import uvicorn, os
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
