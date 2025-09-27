# main.py — تطبيق بسّام الذكي (نسخة Smart مع محادثة خفيفة)

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# الدماغ
from src.brain import safe_run, chat_run

app = FastAPI(title="Bassam الذكي", version="0.2")

# ملفات ثابتة وقوالب
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# الصفحة الرئيسية
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# نموذج POST من الواجهة (زر ابدأ)
@app.post("/search", response_class=HTMLResponse)
async def search(request: Request, query: str = Form(...)):
    # نستخدم جلسة عامة للواجهة البسيطة
    answer = chat_run("web", query)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "answer": answer, "original": query},
    )


# واجهة محادثة برمجية (للاستخدام مستقبلاً من JS أو تطبيق خارجي)
class ChatIn(BaseModel):
    session_id: str
    message: str

@app.post("/chat")
async def chat_api(payload: ChatIn):
    answer = chat_run(payload.session_id, payload.message)
    return {"answer": answer}


# فحص الصحة
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
