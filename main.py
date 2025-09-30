# main.py — بسام الذكي (بحث عميق + تعلم ذاتي + رفع صور و PDF + تلخيص)
from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.search import deep_search
from core.utils import is_arabic, convert_arabic_numbers
from core.services.learning import save_feedback, log_search, learn_from_sources

import os, time, json, shutil

app = FastAPI(title="Bassam الذكي", version="2.0")

# ربط ملفات static و templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# المجلدات المؤقتة
os.makedirs("uploads", exist_ok=True)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/search")
async def search(q: str = Form(...), want_prices: bool = Form(False)):
    start = time.time()
    try:
        q_norm = convert_arabic_numbers(q.strip())
        summary, sources = await deep_search(q_norm, want_prices)
        latency = round(time.time() - start, 2)

        # الحفظ في سجل التعلم الذاتي
        try:
            save_feedback(q_norm, summary)  # ✅ تم تصحيح الخطأ هنا بإضافة except لاحقًا
        except Exception as e:
            print(f"[Feedback error] {e}")

        return JSONResponse({
            "answer": summary or "لم يتم العثور على نتيجة واضحة.",
            "sources": sources,
            "latency": latency
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/upload_pdf")
async def upload_pdf(pdfFile: UploadFile):
    try:
        path = f"uploads/{pdfFile.filename}"
        with open(path, "wb") as f:
            shutil.copyfileobj(pdfFile.file, f)

        learn_from_sources("PDF", path)
        return JSONResponse({"msg": f"تمت فهرسة الملف: {pdfFile.filename}"})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/upload_image")
async def upload_image(imgFile: UploadFile):
    try:
        path = f"uploads/{imgFile.filename}"
        with open(path, "wb") as f:
            shutil.copyfileobj(imgFile.file, f)

        learn_from_sources("صورة", path)
        return JSONResponse({"msg": f"تم رفع الصورة: {imgFile.filename}"})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
