# main.py — Bassam الذكي v3.6 (Chat + RAG + Web + Math + PDF/Image Upload)
from fastapi import FastAPI, Request, Query, Body, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

import os, json, time, re, shutil
from typing import List, Dict, Any

# === نصي وتلخيص ===
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from readability import Document

# استيراد آمن لـ sumy (PlaintextParser قد تظهر بصيغتين)
try:
    from sumy.parsers.text import PlaintextParser
except Exception:
    from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

# === رياضيات ===
from sympy import symbols, sympify, diff, integrate, simplify, sin, cos, tan, log, exp

# === فهرسة RAG محلية (BM25) ===
from rank_bm25 import BM25Okapi

# === PDF & Images ===
from pypdf import PdfReader
from PIL import Image  # فقط للتأكد من قبول الصور

# -------------------------
# مسارات البيانات
# -------------------------
DATA_DIR   = "data"
NOTES_DIR  = os.path.join(DATA_DIR, "notes")
FILES_DIR  = "files"                # ملفات مرفوعة (PDF/صور) تُخدم عبر /files/...
UPLOADS_DIR = os.path.join(FILES_DIR, "uploads")

LEARN_PATH = os.path.join(NOTES_DIR, "learned.jsonl")
USAGE_PATH = os.path.join(DATA_DIR,  "usage_stats.json")

app = FastAPI(title="Bassam الذكي 🤖", version="3.6")

# ربط مجلدات استاتيكية
os.makedirs(FILES_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
app.mount("/files", StaticFiles(directory=FILES_DIR), name="files")

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

# -------------------------
# تهيئة البيانات
# -------------------------
def _ensure_dirs():
    os.makedirs(DATA_DIR,   exist_ok=True)
    os.makedirs(NOTES_DIR,  exist_ok=True)
    if not os.path.exists(LEARN_PATH):
        open(LEARN_PATH, "a", encoding="utf-8").close()
    if not os.path.exists(USAGE_PATH):
        with open(USAGE_PATH, "w", encoding="utf-8") as f:
            json.dump({"requests": 0, "last_time": int(time.time())}, f)

_ensure_dirs()

def _read_md_txt_files() -> List[Dict[str, str]]:
    docs = []
    # .md/.txt من data/
    for root, _, files in os.walk(DATA_DIR):
        for fn in files:
            if fn.endswith(".md") or fn.endswith(".txt"):
                path = os.path.join(root, fn)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        docs.append({"file": path, "text": f.read()})
                except:
                    pass
    # بنك التعلّم الذاتي
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
    # تقطيع بسيط يدعم العربية والإنجليزية
    return re.findall(r"[\w\u0600-\u06FF]+", s.lower())

BM25_INDEX = None
BM25_CORPUS = []
BM25_DOCS: List[Dict[str, str]] = []

def build_index():
    """أعد بناء فهرس RAG من ملفات data/ ومن بنك التعلم."""
    global BM25_INDEX, BM25_CORPUS, BM25_DOCS
    BM25_DOCS = _read_md_txt_files()
    BM25_CORPUS = [_tokenize_ar(d["text"]) for d in BM25_DOCS]
    BM25_INDEX = BM25Okapi(BM25_CORPUS) if BM25_CORPUS else None
    return len(BM25_DOCS)

build_index()

# -------------------------
# وظائف الذكاء
# -------------------------
def summarize_text(text: str, max_sentences: int = 3) -> str:
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("arabic"))
        summarizer = TextRankSummarizer()
        sents = summarizer(parser.document, max_sentences)
        return " ".join(str(s) for s in sents) if sents else text[:400]
    except Exception:
        return text[:400]

def web_search(query: str):
    try:
        with DDGS() as ddgs:
            res = ddgs.text(query, region="xa-ar", max_results=5)
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
        snippet = doc["text"][:800]
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

