# main.py  — Bassam App (Render-ready, free search)
import os, time, traceback
from typing import Optional, List, Dict

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# === الوحدات الداخلية
from core.search import deep_search, people_search     # لازم تكون موجودة
from core.utils import ensure_dirs                     # أضفناها سابقاً في core/utils.py

# مسارات أساسية
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
ensure_dirs(TEMPLATES_DIR, STATIC_DIR, UPLOADS_DIR, CACHE_DIR)

# === FastAPI
app = FastAPI(title="Bassam — Deep Search")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ===== أدوات مساعدة خفيفة =====
def _parse_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "on", "t"}

def _simple_summarize(text: str, max_sentences: int = 5) -> str:
    """
    مُلخِّص بسيط بدون اعتماديات ثقيلة: يلتقط أفضل الجُمل الأطول والأكثر احتواءً على الكلمات الفريدة.
    تكفي للاستخدام المبدئي.
    """
    if not text:
        return ""
    import re
    sents = re.split(r"(?<=[.!؟\?])\s+", text)
    sents = [s.strip() for s in sents if len(s.strip()) > 0]
    if len(sents) <= max_sentences:
        return " ".join(sents[:max_sentences])
    # وزن تقريبي: طول الجملة + عدد الكلمات الفريدة
    def score(s: str) -> float:
        words = re.findall(r"\w+", s.lower())
        return 0.7 * len(s) + 0.3 * len(set(words))
    ranked = sorted(sents, key=score, reverse=True)
    picked = sorted(ranked[:max_sentences], key=lambda x: sents.index(x))
    return " ".join(picked)

def _sources_to_text(sources: List[Dict], limit: int = 12) -> str:
    parts = []
    for s in (sources or [])[:limit]:
        snip = s.get("snippet") or s.get("body") or ""
        if snip:
            parts.append(snip)
    return " ".join(parts)


# ===== صفحات عامة =====
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# ===== API: البحث العام =====
@app.post("/search")
async def search_endpoint(
    request: Request,
    q: Optional[str] = Form(None),
    want_prices: Optional[bool] = Form(False),
):
    t0 = time.time()
    try:
        # في حال أتى الطلب JSON من السكربت
        if not q:
            try:
                body = await request.json()
            except Exception:
                body = {}
            q = (body.get("q") or "").strip()
            want_prices = _parse_bool(body.get("want_prices"))

        q = (q or "").strip()
        if not q:
            return JSONResponse({"ok": False, "error": "query_is_empty"}, status_code=400)

        # البحث المجاني (DuckDuckGo عبر core/search.py)
        sources = deep_search(q, include_prices=_parse_bool(want_prices))
        sources = sources or []
        if not sources:
            print(f"[SEARCH WARN] No sources for: {q}")

        # تلخيص سريع
        text_blob = _sources_to_text(sources, limit=12)
        answer = _simple_summarize(text_blob, max_sentences=5) or "تم العثور على نتائج — راجع الروابط."

        payload = {
            "ok": True,
            "latency_ms": int((time.time() - t0) * 1000),
            "answer": answer,
            "sources": [{"title": s.get("title") or s.get("url"), "url": s.get("url")} for s in sources[:12]],
        }
        return JSONResponse(payload)

    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"ok": False, "error": f"search_failed:{type(e).__name__}"}, status_code=500)


# ===== API: البحث عن أشخاص/يوزرات =====
@app.post("/people")
async def people_endpoint(
    request: Request,
    name: Optional[str] = Form(None),
):
    try:
        if not name:
            try:
                body = await request.json()
            except Exception:
                body = {}
            name = (body.get("name") or "").strip()

        name = (name or "").strip()
        if not name:
            return JSONResponse({"ok": False, "error": "name_is_empty"}, status_code=400)

        results = people_search(name) or []
        return {"ok": True, "sources": [{"title": r.get("title") or r.get("url"), "url": r.get("url")} for r in results[:20]]}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"ok": False, "error": f"people_failed:{type(e).__name__}"}, status_code=500)


# ===== API: رفع PDF (اختياري) =====
@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        fname = os.path.basename(file.filename)
        dest = os.path.join(UPLOADS_DIR, fname)
        with open(dest, "wb") as f:
            f.write(await file.read())

        # محاولة استخراج نص بدون إسقاط السيرفر لو المكتبات ناقصة
        text = ""
        try:
            # أولوية: pdfminer.six
            from pdfminer.high_level import extract_text as _extract
            text = _extract(dest) or ""
        except Exception:
            pass

        msg = "تم الرفع."
        if text:
            msg += " وتم استخراج النص."

        return {"ok": True, "message": msg, "filename": fname, "chars": len(text)}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"ok": False, "error": f"pdf_failed:{type(e).__name__}"}, status_code=500)


# ===== API: رفع صورة + OCR (اختياري) =====
@app.post("/upload_image")
async def upload_image(file: UploadFile = File(...)):
    try:
        fname = os.path.basename(file.filename)
        dest = os.path.join(UPLOADS_DIR, fname)
        with open(dest, "wb") as f:
            f.write(await file.read())

        ocr_text = ""
        # نحاول بـ pillow + pytesseract إذا متوفرة
        try:
            from PIL import Image
            import pytesseract
            img = Image.open(dest).convert("RGB")
            # eng+ara لو تتوفر حزم اللغة في بيئة النظام
            try:
                ocr_text = pytesseract.image_to_string(img, lang="ara+eng")
            except Exception:
                ocr_text = pytesseract.image_to_string(img)
            ocr_text = (ocr_text or "").strip()
        except Exception:
            pass

        return {"ok": True, "message": "تم رفع الصورة.", "filename": fname, "text": ocr_text}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"ok": False, "error": f"image_failed:{type(e).__name__}"}, status_code=500)


# ===== مسار تشخيص سريع =====
@app.get("/debug_search")
def debug_search(q: str, want_prices: bool = False):
    try:
        src = deep_search(q, include_prices=_parse_bool(want_prices)) or []
        return {"ok": True, "n": len(src), "sources": src[:5]}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# ===== تشغيل محلياً (للـ dev) =====
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
