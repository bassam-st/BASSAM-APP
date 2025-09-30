# main.py — تطبيق بسام الذكي (نسخة Render مستقرة)
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.search import deep_search
from core.summarizer import smart_summarize
from core.utils import extract_image_text, extract_pdf_text
from core.services.learning import save_feedback, log_search

import os

# إنشاء التطبيق
app = FastAPI(title="Bassam الذكي", version="3.1")

# ربط ملفات الواجهة
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ===== الصفحة الرئيسية =====
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ===== اختبار الصحة =====
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# ===== دالة البحث =====
@app.post("/search")
async def search_route(request: Request, q: str = Form(None), want_prices: bool = Form(False)):
    """
    نقطة البحث الأساسية — تدعم Form أو JSON
    """
    try:
        # جلب البيانات سواء كانت Form أو JSON
        if q is None:
            try:
                data = await request.json()
                q = data.get("q", "")
                want_prices = data.get("want_prices", False)
            except Exception:
                q = ""

        query = (q or "").strip()
        if not query:
            return JSONResponse({"answer": "", "sources": []})

        # تنفيذ البحث
        results = deep_search(query, include_prices=want_prices)

        # تلخيص النتائج
        corpus = " ".join(r.get("snippet", "") for r in results)
        summary = smart_summarize(corpus, max_sentences=5) if corpus else ""

        # حفظ سجل التعلم (اختياري)
        try:
            log_search(query, [r["url"] for r in results])
            save_feedback(query, summary)
        except Exception as e:
            print(f"[LEARNING ERROR] {e}")

        return JSONResponse({
            "answer": summary or "لم أجد إجابة دقيقة الآن، حاول بعبارة أخرى.",
            "sources": results
        })

    except Exception as e:
        print(f"[SEARCH ERROR] {e}")
        return JSONResponse({"error": "حدث خطأ في البحث"}, status_code=500)


# ===== رفع ملفات PDF =====
@app.post("/upload/pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """
    يرفع ملف PDF ويفهرسه
    """
    try:
        path = f"uploads/{file.filename}"
        os.makedirs("uploads", exist_ok=True)
        with open(path, "wb") as f:
            f.write(await file.read())

        text = extract_pdf_text(path)
        if not text.strip():
            return JSONResponse({"msg": "لم يتم العثور على نص في الملف."})

        return JSONResponse({"msg": "تم رفع الملف وفهرسته بنجاح", "text": text[:1000]})
    except Exception as e:
        print(f"[PDF ERROR] {e}")
        return JSONResponse({"msg": "حدث خطأ أثناء رفع الملف."}, status_code=500)


# ===== رفع الصور للبحث =====
@app.post("/upload/image")
async def upload_image(file: UploadFile = File(...)):
    """
    يرفع صورة ويستخرج النص منها للبحث
    """
    try:
        path = f"uploads/{file.filename}"
        os.makedirs("uploads", exist_ok=True)
        with open(path, "wb") as f:
            f.write(await file.read())

        text = extract_image_text(path)
        if not text.strip():
            return JSONResponse({"msg": "لم يتم العثور على نص في الصورة."})

        return JSONResponse({"msg": "تم استخراج النص من الصورة بنجاح", "text": text})
    except Exception as e:
        print(f"[IMAGE ERROR] {e}")
        return JSONResponse({"msg": "حدث خطأ أثناء تحليل الصورة."}, status_code=500)


# ===== البحث عن أشخاص / يوزرات =====
@app.post("/search/users")
async def search_users(request: Request, name: str = Form(...)):
    """
    بحث عن أشخاص / يوزرات (بشكل مبدئي يستخدم بحث الويب)
    """
    try:
        query = f"{name} site:linkedin.com OR site:twitter.com OR site:facebook.com"
        results = deep_search(query)
        return JSONResponse({"users": results})
    except Exception as e:
        print(f"[USER SEARCH ERROR] {e}")
        return JSONResponse({"error": "حدث خطأ في البحث عن الأشخاص."}, status_code=500)
