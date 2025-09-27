# main.py — نقطة تشغيل تطبيق بسام الذكي (نمط واحد: smart)

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# الدالة الذكية (نمط smart فقط)
from src.brain import safe_run

app = FastAPI(title="Bassam الذكي", version="0.2")

# ربط الملفات الثابتة والقوالب
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# الصفحة الرئيسية (تعرض النموذج + النتيجة إن وُجدت)
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None, "query": ""})


# استقبال النموذج (نمط واحد smart)
@app.post("/search", response_class=HTMLResponse)
async def search(request: Request, query: str = Form(...)):
    try:
        result = safe_run(query)
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "result": result, "query": query}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "result": f"حدث خطأ غير متوقع: {e}", "query": query}
        )


# واجهة API بسيطة للاستعلام المباشر
@app.get("/ask")
async def ask(query: str):
    try:
        result = safe_run(query)
        return JSONResponse({"query": query, "result": result})
    except Exception as e:
        return JSONResponse({"query": query, "result": f"error: {e}"})


# فحص الصحة
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
