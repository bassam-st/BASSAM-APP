# main.py — نقطة تشغيل تطبيق بسام الذكي (نسخة متقدمة مع واجهة محادثة)

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# استدعاء النظام الذكي من brain
from src.brain import safe_run

# إنشاء التطبيق
app = FastAPI(title="Bassam الذكي", version="1.0")

# تفعيل CORS (مفيد للربط مع واجهات الموبايل والويب)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ربط الملفات الثابتة (CSS / JS / صور)
app.mount("/static", StaticFiles(directory="static"), name="static")

# مجلد القوالب HTML
templates = Jinja2Templates(directory="templates")

# ---------------------------
# الصفحة الرئيسية
# ---------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ---------------------------
# تحويل زر "ابدأ 🚀" إلى واجهة المحادثة الذكية
# ---------------------------
@app.post("/search")
async def go_chat(request: Request):
    form = await request.form()
    query = form.get("query", "").strip()
    # عند الضغط على الزر، ينتقل المستخدم إلى صفحة المحادثة مع تمرير السؤال
    return RedirectResponse(url=f"/chatui?query={query}", status_code=303)


# ---------------------------
# واجهة المحادثة الجديدة (chat.html)
# ---------------------------
@app.get("/chatui", response_class=HTMLResponse)
async def chatui(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


# ---------------------------
# مسار الذكاء: يُستخدم من داخل chat.html
# ---------------------------
@app.get("/ask")
async def ask(query: str):
    try:
        result = safe_run(query)
        return JSONResponse({"query": query, "result": result})
    except Exception as e:
        return JSONResponse({"query": query, "result": f"⚠️ خطأ أثناء المعالجة: {e}"})


# ---------------------------
# واجهة محادثة (POST) — يمكن استخدامها لاحقًا لتطبيق الموبايل
# ---------------------------
@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        message = data.get("message", "")
        result = safe_run(message)
        return JSONResponse({"answer": result})
    except Exception as e:
        return JSONResponse({"answer": f"⚠️ حدث خطأ أثناء الرد: {e}"})


# ---------------------------
# مسار فحص الصحة (لـ Render)
# ---------------------------
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
