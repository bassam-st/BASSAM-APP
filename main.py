# main.py — نقطة تشغيل تطبيق بسام الذكي

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# استدعاء النظام الذكي من brain
from src.brain import safe_run

# إنشاء التطبيق
app = FastAPI(title="Bassam الذكي", version="1.0")

# تفعيل CORS لتطبيق الويب أو الموبايل
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ربط الملفات الثابتة (CSS/JS/صور)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ربط القوالب (HTML)
templates = Jinja2Templates(directory="templates")

# الصفحة الرئيسية
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# صفحة واجهة المحادثة التفاعلية
@app.get("/chatui", response_class=HTMLResponse)
async def chatui(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

# واجهة الذكاء — البحث أو الرياضيات
@app.get("/ask")
async def ask(query: str):
    try:
        result = safe_run(query)
        return JSONResponse({"query": query, "result": result})
    except Exception as e:
        return JSONResponse({"query": query, "result": f"⚠️ حدث خطأ أثناء المعالجة: {e}"})

# واجهة المحادثة — تستخدمها chat.html
@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        message = data.get("message", "")
        result = safe_run(message)
        return JSONResponse({"answer": result})
    except Exception as e:
        return JSONResponse({"answer": f"⚠️ حدث خطأ أثناء الرد: {e}"})

# فحص الصحة (لريندر)
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
