# main.py — Bassam AI (Omni Brain v3)

import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# Omni Brain
from src.brain.omni_brain import omni_answer

app = FastAPI(title="Bassam الذكي — Omni Brain v3", version="3.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# static/templates (آمن لو المجلدات غير موجودة)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
except Exception:
    templates = None

# صفحة بسيطة بديلة
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
<h2>🤖 بسّام الذكي — Omni Brain v3</h2>
<form method="post" action="/search">
  <input name="query" placeholder="اكتب سؤالك..." autofocus>
  <button type="submit">ابدأ 🚀</button>
</form>
<p style="margin-top:10px">أو جرّب: <a href="/chatui">واجهة المحادثة</a></p>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if templates:
        # Starlette ≥0.37: TemplateResponse(request, name, context)
        return templates.TemplateResponse(request, "index.html", {})
    return HTMLResponse(BASIC_HTML)

@app.post("/search")
async def go_chat(request: Request):
    form = await request.form()
    query = (form.get("query") or "").strip()
    return RedirectResponse(url=f"/chatui?query={query}", status_code=303)

@app.get("/chatui", response_class=HTMLResponse)
async def chatui(request: Request):
    if templates:
        return templates.TemplateResponse(request, "chat.html", {})
    return HTMLResponse(BASIC_HTML)

def safe_run(message: str) -> str:
    try:
        return omni_answer(message or "")
    except Exception as e:
        return f"⚠️ خطأ أثناء المعالجة: {e}"

@app.get("/ask")
async def ask(query: str = ""):
    return JSONResponse({"query": query, "result": safe_run(query)})

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        message = data.get("message", "")
    except Exception:
        message = ""
    return JSONResponse({"answer": safe_run(message)})

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
