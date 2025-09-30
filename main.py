# main.py — Bassam v2: Deep Search + PWA + PDF/Images Upload + Auto-Learn
import os, re, json, time, html, pathlib, shutil, hashlib
from typing import Optional, List, Dict

from fastapi import FastAPI, Request, Query, File, UploadFile, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.search import deep_search, ddg_web
from core.summarizer import smart_summarize
from core.arabic_text import is_arabic, normalize_spaces
from core.providers import price_lookup_grouped, profile_links
from core.utils import ensure_dirs
from services.learning import save_feedback, log_search, learn_from_sources
from services.pdf_tools import extract_pdf_text
from services.image_tools import basic_image_tags, phash, image_search_links

APP_NAME = "Bassam Deep Search"
app = FastAPI(title=APP_NAME, version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Mount static/uploads/templates
ensure_dirs(["static", "templates", "uploads/images", "uploads/pdf", "data", "data/brain"])
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
templates = Jinja2Templates(directory="templates")

@app.get("/healthz")
def healthz():
    return {"status": "ok", "time": time.time()}

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "app_name": APP_NAME})

# ========== Core Search ==========
@app.get("/api/search")
def api_search(
    q: str = Query(..., min_length=2, description="سؤال أو كلمات مفتاحية"),
    max_sources: int = 6,
    want_prices: bool = False,
    lang: Optional[str] = None
):
    q = normalize_spaces(q)
    t0 = time.time()
    result = deep_search(q, max_sources=max_sources, force_lang=lang)
    answer = smart_summarize(result["passages"], query=q)

    payload: Dict = {
        "query": q,
        "answer": answer["ar_answer"],
        "detected_lang": result["detected_lang"],
        "sources": result["sources"],
        "snippets": result["passages"],
        "latency_ms": int((time.time() - t0) * 1000),
    }
    if want_prices:
        payload["prices"] = price_lookup_grouped(q)

    # learning log (no background jobs; only on-invocation)
    log_search(q, payload)
    return JSONResponse(payload)

# ========== People / Username finder ==========
@app.get("/api/profile")
def api_profile(name: str = Query(..., description="اسم أو يوزر")):
    links = profile_links(name)
    # نضيف بعض نتائج ddg النصية المساندة
    hits = ddg_web(name + " social media", max_results=10)
    return JSONResponse({"query": name, "links": links, "web": hits})

# ========== Upload: PDF -> data/ for RAG ==========
@app.post("/api/upload/pdf")
async def upload_pdf(file: UploadFile = File(...)):
    folder = pathlib.Path("uploads/pdf"); folder.mkdir(parents=True, exist_ok=True)
    content = file.file.read(); file.file.seek(0)
    sha = hashlib.sha1(content).hexdigest()[:16]
    out = folder / f"{sha}.pdf"
    with open(out, "wb") as f:
        shutil.copyfileobj(file.file, f)
    public_url = f"/uploads/pdf/{out.name}"
    # extract & index
    text = extract_pdf_text(str(out))
    idx = pathlib.Path("data") / f"pdf_{sha}.txt"
    idx.write_text(text[:500000], encoding="utf-8", errors="ignore")
    log_search("[PDF-UPLOAD]", {"file": public_url, "index": str(idx)})
    return {"ok": True, "url": public_url, "indexed_file": str(idx)}

# ========== Upload: Image -> visual search links ==========
@app.post("/api/search_image")
async def search_image(file: UploadFile = File(...)):
    folder = pathlib.Path("uploads/images"); folder.mkdir(parents=True, exist_ok=True)
    content = file.file.read(); file.file.seek(0)
    sha = hashlib.sha1(content).hexdigest()[:16]
    ext = (file.filename or "").split(".")[-1].lower()
    if ext not in ("png","jpg","jpeg","webp"): ext = "jpg"
    out = folder / f"{sha}.{ext}"
    with open(out, "wb") as f:
        shutil.copyfileobj(file.file, f)
    public_url = f"/uploads/images/{out.name}"

    tags = basic_image_tags(str(out))
    p = phash(str(out))
    return {
        "ok": True,
        "image_url": public_url,
        "perceptual_hash": p,
        "tags": tags,
        "links": image_search_links(public_url, extra_query=tags)
    }

# ========== Feedback & Learn ==========
@app.post("/api/feedback")
async def feedback(query: str = Form(...), answer_helpful: bool = Form(True), notes: str = Form("")):
    save_feedback(query, bool(answer_helpful), notes)
    return {"ok": True}

@app.post("/api/learn")
async def learn(query: str = Form(...), top_k: int = Form(3)):
    # يجلب أفضل المصادر للنص الحالي ويخزن نصها في data/brain لتتحسن الإجابات لاحقًا
    learned = learn_from_sources(query, top_k=top_k)
    return {"ok": True, "learned": learned}
