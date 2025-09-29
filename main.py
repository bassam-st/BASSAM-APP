# main.py — Bassam v3.9 (Human-like Chat • RAG • Deep Web/Platforms • Math • PDF/Image • Spelling/Intents)
from fastapi import FastAPI, Request, Query, Body, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

import os, json, time, re, shutil
from typing import List, Dict, Any

# بحث وRAG وأدوات
from duckduckgo_search import DDGS
from rank_bm25 import BM25Okapi

# تلخيص
try:
    from sumy.parsers.text import PlaintextParser
except Exception:
    from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

# رياضيات
from sympy import symbols, sympify, diff, integrate, simplify

# PDF/صور وتصحيح
from pypdf import PdfReader
from PIL import Image
from rapidfuzz import process, fuzz

# ------------------ ثوابت ومسارات ------------------
DATA_DIR     = "data"
BRAIN_DIR    = os.path.join(DATA_DIR, "brain")
NOTES_DIR    = os.path.join(DATA_DIR, "notes")
FILES_DIR    = "files"
UPLOADS_DIR  = os.path.join(FILES_DIR, "uploads")
LEARN_PATH   = os.path.join(NOTES_DIR, "learned.jsonl")
USAGE_PATH   = os.path.join(DATA_DIR,  "usage_stats.json")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BRAIN_DIR, exist_ok=True)
os.makedirs(NOTES_DIR, exist_ok=True)
os.makedirs(FILES_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

app = FastAPI(title="Bassam الذكي 🤖", version="3.9")
app.mount("/files", StaticFiles(directory=FILES_DIR), name="files")

# قوالب الواجهة (اختياري)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
except Exception:
    templates = None

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ------------------ تحميل دماغ بسّام ------------------
def _load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

INTENTS   = _load_json(os.path.join(BRAIN_DIR, "intents.json"),   {})
SYN_RULES = _load_json(os.path.join(BRAIN_DIR, "synonyms.json"),  {})
PLATFORMS = _load_json(os.path.join(BRAIN_DIR, "platforms.json"), {})

# ------------------ أدوات نصية ------------------
AR_DIGITS_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def normalize_ar(s: str) -> str:
    s = (s or "").strip().lower()
    drop = SYN_RULES.get("drop", "")
    keep = SYN_RULES.get("keep", "")
    norm_map = SYN_RULES.get("normalize", {})

    if drop:
        s = re.sub(drop, "", s)
    for k, v in norm_map.items():
        s = s.replace(k, v)
    if SYN_RULES.get("digits_ar_to_en", True):
        s = s.translate(AR_DIGITS_MAP)
    if keep:
        s = "".join(ch if re.match(keep, ch) else " " for ch in s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def summarize_text(text: str, max_sentences: int = 3) -> str:
    try:
        parser = PlaintextParser.from_string(text or "", Tokenizer("arabic"))
        s = TextRankSummarizer()(parser.document, max_sentences)
        return " ".join(map(str, s)) if s else (text or "")[:400]
    except Exception:
        return (text or "")[:400]

def web_search(query: str, limit=6):
    try:
        with DDGS() as ddgs:
            res = ddgs.text(query, region="xa-ar", safesearch="off", max_results=limit)
            out = []
            for r in res:
                out.append({
                    "title": r.get("title",""),
                    "link":  r.get("href",""),
                    "snippet": r.get("body","")
                })
            return out
    except Exception:
        return []

def answer_bubble(text: str, sources: List[Dict[str,Any]] = None) -> Dict[str, Any]:
    resp = {"type":"chat","answer": text.strip()}
    if sources:
        enriched = []
        for s in sources:
            s = dict(s)
            s["summary"] = summarize_text(s.get("snippet",""), 2)
            enriched.append(s)
        resp["sources"] = enriched
    return resp

# ------------------ RAG ------------------
def _read_md_txt_files():
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
    try:
        with open(LEARN_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                obj = json.loads(line)
                docs.append({"file":"learned",
                             "text": f"س: {obj.get('question','')}\nج: {obj.get('answer','')}\nوسوم:{','.join(obj.get('tags',[]))}"})
    except:
        pass
    return docs

def _tokenize_ar(s: str) -> List[str]:
    return re.findall(r"[\w\u0600-\u06FF]+", (s or "").lower())

BM25_INDEX = None
BM25_CORPUS = []
BM25_DOCS   = []
VOCAB       = set()

def build_index():
    """بناء فهرس BM25 + مفردات التصحيح."""
    global BM25_INDEX, BM25_CORPUS, BM25_DOCS, VOCAB
    BM25_DOCS = _read_md_txt_files()
    BM25_CORPUS = [_tokenize_ar(d["text"]) for d in BM25_DOCS]
    BM25_INDEX = BM25Okapi(BM25_CORPUS) if BM25_CORPUS else None

    vocab = set()
    for d in BM25_DOCS:
        for t in _tokenize_ar(d["text"]):
            vocab.add(normalize_ar(t))
    for _, spec in INTENTS.items():
        for w in spec.get("triggers", []): vocab.add(normalize_ar(w))
        for w in spec.get("extract",  []): vocab.add(normalize_ar(w))
    VOCAB = {w for w in vocab if w}
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

# ------------------ تصحيح إملائي بسيط ------------------
def correct_token(tok: str) -> str:
    tok = normalize_ar(tok)
    if (not tok) or (tok in VOCAB): return tok
    cand = process.extractOne(tok, VOCAB, scorer=fuzz.WRatio)
    if cand and cand[1] >= 88: return cand[0]
    return tok

def correct_query_ar(q: str) -> str:
    return " ".join(correct_token(t) for t in q.split())

def expand_query_ar(q: str) -> List[str]:
    n = normalize_ar(q)
    vars_ = {n}
    for _, spec in INTENTS.items():
        for base in spec.get("triggers", []):
            b = normalize_ar(base)
            if b and b in n:
                for alt in spec.get("triggers", []):
                    a = normalize_ar(alt)
                    if a and a != b: vars_.add(n.replace(b, a))
    return list(vars_)

# ------------------ رياضيات ------------------
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

# ------------------ منصات/نطاقات مخصّصة ------------------
SOCIAL_DOMAINS  = PLATFORMS.get("social_domains", [])
MARKET_DOMAINS  = PLATFORMS.get("market_domains", [])
GOV_DOMAINS     = PLATFORMS.get("government_domains", [])

def aggregate_search(q: str, domains: List[str], per=5) -> List[Dict[str,Any]]:
    out, seen = [], set()
    try:
        with DDGS() as ddgs:
            for dom in domains:
                query = f"{q} {dom}"
                for r in ddgs.text(query, region="xa-ar", safesearch="off", max_results=per):
                    link = r.get("href","")
                    if not link or link in seen: continue
                    seen.add(link)
                    out.append({
                        "title": r.get("title",""),
                        "link":  link,
                        "snippet": r.get("body",""),
                        "domain": dom.replace("site:","")
                    })
    except Exception:
        pass
    for r in out:
        r["summary"] = summarize_text(r.get("snippet",""), 2)
    return out

# ------------------ PDF/صور ------------------
def extract_pdf_text(path: str) -> str:
    try:
        reader = PdfReader(path)
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        return ""

def ensure_safe_filename(name: str) -> str:
    name = re.sub(r"[^\w\-.]+", "_", name or "")
    return name[:120] or f"file_{int(time.time())}"

# ------------------ خدمات مساعدة ------------------
def log_usage():
    try:
        if not os.path.exists(USAGE_PATH):
            with open(USAGE_PATH, "w", encoding="utf-8") as f:
                json.dump({"requests":0,"last_time":int(time.time())}, f)
        with open(USAGE_PATH, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["requests"] = int(data.get("requests",0)) + 1
            data["last_time"] = int(time.time())
            f.seek(0); json.dump(data, f); f.truncate()
    except Exception:
        pass

def guess_intent(q: str) -> str:
    n = normalize_ar(q)
    for name, spec in INTENTS.items():
        for trig in spec.get("triggers", []):
            if normalize_ar(trig) in n:
                return name
    for name, spec in INTENTS.items():
        if spec.get("fallback"): return name
    return "general"

# ------------------ المسارات ------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if templates:
        return templates.TemplateResponse("index.html", {"request": request, "version": "v3.9"})
    return HTMLResponse("<h3>ارفع templates/index.html</h3>")

@app.get("/healthz")
def healthz():
    return {"status":"ok","version":"3.9","docs_indexed":len(BM25_DOCS)}

@app.get("/ask")
def ask(q: str = Query(..., description="سؤالك")):
    log_usage()
    if not q: return {"error":"أدخل سؤالك"}

    # 1) رياضيات؟
    if any(tok in q for tok in ["sin","cos","tan","log","exp","^"]) or ("مشتقة" in q) or ("تكامل" in q):
        return {"type":"math","result":solve_math(q)}

    # 2) تصحيح + توسيع
    q_norm = normalize_ar(q)
    q_corr = correct_query_ar(q_norm)
    expansions = [q_corr] + expand_query_ar(q_corr)

    # 3) نية
    intent = guess_intent(q_corr)

    # 4) حسب النية
    if intent == "capital":
        hits = web_search(f"capital of {q_corr}", limit=6)
        if hits:  return answer_bubble("نتائج عن العاصمة المطلوبة 👇", hits)
        rag = rag_bm25(q_corr, k=3)
        if rag:   return answer_bubble(summarize_text(rag[0]["snippet"],3))
        return answer_bubble("اكتب: ما عاصمة [اسم الدولة]؟")

    if intent == "product":
        results = aggregate_search(q_corr, MARKET_DOMAINS, per=4)
        if results: return answer_bubble("نتائج متاجر ومنصّات بيع 👇", results[:12])
        hits = []
        for ex in expansions: hits += web_search(ex, limit=4)
        if hits: return answer_bubble("أفضل ما وجدت في الويب 👇", hits[:10])
        return answer_bubble("لم أجد نتائج واضحة، جرّب موديل/اسم أدق.")

    if intent == "social":
        results = aggregate_search(f'"{q_corr}"', SOCIAL_DOMAINS, per=4)
        if results: return answer_bubble("حسابات/نتائج اجتماعية محتملة 👇", results[:15])
        return answer_bubble("أضف مدينة/بلد أو وصفًا مميزًا للاسم.")

    if intent == "howto":
        hits = []
        for ex in expansions: hits += web_search(ex, limit=4)
        if hits:
            steps = []
            for h in hits[:6]:
                txt = h.get("snippet","")
                for part in re.split(r"[.\n•\-–]", txt):
                    p = part.strip()
                    if 6 <= len(p) <= 160 and not p.lower().startswith("http"):
                        steps.append("— " + p)
                if len(steps) >= 10: break
            if not steps:
                steps = ["— اطلع الروابط التالية وطبّق ما فيها خطوة بخطوة."]
            ans = "خلّني أمشيك **خطوة خطوة**:\n" + "\n".join(steps[:10])
            return answer_bubble(ans, hits[:5])
        return answer_bubble("ما وجدت شرحًا مناسبًا الآن.")

    # عام: RAG → ويب
    rag = rag_bm25(q_corr, k=3)
    if rag:
        return answer_bubble(summarize_text(rag[0]["snippet"],3))
    hits = []
    for ex in expansions: hits += web_search(ex, limit=3)
    if hits:
        return answer_bubble("جبت لك أفضل ما وجدت 👇", hits[:10])
    return answer_bubble("لم أجد نتائج حول سؤالك.")

# --- Upload PDF ---
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
    return {"ok":True,"file_url":f"/files/uploads/{safe}","indexed_docs":n}

# --- Upload Image + Reverse Search ---
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
        os.remove(dest); raise HTTPException(400,"الملف ليس صورة صالحة.")
    base = str(request.base_url).rstrip("/")
    url = f"{base}/files/uploads/{safe}"
    return {
        "ok": True, "image_url": url,
        "reverse": {
            "google": f"https://www.google.com/searchbyimage?image_url={url}",
            "bing":   f"https://www.bing.com/images/search?q=imgurl:{url}&view=detailv2&iss=sbi",
            "yandex": f"https://yandex.com/images/search?rpt=imageview&url={url}",
            "tineye": f"https://tineye.com/search?url={url}"
        }
    }

# --- فهرس/إعادة تسمية ملفات ---
@app.get("/files_list")
def files_list(query: str = "", kind: str = "all", sort: str = "date"):
    items = []
    for root, _, files in os.walk(FILES_DIR):
        for fn in files:
            path = os.path.join(root, fn)
            rel_path  = os.path.relpath(path, FILES_DIR)
            rel_web   = rel_path.replace("\\","/")
            ext  = os.path.splitext(fn)[1].lower()
            if kind=="pdf" and ext!=".pdf": continue
            if kind=="image" and ext not in [".jpg",".jpeg",".png",".webp",".bmp"]: continue
            if query and query.lower() not in fn.lower(): continue
            st = os.stat(path)
            items.append({"path":"/files/"+rel_web,"name":fn,"size":st.st_size,"mtime":int(st.st_mtime)})
    if sort=="name": items.sort(key=lambda x:x["name"].lower())
    elif sort=="size": items.sort(key=lambda x:x["size"], reverse=True)
    else: items.sort(key=lambda x:x["mtime"], reverse=True)
    return {"count":len(items), "files":items}

@app.post("/files_rename")
def files_rename(old_path: str = Body(...), new_name: str = Body(...)):
    if not old_path.startswith("/files/"): raise HTTPException(400,"مسار غير صالح.")
    old_fs = os.path.join(FILES_DIR, old_path.replace("/files/","",1).lstrip("/"))
    if not os.path.exists(old_fs): raise HTTPException(404,"الملف غير موجود.")
    safe = ensure_safe_filename(new_name)
    new_fs = os.path.join(os.path.dirname(old_fs), safe)
    if os.path.exists(new_fs): raise HTTPException(400,"اسم موجود مسبقًا.")
    os.rename(old_fs, new_fs)
    rel = os.path.relpath(new_fs, FILES_DIR).replace("\\","/")
    return {"ok":True,"new_path":"/files/"+rel}

# --- تعلّم ذاتي/فهرسة/إحصاءات ---
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

# --- تشغيل محلي ---
if __name__ == "__main__":
    import uvicorn, os
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
