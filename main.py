# main.py — Bassam App (بحث مجاني + واجهة ويب + PWA)
import os, time, traceback, re
from typing import Optional, List, Dict

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.search import deep_search, people_search
from core.utils import ensure_dirs

# مسارات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
ensure_dirs(TEMPLATES_DIR, STATIC_DIR, UPLOADS_DIR, CACHE_DIR)

app = FastAPI(title="Bassam — Deep Search (Free)")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# -------------------------
# أدوات مساعدة محلية
# -------------------------
def _parse_bool(v) -> bool:
    if isinstance(v, bool): return v
    if v is None: return False
    return str(v).strip().lower() in {"1","true","yes","y","on","t"}

def _simple_summarize(text: str, max_sentences: int = 5) -> str:
    import re
    if not text: return ""
    sents = [s.strip() for s in re.split(r"(?<=[.!؟\?])\s+", text) if s.strip()]
    if len(sents) <= max_sentences: return " ".join(sents)
    def score(s: str) -> float:
        words = re.findall(r"\w+", s.lower())
        return 0.7*len(s) + 0.3*len(set(words))
    ranked = sorted(sents, key=score, reverse=True)[:max_sentences]
    ranked.sort(key=lambda s: sents.index(s))
    return " ".join(ranked)

def _sources_to_text(sources: List[Dict], limit: int = 12) -> str:
    return " ".join([(s.get("snippet") or "") for s in (sources or [])][:limit])

# -------------------------
# تعريف ثابت: من هو بسام الشتيمي؟
# -------------------------
_BASSAM_BIO = (
    "بسام الشتيمي حفظه الله هو مصمم تطبيق بسام الذكي، "
    "وهو شخص ناجح في عمله، ودود ولطيف، "
    "يتمتع بذكاء وروح التعلم وحب القراءة، "
    "وينتمي إلى قبيلة المنصوري من قبائل اليمن."
)

# كلمات مفتاحية متنوعة للتعرّف على النية حتى مع اختلاف الصياغة/الإملاء
_BASSAM_PATTERNS = [
    r"\bبسام\s*الشتيمي\b",
    r"\bمن\s*هو\s*بسام\s*الشتيمي\b",
    r"\bمصمم\s*هذا\s*التطبيق\b",
    r"\bمن\s*صمّم\s*التطبيق\b",
    r"\bمؤسس\s*بسام\b",
    r"\bصاحب\s*التطبيق\b",
    r"\bمن\s*هو\s*بسام\b",
]

def _normalize_ar(s: str) -> str:
    if not s: return ""
    s = s.strip()
    # تبسيط بعض الاختلافات الإملائية
    s = s.replace("أ","ا").replace("إ","ا").replace("آ","ا").replace("ى","ي").replace("ة","ه")
    # مسافات إضافية إلى مسافة واحدة
    s = re.sub(r"\s+", " ", s)
    return s

def _maybe_bassam_answer(text: str) -> Optional[str]:
    q = _normalize_ar(text or "").lower()
    if not q: return None
    for pat in _BASSAM_PATTERNS:
        if re.search(pat, q):
            return _BASSAM_BIO
    return None

# -------------------------
# المسارات
# -------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/healthz")
def healthz():
    return {"status":"ok"}

# مسار تعريفي مباشر (اختياري لواجهة /about)
@app.get("/about_bassam")
def about_bassam():
    return {"ok": True, "answer": _BASSAM_BIO}

@app.post("/search")
async def search_api(request: Request, q: Optional[str] = Form(None), want_prices: Optional[bool] = Form(False)):
    t0 = time.time()
    try:
        if not q:
            try:
                body = await request.json()
            except Exception:
                body = {}
            q = (body.get("q") or "").strip()
            want_prices = _parse_bool(body.get("want_prices"))

        if not q:
            return JSONResponse({"ok":False,"error":"query_is_empty"}, 400)

        # 👇 أولاً: تحقق إن كان السؤال عن "من هو بسام الشتيمي"
        bassam_answer = _maybe_bassam_answer(q)
        if bassam_answer:
            return {
                "ok": True,
                "latency_ms": int((time.time()-t0)*1000),
                "answer": bassam_answer,
                "sources": []  # إجابة تعريفية ثابتة
            }

        # المعالجة الاعتيادية للبحث
        hits = deep_search(q, include_prices=_parse_bool(want_prices))
        text_blob = _sources_to_text(hits, limit=12)
        answer = _simple_summarize(text_blob, 5) or "تم العثور على نتائج — راجع الروابط."
        return {
            "ok": True,
            "latency_ms": int((time.time()-t0)*1000),
            "answer": answer,
            "sources": [{"title":h.get("title") or h.get("url"), "url":h.get("url")} for h in hits[:12]]
        }
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"ok":False,"error":f"search_failed:{type(e).__name__}"}, 500)

@app.post("/people")
async def people_api(request: Request, name: Optional[str] = Form(None)):
    try:
        if not name:
            try:
                body = await request.json()
            except Exception:
                body = {}
            name = (body.get("name") or "").strip()

        if not name:
            return JSONResponse({"ok":False,"error":"name_is_empty"}, 400)

        # 👇 أيضاً نعطي التعريف لو كان اسم الشخص هو بسام الشتيمي
        bassam_answer = _maybe_bassam_answer(name)
        if bassam_answer:
            return {"ok": True, "sources": [], "answer": bassam_answer}

        hits = people_search(name) or []
        return {"ok":True, "sources":[{"title":h.get("title") or h.get("url"), "url":h.get("url")} for h in hits[:20]]}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"ok":False,"error":f"people_failed:{type(e).__name__}"}, 500)

@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        fname = os.path.basename(file.filename)
        dest = os.path.join(UPLOADS_DIR, fname)
        with open(dest,"wb") as f:
            f.write(await file.read())
        return {"ok":True,"message":"تم الرفع.","filename":fname}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"ok":False,"error":f"pdf_failed:{type(e).__name__}"}, 500)

@app.post("/upload_image")
async def upload_image(file: UploadFile = File(...)):
    try:
        fname = os.path.basename(file.filename)
        dest = os.path.join(UPLOADS_DIR, fname)
        with open(dest,"wb") as f:
            f.write(await file.read())
        return {"ok":True,"message":"تم رفع الصورة.","filename":fname}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"ok":False,"error":f"img_failed:{type(e).__name__}"}, 500)
