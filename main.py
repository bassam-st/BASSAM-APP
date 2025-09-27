# main.py — نقطة تشغيل تطبيق بسام الذكي (Smart: رياضيات + عقل/بحث)

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.brain import safe_run

app = FastAPI(title="Bassam الذكي", version="1.1")

# ربط الملفات الثابتة والقوالب
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# الصفحة الرئيسية
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# معالجة النموذج (الزر 🚀 في index.html يرسل POST إلى /search)
@app.post("/search", response_class=HTMLResponse)
async def search(request: Request, query: str = Form(...)):
    answer = safe_run(query)
    return templates.TemplateResponse("index.html", {"request": request, "answer": answer})


# حماية من فتح /search كـ GET (يعطي 405 عادة) → نعيد توجيه المستخدم للصفحة الرئيسية
@app.get("/search")
async def search_get_redirect():
    return RedirectResponse(url="/", status_code=303)


# واجهة بسيطة للاختبار عبر الرابط: /ask?query=...
@app.get("/ask", response_class=PlainTextResponse)
async def ask(query: str):
    return safe_run(query)


# فحص الصحة
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
