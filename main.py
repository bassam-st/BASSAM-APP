# main.py — Bassam APP (FastAPI) ready for Render
import os, time, tempfile, pathlib
from typing import Optional, List, Dict

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.templating import Jinja2Templates

# لبّ التطبيق (التي أرسلناها سابقًا)
from core.search import deep_search
from core.summarizer import smart_summarize
from core.utils import extract_pdf_text, extract_image_text

# ------------- إعدادات أساسية -------------
APP_NAME = "Bassam APP"
BASE_DIR = pathlib.Path(__file__).parent.resolve()
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title=APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Static & templates
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ------------- أدوات صغيرة -------------
def _take_json(req: Request) -> Dict:
    """يحاول قراءة JSON وإذا فشل يرجّع {}"""
    try:
        return {} if req is None else (req.json() if isinstance(req, dict) else {})
    except Exception:
        return {}

async def _get_json_body(request: Request) -> Dict:
    try:
        return await request.json()
    except Exception:
        return {}

def _summarize_from_sources(sources: List[Dict], fallback: str = "") -> str:
    if not sources:
        return fallback or "لم أعثر على نتائج."
    # اجمع مقتطفات للملخّص
    big_text = " ".join((s.get("snippet", "") or "") for s in sources)[:8000]
    ans = smart_summarize(big_text, max_sentences=5).strip()
    if not ans:
        ans = fallback or "تم العثور على مصادر، لكن لم أستطع إنشاء ملخّص."
    return ans

# ------------- مسارات -------------
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # يحمّل templates/index.html الموجودة لديك
    return templates.TemplateResponse("index.html", {"request": request, "app_name": APP_NAME})

@app.post("/search")
async def search_endpoint(
    request: Request,
    q: Optional[str] = Form(None),
    want_prices: Optional[bool] = Form(False),
):
    """
    يقبل JSON أو Form:
    JSON: {"q": "...", "want_prices": true}
    Form:  q=...&want_prices=false
    """
    t0 = time.time()
    try:
        # لو لم يصل q من الـ Form، جرّب JSON
        if not q:
            body = await _get_json_body(request)
            q = (body.get("q") or "").strip()
            want_prices = bool(body.get("want_prices") or False)

        q = (q or "").strip()
        if not q:
            return JSONResponse({"error": "query_is_empty"}, status_code=400)

        # بحث متعدد المحركات (حسب المفاتيح المتوفرة) + DDG دائمًا
        sources = deep_search(q, include_prices=bool(want_prices))
        # إنشاء إجابة مختصرة
        answer = _summarize_from_sources(sources, fallback="تم العثور على نتائج. راجع الروابط بالأسفل.")
        # رتّب المصادر البسيطة للواجهة
        src_out = [{"title": s.get("title") or s.get("url"), "url": s.get("url")} for s in sources][:12]

        return {
            "ok": True,
            "latency_ms": int((time.time()-t0)*1000),
            "answer": answer,
            "sources": src_out
        }
    except Exception as e:
        print(f"[SEARCH ERROR] {e}")
        return JSONResponse({"ok": False, "error": "search_failed"}, status_code=500)

@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """
    يقرأ PDF ويُرجع أول 1000 حرف + يمكنك لاحقًا فهرسته داخليًا إذا رغبت.
    """
    try:
        suffix = pathlib.Path(file.filename).suffix or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            data = await file.read()
            tmp.write(data)
            tmp_path = tmp.name

        text = extract_pdf_text(tmp_path) or ""
        os.unlink(tmp_path)
        return {
            "ok": True,
            "chars": len(text),
            "preview": text[:1000]
        }
    except Exception as e:
        print(f"[PDF UPLOAD ERROR] {e}")
        return JSONResponse({"ok": False, "error": "pdf_extract_failed"}, status_code=500)

@app.post("/upload_image")
async def upload_image(file: UploadFile = File(...)):
    """
    يقرأ صورة ويجري OCR بسيط، ثم يعيد النص المستخرج.
    (يمكنك لاحقًا تمرير النص إلى deep_search لإجراء بحث بالصورة).
    """
    try:
        suffix = pathlib.Path(file.filename).suffix or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            data = await file.read()
            tmp.write(data)
            tmp_path = tmp.name

        text = extract_image_text(tmp_path) or ""
        os.unlink(tmp_path)

        # خيار: ابحث بالنص المستخرج
        sources = deep_search(text) if text else []
        answer = _summarize_from_sources(sources, fallback=text or "لم أجد نصًا واضحًا في الصورة.")
        src_out = [{"title": s.get("title") or s.get("url"), "url": s.get("url")} for s in sources][:10]

        return {
            "ok": True,
            "ocr_text": text,
            "answer": answer,
            "sources": src_out
        }
    except Exception as e:
        print(f"[IMG UPLOAD ERROR] {e}")
        return JSONResponse({"ok": False, "error": "image_process_failed"}, status_code=500)
