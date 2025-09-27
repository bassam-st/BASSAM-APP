# main.py — نقطة تشغيل تطبيق بسام الذكي (نمط واحد مُحسَّن: Smart)

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# نواة بسام
from src.brain import safe_run

app = FastAPI(title="Bassam الذكي", version="0.2")

# ربط الملفات الثابتة والقوالب
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# الصفحة الرئيسية
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "answer": None})


# معالجة النموذج (زر «ابدأ 🚀») — POST /smart
@app.post("/smart", response_class=HTMLResponse)
async def smart(request: Request, query: str = Form(...)):
    answer = safe_run(query)
    return templates.TemplateResponse("index.html", {"request": request, "answer": answer, "asked": query})


# واجهة برمجية بسيطة (للاختبار من المتصفح/الجوال): GET /ask?query=...
@app.get("/ask")
async def ask(query: str):
    result = safe_run(query)
    return JSONResponse({"query": query, "result": result})


# فحص الصحة
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
