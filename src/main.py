# src/main.py — نقطة تشغيل تطبيق بسّام (QA + RAG + Memory + SSE)

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from sse_starlette.sse import EventSourceResponse  # لتفعيل البثّ الحي SSE
import itertools

# محرّك الذكاء الموحد مع الذاكرة
from src.brain.omni_brain import qa_pipeline

app = FastAPI(title="Bassam AI", version="2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# مجلدات الواجهة إن وُجدت
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
except Exception:
    templates = None

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# صفحة بسيطة إن لم يتوفر قالب
BASIC_HTML = """
<!doctype html><html lang=ar dir=rtl><meta charset=utf-8>
<title>Bassam AI</title>
<style>
body{font-family:system-ui,Segoe UI,Arial;max-width:780px;margin:24px auto;padding:0 12px}
input,button{font-size:16px}
</style>
<h2>محادثة بسّام الذكي</h2>
<form method="post" action="/ask">
  <input name="q" placeholder="اكتب سؤالك هنا..." style="width:100%;padding:10px"/>
  <input name="user" placeholder="اسم المستخدم (اختياري)" style="width:100%;padding:10px;margin-top:8px"/>
  <button type="submit" style="margin-top:8px">إرسال</button>
</form>
<p>تجربة GET سريعة: <code>/ask?q=ماهي%20عاصمة%20اليمن&user=ali</code></p>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return HTMLResponse(BASIC_HTML)

# ========== نقاط السؤال الأساسية ==========
# 1) POST من النموذج
@app.post("/ask")
async def ask_form(q: str = Form(""), user: str = Form("guest")):
    answer = qa_pipeline(q or "", user_id=(user or "guest"))
    return JSONResponse({"user": user or "guest", "answer": answer})

# 2) JSON API
@app.post("/api/ask")
async def ask_json(payload: dict):
    q = (payload or {}).get("q", "") or ""
    user = (payload or {}).get("user", "guest") or "guest"
    answer = qa_pipeline(q, user_id=user)
    return {"user": user, "answer": answer}

# 3) GET للتجربة السريعة في المتصفح
@app.get("/ask")
async def ask_get(q: str = "", user: str = "guest"):
    answer = qa_pipeline(q or "", user_id=(user or "guest"))
    return {"user": user or "guest", "answer": answer}

# ========== بثّ حي (SSE) اختياري ==========
# يجزّئ الرد إلى مقاطع قصيرة ويرسلها كأحداث SSE متتالية.
@app.get("/ask/stream")
async def ask_stream(q: str = "", user: str = "guest"):
    full_answer = qa_pipeline(q or "", user_id=(user or "guest"))

    # تقسيم بسيط للكلمات إلى دفعات صغيرة (حتى بدون sleep سيرسلها متتابعة)
    words = full_answer.split()
    chunks = []
    buf = []
    for w in words:
        buf.append(w)
        if len(buf) >= 12:  # كل 12 كلمة دفعة
            chunks.append(" ".join(buf))
            buf = []
    if buf:
        chunks.append(" ".join(buf))

    async def event_generator():
        for i, part in enumerate(chunks, start=1):
            yield {"event": "message", "id": str(i), "data": part}
        # إشارة انتهاء
        yield {"event": "done", "id": "end", "data": "[[END]]"}

    return EventSourceResponse(event_generator())
