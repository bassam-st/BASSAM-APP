# main.py — نقطة تشغيل تطبيق بسام الذكي (Smart)

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.brain import safe_run

app = FastAPI(title="Bassam الذكي", version="0.2")

# ملفات ثابتة وقوالب
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# الصفحة الرئيسية
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# استدعاء الذكاء - من النموذج (POST)
@app.post("/ask", response_class=PlainTextResponse)
async def ask_form(query: str = Form(...)):
    return safe_run(query)

# استدعاء الذكاء - من الرابط (GET) لأغراض الاختبار السريع
@app.get("/ask", response_class=PlainTextResponse)
async def ask_get(query: str):
    return safe_run(query)

# فحص الصحة
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
