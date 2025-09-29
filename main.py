# main.py — Bassam الذكي v4.1
# Chat + RAG + Deep Web + Math + PDF/Image + Download
# (يعمل بلا نماذج ثقيلة — جاهز للنشر على Render)

from fastapi import FastAPI, Request, Query, Body, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

import os, json, time, re, shutil
from typing import List, Dict, Any
from urllib.parse import urlparse, quote

# -------- Web / Text --------
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
from readability import Document

# -------- Summarization (sumy) --------
try:
    from sumy.parsers.text import PlaintextParser
except Exception:
    from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

# -------- Math --------
from sympy import symbols, sympify, diff, integrate, simplify

# -------- RAG BM25 --------
from rank_bm25 import BM25Okapi

# -------- Files / PDF / Images --------
from pypdf import PdfReader
from PIL import Image

# -------- HTTP client (download/proxy) --------
import httpx


# =========================
# 1) تهيئة التطبيق والمجلدات
# =========================
app = FastAPI(title="Bassam الذكي 🤖", version="4.1")

DATA_DIR     = "data"
NOTES_DIR    = os.path.join(DATA_DIR, "notes")
FILES_DIR    = "files"
UPLOADS_DIR  = os.path.join(FILES_DIR, "uploads")
LEARN_PATH   = os.path.join(NOTES_DIR, "learned.jsonl")
USAGE_PATH   = os.path.join(DATA_DIR,  "usage_stats.json")

for d in (DATA_DIR, NOTES_DIR, FILES_DIR, UPLOADS_DIR):
    os.makedirs(d, exist_ok=True)

app.mount("/files", StaticFiles(directory=FILES_DIR), name="files")

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


# =========================
# 2) أدوات مساعدة
# =========================
def summarize_text(text: str, max_sentences: int = 3) -> str:
    try:
        parser = PlaintextParser.from_string(text or "", Tokenizer("arabic"))
        sents = TextRankSummarizer()(parser.document, max_sentences)
        return " ".join(map(str, sents)) if sents else (text or "")[:400]
    except Exception:
        return (text or "")[:400]

def _tokenize_ar(s: str) -> List[str]:
    return re.findall(r"[\w\u0600-\u06FF]+", (s or "").lower())

def ensure_safe_filename(name: str) -> str:
    name = re.sub(r"[^\w\-.]+", "_", name or "")
    return name[:120] or f"file_{int(time.time())}"

