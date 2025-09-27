# main.py — نقطة تشغيل تطبيق بسام الذكي

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# استدعاء النظام الذكي من brain
from src.brain import safe_run

# إنشاء التطبيق
app = FastAPI(title="Bassam الذكي", version="0.1")

# ربط الملفات الثابتة (مثلاً CSS/JS/صور)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ربط القوالب (HTML)
templates = Jinja2Templates(directory="templates")


# الصفحة الرئيسية
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# مسار الذكاء: استفسار المستخدم
@app.get("/ask")
async def ask(query: str):
    try:
        result = safe_run(query)
        return JSONResponse({"query": query, "result": result})
    except Exception as e:
        return JSONResponse({"query": query, "result": ["error", f"تم التقاط خطأ: {e}"]})


# مسار فحص الصحة
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
