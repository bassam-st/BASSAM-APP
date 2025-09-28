# main.py — Bassam App (v3.1) مع واجهة محادثة

import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from src.brain.omni_brain import qa_pipeline, omni_answer

app = FastAPI(title="Bassam App v3.1", version="3.1")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# static/templates (لا تتعطل لو المجلدات غير موجودة)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
except Exception:
    templates = None

HOME_HINT = """
<!doctype html><meta charset="utf-8">
<title>Bassam App (v3.1)</title>
<div style="font-family:system-ui;max-width:720px;margin:40px auto;line-height:1.6">
  <h1>أهلًا بك في <b>Bassam App (v3.1)</b> 👋</h1>
  <ul>
    <li>/healthz — فحص الصحة</li>
    <li>/chatui — واجهة محادثة</li>
    <li>/ask?q=... — إجابة ذكية (RAG + ويب)</li>
    <li>/search?q=... — بحث ويب + تلخيص</li>
    <li>/summarize?text=...&sentences=5 — تلخيص نص</li>
  </ul>
</div>
"""

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return HTMLResponse(HOME_HINT)

@app.get("/chatui", response_class=HTMLResponse)
async def chatui(request: Request):
    if templates:
        return templates.TemplateResponse("chat.html", {"request": request})
    return HTMLResponse(HOME_HINT)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/ask")
async def ask(q: str = "", user: str = "guest"):
    # خط الذكاء مع الذاكرة (Omni v3)
    return {"answer": qa_pipeline(q, user_id=user)}

@app.get("/search")
async def search(q: str = ""):
    return {"answer": omni_answer(q)}

@app.get("/summarize")
async def summarize(text: str = "", sentences: int = 5):
    from src.brain.omni_brain import summarize_text
    return {"summary": summarize_text(text, max_sentences=sentences)}

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        q = (data.get("message") or "").strip()
        user = (data.get("user") or "guest").strip() or "guest"
    except Exception:
        q, user = "", "guest"
    return JSONResponse({"answer": qa_pipeline(q, user_id=user)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
