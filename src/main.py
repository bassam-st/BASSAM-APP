from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from src.brain.gemini_search import qa_pipeline

app = FastAPI(title="Bassam AI", version="0.1")

# CORS (اختياري)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# مجلدات الواجهة إن وجدت
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
except Exception:
    templates = None

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# صفحة رئيسية بسيطة (إن لم يوجد قالب)
BASIC_HTML = """
<!doctype html>
<html lang="ar" dir="rtl">
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Bassam AI</title>
  <style>body{font-family:system-ui,Segoe UI,Arial;max-width:780px;margin:24px auto;padding:0 12px}</style>
  <h2>محادثة بسّام الذكي</h2>
  <form method="post" action="/ask">
    <input name="q" placeholder="اكتب سؤالك هنا..." style="width:100%;padding:10px" />
    <button type="submit" style="margin-top:8px">إرسال</button>
  </form>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return HTMLResponse(BASIC_HTML)

# يقبل POST من النموذج، وأيضًا JSON عبر تطبيقات خارجية
@app.post("/ask")
async def ask_form(q: str = Form(None)):
    answer = qa_pipeline(q or "")
    return JSONResponse({"answer": answer})

# نقطة بديلة للواجهات الأمامية التي ترسل JSON
@app.post("/api/ask")
async def ask_json(payload: dict):
    q = (payload or {}).get("q", "")
    answer = qa_pipeline(q)
    return {"answer": answer}

# نقطة GET اختيارية للاختبار السريع في المتصفح
@app.get("/ask")
async def ask_get(q: str = ""):
    answer = qa_pipeline(q)
    return {"answer": answer}
