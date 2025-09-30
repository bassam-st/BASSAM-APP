# main.py — تطبيق بسام الذكي (بحث عميق + صور + PDF + تعلم تلقائي + PWA)
from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import os, re, json, tempfile

# ===== استيراد الوحدات الداخلية =====
from core.utils import (
    ensure_dirs,
    extract_image_text,
    convert_arabic_numbers,
    normalize_text,
    clean_html,
)
from core.summarizer import smart_summarize
from core.search import deep_search, ddg_web
from core.services.learning import save_feedback, log_search, learn_from_sources
from core.services.pdf_tools import extract_pdf_text

# ===== إعداد التطبيق =====
app = FastAPI(title="بسام الذكي — بحث عميق", version="2.0")

# مجلدات ثابتة + قوالب
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# إنشاء المجلدات اللازمة
ensure_dirs(["static/uploads", "knowledge", "logs"])

# ===== الصفحة الرئيسية =====
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ===== البحث العام =====
@app.post("/search")
async def search_route(q: str = Form(...), want_prices: bool = Form(False)):
    """تنفيذ بحث عميق مع تلخيص ذكي"""
    q_norm = normalize_text(q)
    try:
        results = deep_search(q_norm, include_prices=want_prices)
        summary = smart_summarize(" ".join(r["snippet"] for r in results))
        log_search(q_norm, summary, results)
        return JSONResponse({"answer": summary, "sources": results})
    except Exception as e:
        return JSONResponse({"error": str(e)})


# ===== رفع ملف PDF وفهرسته =====
@app.post("/upload_pdf")
async def upload_pdf(pdfFile: UploadFile = File(...)):
    """يرفع ملف PDF ويستخرج نصه"""
    try:
        temp_path = f"static/uploads/{pdfFile.filename}"
        with open(temp_path, "wb") as f:
            f.write(await pdfFile.read())
        text = extract_pdf_text(temp_path)
        if not text.strip():
            return JSONResponse({"result": "لم يتم العثور على نص في هذا الملف."})
        # تخزين النص للتعلم الذاتي
        learn_from_sources("pdf", text)
        return JSONResponse({"result": "تم رفع الملف وتحليله بنجاح ✅"})
    except Exception as e:
        return JSONResponse({"error": str(e)})


# ===== رفع صورة والبحث بالصور =====
@app.post("/upload_image")
async def upload_image(imgFile: UploadFile = File(...)):
    """يرفع صورة ويبحث عن الصور المشابهة"""
    try:
        temp_path = f"static/uploads/{imgFile.filename}"
        with open(temp_path, "wb") as f:
            f.write(await imgFile.read())

        # استخراج النص من الصورة
        text = extract_image_text(temp_path)
        if not text.strip():
            return JSONResponse({"result": "لم يُستخرج أي نص من الصورة."})

        # بحث عميق بناءً على النص
        results = deep_search(text, include_images=True)
        learn_from_sources("image", text)
        return JSONResponse({"text": text, "sources": results})
    except Exception as e:
        return JSONResponse({"error": str(e)})


# ===== تعلم من المستخدم =====
@app.post("/feedback")
async def feedback_route(query: str = Form(...), answer: str = Form(...)):
    """يخزن التعلم الذاتي من المستخدم"""
    try:
        save_feedback(query, answer)
        return JSONResponse({"result": "تم حفظ التعلم بنجاح ✅"})
    except Exception as e:
        return JSONResponse({"error": str(e)})


# ===== فحص الصحة =====
@app.get("/healthz")
async def healthz():
    return {"status": "ok", "version": "2.0"}


# ===== التشغيل المحلي =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
