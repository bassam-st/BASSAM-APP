# main.py — نقطة تشغيل تطبيق بسام الذكي (نمط ذكي فقط)

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# استدعاء النظام الذكي من brain
from src.brain import safe_run

# إنشاء التطبيق
app = FastAPI(title="Bassam الذكي", version="1.0")

# ربط الملفات الثابتة (CSS / صور / JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# مجلد القوالب
templates = Jinja2Templates(directory="templates")


# الصفحة الرئيسية
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# استقبال استفسار المستخدم عبر النموذج (POST)
@app.post("/search")
async def search(request: Request, query: str = Form(...)):
    try:
        result = safe_run(query)
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "query": query, "result": result}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "query": query, "result": f"حدث خطأ: {e}"}
        )


# إعادة توجيه GET /search → الصفحة الرئيسية
@app.get("/search")
async def search_redirect():
    return RedirectResponse(url="/", status_code=303)


# واجهة API مباشرة (للإختبار عبر الرابط)
@app.get("/ask")
async def ask(query: str):
    try:
        result = safe_run(query)
        return JSONResponse({"query": query, "result": result})
    except Exception as e:
        return JSONResponse({"query": query, "result": f"تم التقاط خطأ: {e}"})


# فحص الصحة
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
