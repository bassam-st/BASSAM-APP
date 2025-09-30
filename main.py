# main.py — تطبيق "بسام الذكي"
# بحث عميق + تلخيص + تعلم ذاتي + رفع PDF وصور + واجهة PWA

from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import os
from typing import List

# ========== Imports داخلية ==========
from core.search import deep_search
from core.summarizer import smart_summarize
from core.utils import ensure_dirs, extract_image_text

# التعلم الذاتي
from core.services.learning import save_feedback, log_search

# PDF (مع معالجة احتياطية إن لم تتوفر الأداة)
try:
    from core.services.pdf_tools import extract_pdf_text
except Exception:
    def extract_pdf_text(_path: str) -> str:
        return ""

# ========== إعداد التطبيق ==========
app = FastAPI(title="بسام الذكي — بحث عميق", version="2.0")

# ملفات ثابتة + القوالب
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# مجلدات لازمة
ensure_dirs(["static/uploads", "data/learning_logs", "logs", "data/ingested"])

# ========== الصفحة الرئيسية ==========
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# ========== البحث العام ==========
@app.post("/search")
async def search_route(q: str = Form(...), want_prices: bool = Form(False)):
    """
    ينفّذ بحثًا عميقًا عبر الويب ثم يكوّن ملخّصًا من مقتطفات النتائج.
    يعيد: {"answer": "...", "sources": [...]}
    """
    try:
        query = (q or "").strip()
        if not query:
            return JSONResponse({"answer": "", "sources": []})

        # 1) نفّذ البحث (ليست async)
        results = deep_search(query, include_prices=want_prices)

        # 2) لخص المقتطفات لعرض إجابة موجزة
        corpus = " ".join(r.get("snippet", "") for r in results)
        summary = smart_summarize(corpus, max_sentences=5) if corpus else ""

        # 3) تعلم ذاتي (سجل الكلمات/المصادر + خزّن الإجابة)
        try:
            log_search(query, [r["url"] for r in results])
            save_feedback(query, summary)
        except Exception as e:
            print(f"[learning/log error] {e}")

        return JSONResponse({"answer": summary or "لم أجد إجابة واضحة الآن.", "sources": results})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ========== رفع PDF وفهرسته ==========
@app.post("/upload_pdf")
async def upload_pdf(pdfFile: UploadFile = File(...)):
    """
    يحفظ PDF مؤقتًا، يستخرج النص، ويخزّنه ضمن data/ingested
    """
    try:
        if not pdfFile.filename.lower().endswith(".pdf"):
            return JSONResponse({"result": "الملف ليس PDF"}, status_code=400)

        save_path = os.path.join("static", "uploads", pdfFile.filename)
        with open(save_path, "wb") as f:
            f.write(await pdfFile.read())

        text = extract_pdf_text(save_path) or ""
        if not text.strip():
            return JSONResponse({"result": "لم أجد نصًا داخل PDF."})

        # خزّن النص ليستفيد منه مستقبلًا (تعلم سلِس)
        out_txt = os.path.join("data", "ingested", f"{os.path.splitext(pdfFile.filename)[0]}.txt")
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write(text)

        # حفظ مقتطف في السجل (اختياري)
        try:
            save_feedback(f"[PDF] {pdfFile.filename}", text[:500])
        except Exception as e:
            print(f"[feedback pdf] {e}")

        return JSONResponse({"result": "تم رفع الملف وفهرسته بنجاح ✅"})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ========== رفع صورة والبحث بالنص المستخرج ==========
@app.post("/upload_image")
async def upload_image(imgFile: UploadFile = File(...)):
    """
    يحفظ الصورة مؤقتًا، يستخرج النص عبر OCR، ثم يبحث في الويب بذلك النص
    """
    try:
        save_path = os.path.join("static", "uploads", imgFile.filename)
        with open(save_path, "wb") as f:
            f.write(await imgFile.read())

        text = extract_image_text(save_path) or ""
        if not text.strip():
            return JSONResponse({"text": "", "sources": [], "result": "لم يُستخرج نص من الصورة."})

        results = deep_search(text, include_images=True)
        try:
            save_feedback(f"[IMAGE OCR] {imgFile.filename}", text[:500])
            log_search(text, [r["url"] for r in results])
        except Exception as e:
            print(f"[learning image] {e}")

        return JSONResponse({"text": text, "sources": results})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ========== حفظ Feedback يدوي (عند الحاجة من الواجهة) ==========
@app.post("/feedback")
async def feedback_route(query: str = Form(...), answer: str = Form("")):
    try:
        save_feedback(query, answer)
        return JSONResponse({"result": "تم الحفظ ✅"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ========== فحص صحة ==========
@app.get("/healthz")
async def healthz():
    return {"status": "ok", "version": "2.0"}

# ========== تشغيل محلي ==========
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
