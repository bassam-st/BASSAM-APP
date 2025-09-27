# main.py — تطبيق بسام الذكي (نمط Smart واحد)

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# نواة الذكاء
from src.brain import safe_run

app = FastAPI(title="BASSAM AI", version="0.2")

# ربط الملفات الثابتة والقوالب
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# الصفحة الرئيسية
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, answer: str | None = None):
    return templates.TemplateResponse("index.html", {"request": request, "answer": answer})


# معالجة الفورم (زر ابدأ)
@app.post("/search", response_class=HTMLResponse)
async def search(request: Request, query: str = Form(...)):
    try:
        answer = safe_run(query)
    except Exception as e:
        answer = f"حدث خطأ غير متوقع: {e}"
    return templates.TemplateResponse("index.html", {"request": request, "answer": answer})


# API بسيطة للاستفسار عبر رابط
@app.get("/ask")
async def ask(query: str):
    try:
        result = safe_run(query)
        return JSONResponse({"query": query, "result": result})
    except Exception as e:
        return JSONResponse({"query": query, "result": f'error: {e}'})


# فحص صحة
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