def log_usage():
    try:
        with open(USAGE_PATH, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["requests"] = int(data.get("requests", 0)) + 1
            data["last_time"] = int(time.time())
            f.seek(0); json.dump(data, f); f.truncate()
    except Exception:
        pass

def save_feedback(question: str, answer: str, tags: List[str]):
    record = {
        "time": int(time.time()),
        "question": question.strip(),
        "answer": answer.strip(),
        "tags": tags or []
    }
    with open(LEARN_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

# -------------------------
# أدوات PDF/صورة
# -------------------------
def extract_pdf_text(pdf_path: str) -> str:
    """استخراج نص من PDF (أفضل ما يمكن)."""
    try:
        reader = PdfReader(pdf_path)
        chunks = []
        for page in reader.pages:
            chunks.append(page.extract_text() or "")
        return "\n".join(chunks)
    except Exception as e:
        return ""

def ensure_safe_filename(name: str) -> str:
    # اسم ملف بسيط وآمن
    name = re.sub(r"[^\w\-.]+", "_", name)
    return name[:120] or f"file_{int(time.time())}"

# -------------------------
# واجهات التطبيق
# -------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if templates:
        return templates.TemplateResponse("index.html", {"request": request, "version": "v3.6"})
    # نسخة احتياطية بسيطة إن لم توجد القوالب
    html = """<!doctype html><meta charset='utf-8'><title>Bassam v3.6</title>
    <div style='font-family:system-ui;padding:20px;color:#e7ecff;background:#0b1020'>
      <h2>🤖 بسّام الذكي v3.6</h2>
      <p>الواجهة غير مثبتة. ارفع <code>templates/index.html</code>.</p>
    </div>"""
    return HTMLResponse(html)

@app.get("/healthz")
def healthz():
    return {"status": "ok", "version": "3.6", "docs_indexed": len(BM25_DOCS)}

@app.get("/ask")
def ask(q: str = Query(..., description="سؤالك")):
    log_usage()
    q = (q or "").strip()
    if not q:
        return {"error": "أدخل سؤالك"}

    # تلميح بسيط للأخطاء الإملائية/الاختصارات: (مكان سريع للتوسعة لاحقًا)
    # هنا نكتفي بالتعامل المباشر.

    # رياضيات؟
    if any(tok in q for tok in ["sin", "cos", "tan", "log", "exp", "^"]) or ("مشتقة" in q) or ("تكامل" in q):
        return {"type": "math", "result": solve_math(q)}

    # RAG محلي
    rag = rag_bm25(q, k=3)
    if rag:
        s = summarize_text(rag[0]["snippet"], 3)
        return {"type": "rag", "hits": rag, "summary": s}

    # بحث ويب
    web = web_search(q)
    if web:
        for item in web:
            item["summary"] = summarize_text(item["snippet"], 2)
        return {"type": "web", "results": web}

    return {"msg": "لم أجد نتائج حول سؤالك."}

# === التعلم الذاتي عبر تغذية راجعة ===
@app.post("/feedback")
def feedback(payload: Dict[str, Any] = Body(...)):
    q = (payload.get("question") or "").strip()
    a = (payload.get("answer") or "").strip()
    tags = payload.get("tags") or []
    if not q or not a:
        return {"ok": False, "error": "question و answer مطلوبة"}
    save_feedback(q, a, tags)
    n = build_index()
    return {"ok": True, "indexed_docs": n}

# إعادة بناء الفهرس يدويًا
@app.post("/train")
def train():
    n = build_index()
    return {"ok": True, "indexed_docs": n}

# إحصاءات بسيطة
@app.get("/stats")
def stats():
    try:
        with open(USAGE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"requests": 0}

# -------------------------
# رفع PDF
# -------------------------
@app.post("/upload/pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "ارفع ملف PDF فقط.")
    safe = ensure_safe_filename(file.filename)
    dest_path = os.path.join(UPLOADS_DIR, safe)
    # احفظ الملف
    with open(dest_path, "wb") as out:
        shutil.copyfileobj(file.file, out)
    # استخرج النص واحفظه في data/ كي يدخل ضمن RAG
    text = extract_pdf_text(dest_path)
    if text.strip():
        txt_name = safe.rsplit(".", 1)[0] + ".txt"
        txt_path = os.path.join(DATA_DIR, txt_name)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        n = build_index()
    else:
        n = len(BM25_DOCS)

    # رابط الملف العام
    file_url = f"/files/uploads/{safe}"
    return {"ok": True, "file_url": file_url, "indexed_docs": n}

# -------------------------
# رفع صورة + روابط بحث عكسي
# -------------------------
@app.post("/upload/image")
async def upload_image(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
        raise HTTPException(400, "ارفع صورة بصيغة jpg/png/webp/bmp.")
    safe = ensure_safe_filename(file.filename or f"img_{int(time.time())}{ext}")
    dest_path = os.path.join(UPLOADS_DIR, safe)
    with open(dest_path, "wb") as out:
        shutil.copyfileobj(file.file, out)
    # تحقق سريع أنها صورة بالفعل
    try:
        Image.open(dest_path).verify()
    except Exception:
        os.remove(dest_path)
        raise HTTPException(400, "الملف ليس صورة صالحة.")

    public_url = f"/files/uploads/{safe}"
    # روابط بحث عكسي شهيرة (تعتمد على URL عام للصورة)
    # بعض المنصّات قد تعيد توجيه/تحجب تلقائيًا، لكن الروابط التالية هي الأكثر شيوعًا
    google = f"https://www.google.com/searchbyimage?image_url={{BASE}}".replace("{BASE}", public_url)
    bing   = f"https://www.bing.com/images/search?q=imgurl:{{BASE}}&view=detailv2&iss=sbi".replace("{BASE}", public_url)
    yandex = f"https://yandex.com/images/search?rpt=imageview&url={{BASE}}".replace("{BASE}", public_url)
    tineye = f"https://tineye.com/search?url={{BASE}}".replace("{BASE}", public_url)

    return {"ok": True, "image_url": public_url,
            "reverse": {"google": google, "bing": bing, "yandex": yandex, "tineye": tineye}}

# فهرس بسيط للملفات
@app.get("/files_list")
def files_list():
    items = []
    for root, _, files in os.walk(FILES_DIR):
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), FILES_DIR).replace("\\", "/")
            items.append("/files/" + rel)
    items.sort()
    return {"count": len(items), "files": items}

# نقطة تشغيل محلية
if __name__ == "__main__":
    import uvicorn, os
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
