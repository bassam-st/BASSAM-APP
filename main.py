# main.py — نقطة تشغيل تطبيق بسام الذكي (نسخة مجانية بالكامل)

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# الدالة الذكية الموحَّدة
from src.brain import safe_run

app = FastAPI(title="Bassam الذكي", version="0.1")

# ملفات الواجهة
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# الصفحة الرئيسية
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# نفس الدالة على مسارين لراحة الواجهة
@app.get("/ask")
@app.get("/api/ask")
async def ask(query: str):
    try:
        result = safe_run(query)
        return JSONResponse({"query": query, "result": result})
    except Exception as e:
        return JSONResponse({"query": query, "result": ["error", f"تم التقاط خطأ: {e}"]})

# فحص الصحة
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
