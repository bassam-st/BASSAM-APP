# main.py — نقطة تشغيل تطبيق بسّام الذكي (Omni Brain v2.1 + Streaming + Memory-ready)

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# البثّ الحي
from sse_starlette.sse import EventSourceResponse
import asyncio

# العقل الذكي الموحّد
from src.brain.omni_brain import omni_answer

app = FastAPI(title="Bassam الذكي — Omni Brain v2.1", version="2.1")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# محاولة ربط static/templates (لا يتعطل لو المجلدات غير موجودة)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
except Exception:
    templates = None

# ---------------------------
# صفحة رئيسية (fallback بسيط إن لم توجد قوالب)
# ---------------------------
BASIC_HTML = """
<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>بسّام الذكي</title>
<style>
body{font-family:system-ui,Segoe UI,Arial;max-width:780px;margin:24px auto;padding:0 12px;background:#f9fafb}
input,button{font-size:1em;border-radius:10px;border:1px solid #ccc;padding:10px;width:100%}
button{background:#1e88e5;color:#fff;cursor:pointer;margin-top:8px}
button:hover{background:#1565c0}
</style>
<h2>🤖 بسّام الذكي — Omni Brain</h2>
<form method="post" action="/search">
  <input name="query" placeholder="اكتب سؤالك..." autofocus>
  <button type="submit">ابدأ 🚀</button>
</form>
<p style="margin-top:10px">أو استخدم واجهة المحادثة: <a href="/chatui">/chatui</a></p>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return HTMLResponse(BASIC_HTML)

# ---------------------------
# تحويل زر "ابدأ 🚀" إلى واجهة المحادثة
# ---------------------------
@app.post("/search")
async def go_chat(request: Request):
    form = await request.form()
    query = (form.get("query") or "").strip()
    return RedirectResponse(url=f"/chatui?query={query}", status_code=303)

# ---------------------------
# واجهة المحادثة (chat.html) — إن لم توجد قوالب نعرض الصفحة البسيطة
# ---------------------------
@app.get("/chatui", response_class=HTMLResponse)
async def chatui(request: Request):
    if templates:
        return templates.TemplateResponse("chat.html", {"request": request})
    return HTMLResponse(BASIC_HTML)

# ---------------------------
# دالة مساعدة: تقسيم النص للبث التدريجي
# ---------------------------
def chunk_text(txt: str, size: int = 60):
    for i in range(0, len(txt), size):
        yield txt[i:i+size]

# ---------------------------
# دالة تغليف آمنة لاستدعاء العقل
# ---------------------------
def safe_run(message: str, session_id: str = "anon") -> str:
    try:
        return omni_answer(message or "", session_id=session_id)
    except Exception as e:
        return f"⚠️ خطأ أثناء المعالجة: {e}"

# ---------------------------
# مسار الذكاء (GET بسيط) — متوافق مع واجهات قديمة
# ---------------------------
@app.get("/ask")
async def ask_get(q: str = "", sid: str = "anon"):
    answer = safe_run(q, session_id=sid)
    return {"answer": answer}

# ---------------------------
# مسار الذكاء (POST من نموذج HTML)
# ---------------------------
@app.post("/ask")
async def ask_form(q: str = Form(None)):
    answer = safe_run(q or "")
    return JSONResponse({"answer": answer})

# ---------------------------
# مسار الذكاء (POST JSON) — متوافق مع واجهات خارجية
# ---------------------------
@app.post("/api/ask")
async def ask_json(payload: dict):
    q = (payload or {}).get("q", "")
    sid = (payload or {}).get("sid", "anon")
    answer = safe_run(q, session_id=sid)
    return {"answer": answer}

# ---------------------------
# البثّ الحي للردود (Streaming) عبر SSE
# ---------------------------
@app.get("/ask_stream")
async def ask_stream(query: str = "", sid: str = "anon"):
    async def eventgen():
        try:
            answer = safe_run(query, session_id=sid)
            for piece in chunk_text(answer, 50):
                yield {"event": "message", "data": piece}
                await asyncio.sleep(0.02)  # لمسة تدرّج
        except Exception as e:
            yield {"event": "message", "data": f"⚠️ خطأ: {e}"}
        finally:
            yield {"event": "end", "data": "[DONE]"}
    return EventSourceResponse(eventgen())

# ---------------------------
# فحص الصحة
# ---------------------------
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
