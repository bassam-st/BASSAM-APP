# main.py — نقطة تشغيل تطبيق بسام الذكي

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# استدعاء النظام الذكي من brain
from src.brain import safe_run

# إنشاء التطبيق
app = FastAPI(title="Bassam الذكي", version="0.1")

# ربط الملفات الثابتة (CSS/JS/صور)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ربط القوالب (HTML)
templates = Jinja2Templates(directory="templates")

# الصفحة الرئيسية
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 🧠 مسار الذكاء (GET) — لاختبار مباشر
@app.get("/ask")
async def ask(query: str):
    try:
        result = safe_run(query)
        return JSONResponse({"query": query, "result": result})
    except Exception as e:
        return JSONResponse({"query": query, "result": ["error", f"تم التقاط خطأ: {e}"]})

# 🧠 مسار الذكاء (POST) — يستخدمه الزر في الواجهة
class AskBody(BaseModel):
    query: str

@app.post("/api/ask")
async def api_ask(body: AskBody):
    try:
        result = safe_run(body.query)
        return JSONResponse({"query": body.query, "result": result})
    except Exception as e:
        return JSONResponse({"query": body.query, "result": ["error", f"تم التقاط خطأ: {e}"]})

# ✅ فحص الصحة
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
