# main.py — نقطة تشغيل تطبيق بسّام الذكي (Omni Brain v2.1)

import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# استدعاء العقل الموحد (Omni Brain)
from src.brain.omni_brain import omni_answer

app = FastAPI(title="Bassam الذكي — Omni Brain v2.1", version="2.1")

# ==============================
# إعدادات CORS (للربط مع الويب أو الجوال)
# ==============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================
# محاولة ربط static/templates
# ==============================
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
except Exception:
    templates = None

# ==============================
# صفحة رئيسية بسيطة
# ==============================
BASIC_HTML = """
<!doctype html><html lang=ar dir=rtl><meta charset=utf-8>
<title>بسّام الذكي</title>
<style>
body{font-family:'Segoe UI',Tahoma,sans-serif;max-width:760px;margin:24px auto;padding:0 12px;background:#f9fafb;color:#111}
input,button{font-size:1em;border-radius:10px;border:1px solid #ccc;padding:10px;width:100%}
button{background:#1e88e5;color:#fff;cursor:pointer;margin-top:8px}
button:hover{background:#1565c0}
.answer{margin-top:20px;padding:10px;background:#fff;border-radius:10px;box-shadow:0 2px 6px rgba(0,0,0,0.1)}
</style>
<h2>🤖 بسّام الذكي — Omni Brain (مشاعر + جمال + ذكاء)</h2>
<form method="post" action="/search">
  <input name="query" placeholder="اكتب سؤالك..." autofocus>
  <button type="submit">ابدأ 🚀</button>
</form>
<p style="margin-top:10px">أو جرّب مباشرة: <a href="/chatui">واجهة المحادثة</a></p>
</html>
"""

# ==============================
# الصفحة الرئيسية
# ==============================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if templates:
        return templates.TemplateResponse(request, "index.html", {})
    return HTMLResponse(BASIC_HTML)

# ==============================
# إعادة التوجيه لواجهة المحادثة
# ==============================
@app.post("/search")
async def go_chat(request: Request):
    form = await request.form()
    query = (form.get("query") or "").strip()
    return RedirectResponse(url=f"/chatui?query={query}", status_code=303)

# ==============================
# واجهة المحادثة (chat.html)
# ==============================
@app.get("/chatui", response_class=HTMLResponse)
async def chatui(request: Request):
    if templates:
        return templates.TemplateResponse(request, "chat.html", {})
    return HTMLResponse(BASIC_HTML)

# ==============================
# دالة الأمان لتجنب توقف التطبيق
# ==============================
def safe_run(message: str) -> str:
    try:
        return omni_answer(message or "")
    except Exception as e:
        return f"⚠️ خطأ أثناء المعالجة: {e}"

# ==============================
# واجهة الأسئلة (GET)
# ==============================
@app.get("/ask")
async def ask(query: str = ""):
    result = safe_run(query)
    return JSONResponse({"query": query, "result": result})

# ==============================
# واجهة المحادثة (POST JSON)
# ==============================
@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        message = data.get("message", "")
    except Exception:
        message = ""
    result = safe_run(message)
    return JSONResponse({"answer": result})

# ==============================
# فحص الصحة لـ Render
# ==============================
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# ==============================
# تشغيل محلي أو في Render
# ==============================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