def log_usage():
    try:
        if not os.path.exists(USAGE_PATH):
            with open(USAGE_PATH, "w", encoding="utf-8") as f:
                json.dump({"requests": 0, "last_time": int(time.time())}, f)
        with open(USAGE_PATH, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["requests"] = int(data.get("requests", 0)) + 1
            data["last_time"] = int(time.time())
            f.seek(0); json.dump(data, f); f.truncate()
    except Exception:
        pass

def answer_bubble(text: str, sources: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    resp = {"type": "chat", "answer": text.strip()}
    if sources:
        out = []
        for s in sources:
            s = dict(s)
            s["summary"] = summarize_text(s.get("snippet", ""), 2)
            out.append(s)
        resp["sources"] = out
    return resp


# =========================
# 3) RAG (BM25 محلي)
# =========================
def _read_md_txt_files() -> List[Dict[str, str]]:
    docs = []
    for root, _, files in os.walk(DATA_DIR):
        for fn in files:
            if fn.endswith(".md") or fn.endswith(".txt"):
                p = os.path.join(root, fn)
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        docs.append({"file": p, "text": f.read()})
                except:
                    pass
    # بنك التعلّم الذاتي
    try:
        with open(LEARN_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                obj = json.loads(line)
                text = f"س: {obj.get('question','')}\nج: {obj.get('answer','')}\nوسوم:{','.join(obj.get('tags',[]))}"
                docs.append({"file": "learned", "text": text})
    except:
        pass
    return docs

BM25_INDEX = None
BM25_DOCS  = []
BM25_CORPUS = []

def build_index():
    global BM25_INDEX, BM25_DOCS, BM25_CORPUS
    BM25_DOCS = _read_md_txt_files()
    BM25_CORPUS = [_tokenize_ar(d["text"]) for d in BM25_DOCS]
    BM25_INDEX = BM25Okapi(BM25_CORPUS) if BM25_CORPUS else None
    return len(BM25_DOCS)

def rag_bm25(query: str, k=3):
    if not BM25_INDEX:
        return []
    toks = _tokenize_ar(query)
    scores = BM25_INDEX.get_scores(toks)
    pairs = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:k]
    res = []
    for idx, sc in pairs:
        if sc < 1.0: continue
        doc = BM25_DOCS[idx]
        res.append({"file": doc["file"], "score": float(sc), "snippet": doc["text"][:1000]})
    return res

build_index()


# =========================
# 4) رياضيات
# =========================
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


# =========================
# 5) بحث ويب مُعزّز (عنيد) + بحث منصّاتي
# =========================
AR_DIGITS_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def normalize_ar(text: str) -> str:
    """تطبيع عربي بسيط (حذف تشكيل/إطالة/توحيد همزات/أرقام عربية)."""
    t = (text or "").strip()
    t = re.sub(r"[\u064B-\u0652\u0640]", "", t)
    t = t.replace("أ","ا").replace("إ","ا").replace("آ","ا").replace("ى","ي").replace("ؤ","و").replace("ئ","ي")
    t = t.translate(AR_DIGITS_MAP)
    t = re.sub(r"\s+", " ", t).strip()
    return t

QUERY_SYNONYMS = [
    ("ابحث", "ابحث عن"),
    ("سعر", "ثمن"),
    ("تعريف", "ما هو"),
]

def expand_queries(q: str) -> list[str]:
    base = [q]
    for a, b in QUERY_SYNONYMS:
        if a in q: base.append(q.replace(a, b))
    out = []
    for s in base:
        out.append(s)
        out.append(s + " ")
    return list(dict.fromkeys(out))

def _ddg_text(query: str, limit: int = 8, timelimit: str | None = None):
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(
                query, region="xa-ar", safesearch="off",
                max_results=limit, timelimit=timelimit
            )) or []
    except Exception:
        return []

def _duckduckgo_html_scrape(q: str, limit: int = 10):
    try:
        url = "https://duckduckgo.com/html/?q=" + quote(q, safe="")
        headers = {"User-Agent": "Mozilla/5.0 (BassamBot)"}
        with httpx.Client(headers=headers, follow_redirects=True, timeout=20.0) as c:
            r = c.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for a in soup.select(".result__a"):
            link = a.get("href")
            title = a.get_text(" ", strip=True)
            par = a.find_parent(class_="result")
            snippet = ""
            if par:
                sn = par.select_one(".result__snippet")
                if sn: snippet = sn.get_text(" ", strip=True)
            if link and title:
                items.append({"title": title, "href": link, "body": snippet})
            if len(items) >= limit:
                break
        return items
    except Exception:
        return []

def web_search_strong(q: str, limit: int = 10) -> list[dict]:
    """1) ddg بصيغ متعددة + timelimit  2) fallback كشط HTML  3) تلخيص مقتطفات"""
    qn = normalize_ar(q)
    variants = expand_queries(qn)
    hits: list[dict] = []
    seen = set()

    for v in variants:
        for t in (None, "w", "m"):  # أسبوع، شهر
            res = _ddg_text(v, limit=min(8, limit), timelimit=t)
            for r in res:
                link = r.get("href") or r.get("link")
                if not link or link in seen: 
                    continue
                seen.add(link)
                hits.append({
                    "title": r.get("title",""),
                    "link":  link,
                    "snippet": r.get("body","")
                })
                if len(hits) >= limit:
                    break
            if len(hits) >= limit: break
        if len(hits) >= limit: break

    if len(hits) < max(3, limit//2):
        scraped = _duckduckgo_html_scrape(qn, limit=limit)
        for r in scraped:
            link = r.get("href")
            if not link or link in seen: 
                continue
            seen.add(link)
            hits.append({
                "title": r.get("title",""),
                "link":  link,
                "snippet": r.get("body","")
            })

    for h in hits:
        h["summary"] = summarize_text(h.get("snippet",""), 2)
    return hits[:limit]

PLATFORM_FILTERS = {
    "social":  ["site:x.com","site:twitter.com","site:facebook.com","site:instagram.com",
                "site:linkedin.com","site:tiktok.com","site:reddit.com","site:snapchat.com"],
    "video":   ["site:youtube.com","site:vimeo.com","site:tiktok.com","site:dailymotion.com"],
    "markets": ["site:alibaba.com","site:amazon.com","site:aliexpress.com",
                "site:etsy.com","site:ebay.com","site:noon.com"],
    "gov":     ["site:gov","site:gov.sa","site:gov.ae","site:gov.eg","site:edu","site:edu.sa","site:edu.eg"],
    "all":     []
}

def deep_search(q: str, mode: str = "all", per_site: int = 4, max_total: int = 30):
    domains = PLATFORM_FILTERS.get(mode, [])
    if not domains:
        return web_search_strong(q, limit=max_total)

    out, seen = [], set()
    for dom in domains:
        res = web_search_strong(f"{q} {dom}", limit=per_site)
        for r in res:
            link = r.get("link")
            if not link or link in seen: 
                continue
            seen.add(link)
            r["domain"] = dom.replace("site:","")
            out.append(r)
            if len(out) >= max_total:
                break
        if len(out) >= max_total:
            break
    return out


# =========================
# 6) PDF/صورة + تنزيل
# =========================
def extract_pdf_text(path: str) -> str:
    try:
        reader = PdfReader(path)
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        return ""

@app.post("/upload/pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "ارفع ملف PDF فقط.")
    safe = ensure_safe_filename(file.filename)
    dest = os.path.join(UPLOADS_DIR, safe)
    with open(dest, "wb") as out:
        shutil.copyfileobj(file.file, out)
    text = extract_pdf_text(dest)
    if text.strip():
        txt = safe.rsplit(".",1)[0] + ".txt"
        with open(os.path.join(DATA_DIR, txt), "w", encoding="utf-8") as f:
            f.write(text)
        n = build_index()
    else:
        n = len(BM25_DOCS)
    return {"ok": True, "file_url": f"/files/uploads/{safe}", "indexed_docs": n}

@app.post("/upload/image")
async def upload_image(request: Request, file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in [".jpg",".jpeg",".png",".webp",".bmp"]:
        raise HTTPException(400, "ارفع صورة بصيغة jpg/png/webp/bmp.")
    safe = ensure_safe_filename(file.filename or f"img_{int(time.time())}{ext}")
    dest = os.path.join(UPLOADS_DIR, safe)
    with open(dest, "wb") as out:
        shutil.copyfileobj(file.file, out)
    try:
        Image.open(dest).verify()
    except Exception:
        os.remove(dest); raise HTTPException(400, "الملف ليس صورة صالحة.")
    base = str(request.base_url).rstrip("/")
    url  = f"{base}/files/uploads/{safe}"
    return {
        "ok": True, "image_url": url,
        "reverse": {
            "google": f"https://www.google.com/searchbyimage?image_url={url}",
            "bing":   f"https://www.bing.com/images/search?q=imgurl:{url}&view=detailv2&iss=sbi",
            "yandex": f"https://yandex.com/images/search?rpt=imageview&url={url}",
            "tineye": f"https://tineye.com/search?url={url}"
        }
    }

@app.get("/files_list")
def files_list():
    items = []
    for root, _, files in os.walk(FILES_DIR):
        for fn in files:
            path = os.path.join(root, fn)
            rel  = os.path.relpath(path, FILES_DIR).replace("\\","/")
            items.append("/files/" + rel)
    items.sort()
    return {"count": len(items), "files": items}

@app.get("/download")
async def download(url: str = Query(..., description="URL للتنزيل")):
    headers = {"User-Agent": "Mozilla/5.0 (BassamBot; +https://render.com)"}
    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url)
    ct = (r.headers.get("content-type") or "application/octet-stream").split(";")[0]
    return Response(content=r.content, media_type=ct)


# =========================
# 7) واجهات الدردشة/البحث
# =========================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if templates and os.path.exists(os.path.join("templates","index.html")):
        return templates.TemplateResponse("index.html", {"request": request, "version": "4.1"})
    return HTMLResponse("<h3>بسّام يعمل. ارفع templates/index.html لاستخدام الواجهة.</h3>")

@app.get("/healthz")
def healthz():
    return {"status":"ok","version":"4.1","docs_indexed":len(BM25_DOCS)}

@app.get("/ask")
def ask(q: str = Query(..., description="سؤالك")):
    log_usage()
    q = (q or "").strip()
    if not q: 
        return {"type":"chat","answer":"أدخل سؤالك."}

    # (A) رياضيات؟
    if any(t in q for t in ["sin","cos","tan","log","exp","^"]) or ("مشتقة" in q) or ("تكامل" in q):
        math = solve_math(q)
        return {"type":"math", "result": math, "answer": "تم الحساب. انظر التفاصيل."}

    # (B) RAG محلي أولًا
    rag = rag_bm25(q, k=3)
    if rag:
        summary = summarize_text(rag[0]["snippet"], 3)
        return {"type":"chat","answer":summary, "sources":[
            {"title": os.path.basename(r["file"]), "link":"", "snippet": r["snippet"]} for r in rag
        ]}

    # (C) إن لم تجد RAG → ويب معزّز (عنيد)
    hits = web_search_strong(q, limit=10)
    if hits:
        bullet = "\n".join(f"- {h.get('title')}: {h.get('summary') or h.get('snippet','')}" for h in hits[:6])
        final  = "ملخص مختصر لأفضل النتائج:\n" + bullet
        return {"type":"chat","answer":final, "sources": hits}

    return {"type":"chat","answer": "لم أجد نتائج حول سؤالك. جرّب صياغة أدق أو حمّل مرجع PDF وسيتم فهرسته."}

@app.get("/search")
def search_endpoint(q: str = Query(...), mode: str = "all", per_site: int = 4, max_total: int = 30):
    q = (q or "").strip()
    if not q:
        return {"type":"chat", "answer":"أدخل عبارة البحث."}
    results = deep_search(q, mode=mode, per_site=per_site, max_total=max_total)
    if results:
        summary = "أفضل النتائج (مختصر):\n" + "\n".join("- " + (r.get("title") or "") for r in results[:8])
        return {"type":"chat", "answer": summary, "sources": results}
    return {"type":"chat", "answer":"لم أجد نتائج واضحة، جرّب وصفًا أدق."}

@app.get("/search/advanced")
def search_advanced(q: str = Query(...), timelimit: str = "", social: bool=False, market: bool=False,
                    gov: bool=False, edu: bool=False, video: bool=False, deep: bool=False):
    mode = "all"
    if social: mode = "social"
    elif market: mode = "markets"
    elif gov or edu: mode = "gov"
    elif video: mode = "video"
    results = deep_search(q, mode=mode, per_site=6 if deep else 4, max_total=40 if deep else 25)
    summary = "ملخص النتائج:\n" + "\n".join("- "+(r.get("title") or "") for r in results[:10]) if results else "لا نتائج."
    return {"count": len(results), "results": results, "answer": summary}

@app.post("/feedback")
def feedback(payload: Dict[str,Any] = Body(...)):
    q = (payload.get("question") or "").strip()
    a = (payload.get("answer") or "").strip()
    tags = payload.get("tags") or []
    if not q or not a: return {"ok":False,"error":"question و answer مطلوبة"}
    with open(LEARN_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"time":int(time.time()),"question":q,"answer":a,"tags":tags}, ensure_ascii=False)+"\n")
    n = build_index()
    return {"ok":True,"indexed_docs":n}

@app.post("/train")
def train(): return {"ok":True, "indexed_docs": build_index()}

@app.get("/stats")
def stats():
    try:
        with open(USAGE_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except: return {"requests":0}


# =========================
# 8) تشغيل محلّي
# =========================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
