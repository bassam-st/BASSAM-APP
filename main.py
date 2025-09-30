# main.py — Bassam Deep Search API
import os, re, json, time, html
from typing import Optional, List, Dict
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.search import deep_search
from core.summarizer import smart_summarize
from core.arabic_text import is_arabic, normalize_spaces
from core.providers import price_lookup_grouped

APP_NAME = "Bassam Deep Search"
app = FastAPI(title=APP_NAME, version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# مجلداتك الحالية
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates") if os.path.isdir("templates") else None

@app.get("/healthz")
def healthz(): return {"status": "ok", "time": time.time()}

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    if not templates:
        return HTMLResponse("<h2>Bassam API is running</h2>")
    return templates.TemplateResponse("index.html", {"request": request, "app_name": APP_NAME})

@app.get("/api/search")
def api_search(
    q: str = Query(..., min_length=2, description="سؤال أو كلمات مفتاحية"),
    max_sources: int = 6,
    want_prices: bool = False,
    lang: Optional[str] = None
):
    q = normalize_spaces(q)
    result = deep_search(q, max_sources=max_sources, force_lang=lang)

    # تلخيص عربي مختصر + ترجمة تلقائية إلى العربية
    answer = smart_summarize(result["passages"], query=q)

    payload: Dict = {
        "query": q,
        "answer": answer["ar_answer"],
        "detected_lang": result["detected_lang"],
        "sources": result["sources"],   # [{title,url,site,lang,score}]
        "snippets": result["passages"], # [{url,text}]
        "tokens_used": result.get("tokens_used", 0),
        "latency_ms": int((time.time() - result["t0"]) * 1000),
    }

    if want_prices:
        payload["prices"] = price_lookup_grouped(q)

    return JSONResponse(payload)
    # ====== UPLOADS: إعدادات بسيطة ======
import pathlib, shutil, hashlib
from fastapi import File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pdfminer.high_level import extract_text
from PIL import Image
import imagehash
import numpy as np

UPLOAD_DIR = pathlib.Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# نعرض مجلد الرفع كستاتيك للوصول للملفات برابط عام (يلزم لـ Google Lens/Yandex)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

def _save_upload(tmpfile: UploadFile, subdir: str) -> str:
    folder = UPLOAD_DIR / subdir
    folder.mkdir(parents=True, exist_ok=True)
    # اسم ثابت من تجزئة المحتوى
    content = tmpfile.file.read()
    tmpfile.file.seek(0)
    h = hashlib.sha1(content).hexdigest()[:16]
    ext = (tmpfile.filename or "").split(".")[-1].lower()
    ext = ext if ext in ("png","jpg","jpeg","webp","pdf") else "bin"
    out = folder / f"{h}.{ext}"
    with open(out, "wb") as f:
        shutil.copyfileobj(tmpfile.file, f)
    return f"/uploads/{subdir}/{out.name}"

# ====== 1) رفع PDF وضمّه لـ RAG ======
@app.post("/api/upload/pdf")
async def upload_pdf(file: UploadFile = File(...)):
    public_url = _save_upload(file, "pdf")
    # استخرج نص PDF وضعه كملف .txt داخل data/ ليدخله RAG
    local_path = "." + public_url  # لأن public_url يبدأ بـ /uploads
    try:
        text = extract_text(local_path)
        data_dir = pathlib.Path("data")
        data_dir.mkdir(exist_ok=True)
        out_txt = data_dir / (pathlib.Path(local_path).stem.split("/")[-1] + ".txt")
        out_txt.write_text(text[:500000], encoding="utf-8", errors="ignore")
        return {"ok": True, "url": public_url, "indexed_file": str(out_txt)}
    except Exception as e:
        return {"ok": False, "url": public_url, "error": str(e)}

# ====== 2) رفع صورة والبحث بصريًا ======
def _basic_image_tags(local_path: str) -> str:
    """وصف بسيط جداً: ألوان سائدة + مقاس + (اختياري) OCR لاحقاً"""
    try:
        im = Image.open(local_path).convert("RGB")
        arr = np.array(im).reshape(-1, 3)
        mean = arr.mean(axis=0)
        w, h = im.size
        color = f"rgb({int(mean[0])},{int(mean[1])},{int(mean[2])})"
        return f"image {w}x{h} avg_color {color}"
    except Exception:
        return ""

def _image_hash(local_path: str) -> str:
    try:
        im = Image.open(local_path)
        return str(imagehash.phash(im))
    except Exception:
        return ""

def _search_by_image_links(public_url: str, extra_query: str = ""):
    # مزيج روابط جاهزة للبحث بالصورة عبر خدمات عامة تتقبل URL
    # (أحياناً تحتاج ضغط المستخدم للتأكيد)
    links = [
        {"name": "Google Lens (Upload URL)", "url": f"https://lens.google.com/uploadbyurl?url={public_url}"},
        {"name": "Yandex Images", "url": f"https://yandex.com/images/search?rpt=imageview&url={public_url}"},
        {"name": "Bing Images (preview)", "url": f"https://www.bing.com/images/search?q=imgurl:{public_url}&view=detailv2&iss=1"},
    ]
    # بحث نصي مساعد من اللون/المقاس
    if extra_query:
        from core.search import ddg_web
        hints = ddg_web(extra_query, max_results=5)
        for h in hints:
            links.append({"name": f"Related: {h.get('title','')[:40]}", "url": h["url"]})
    return links

@app.post("/api/search_image")
async def search_image(file: UploadFile = File(...)):
    public_url = _save_upload(file, "images")
    local_path = "." + public_url
    tags = _basic_image_tags(local_path)
    ph = _image_hash(local_path)
    return {
        "ok": True,
        "image_url": public_url,
        "perceptual_hash": ph,
        "tags": tags,
        "links": _search_by_image_links(public_url, extra_query=tags)
    }
