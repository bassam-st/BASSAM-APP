# main.py — Bassam App (v3.1)
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# الذكاء
from src.brain.omni_brain import omni_answer

APP_TITLE = "Bassam App (v3.1)"
app = FastAPI(title=APP_TITLE, version="3.1")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ربط static/templates (آمن لو المجلدات غير موجودة)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
except Exception:
    templates = None

# ===== واجهة HTML افتراضية =====
BASIC_HTML = """<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><title>Bassam — v3.1</title><meta name="viewport" content="width=device-width, initial-scale=1">
<style>:root{--bg:#0b1020;--card:#10162b;--text:#e7ecff;--muted:#9fb0ff;--accent:#5b8cff}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,Roboto}
.container{max-width:860px;margin:24px auto;padding:0 16px}.header{display:flex;align-items:center;gap:10px}
.badge{background:#182044;color:#b8c4ff;border:1px solid #223066;padding:4px 10px;border-radius:999px;font-size:12px}
.card{background:var(--card);border:1px solid #1f2b52;border-radius:16px;box-shadow:0 10px 30px rgba(0,0,0,.25)}
.chat{height:58vh;overflow:auto;padding:14px}.msg{padding:10px 12px;border-radius:12px;margin:8px 0;line-height:1.6;white-space:pre-wrap}
.user{background:#152043;border:1px solid #24336b;align-self:flex-end}.bot{background:#0f1a38;border:1px solid #1a2a60}
.row{display:flex;gap:10px;padding:12px;border-top:1px solid #1f2b52}
input{flex:1;background:#0b132b;border:1px solid #203060;color:var(--text);padding:12px;border-radius:12px;outline:none}
button{background:var(--accent);color:white;border:none;border-radius:12px;padding:12px 16px;font-weight:600;cursor:pointer}
button:disabled{opacity:.6;cursor:not-allowed}.hint{color:var(--muted);margin-top:10px;font-size:14px}a{color:#86a8ff}</style>
<div class="container"><div class="header"><h2 style="margin:0">🤖 بسّام — Omni Brain</h2><span class="badge">v3.1</span></div>
<div class="card" style="margin-top:16px"><div id="chat" class="chat"><div class="msg bot">أهلًا! اكتب سؤالك بالعربي وسأحاول مساعدتك 🌟</div></div>
<div class="row"><input id="q" placeholder="اكتب سؤالك… ثم اضغط إرسال"><button id="send">إرسال</button></div></div>
<p class="hint">نصائح: اسأل عن الرياضيات، ويكيبيديا، أو اطلب تلخيص صفحة.</p>
<div class="card" style="margin-top:18px;padding:14px"><b>نقاط الدخول (API):</b><ul>
<li><code>GET /healthz</code></li><li><code>GET /ask?q=...</code></li><li><code>POST /chat</code></li></ul></div></div>
<script>
const chat=document.getElementById('chat'),q=document.getElementById('q'),send=document.getElementById('send');
function push(role,text){const d=document.createElement('div');d.className='msg '+(role==='user'?'user':'bot');d.textContent=text;chat.appendChild(d);chat.scrollTop=chat.scrollHeight;}
async function ask(){const text=q.value.trim();if(!text)return;push('user',text);q.value='';send.disabled=true;
try{const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text})});
const j=await r.json();push('bot',j.answer||'—');}catch(e){push('bot','⚠️ حدث خطأ أثناء الاتصال بالخادم.');}finally{send.disabled=false;q.focus();}}
send.addEventListener('click',ask);q.addEventListener('keydown',e=>{if(e.key==='Enter'){ask();}})
</script></html>"""

# ===== صفحات =====
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return HTMLResponse(BASIC_HTML)

@app.get("/chatui", response_class=HTMLResponse)
async def chatui(request: Request):
    if templates:
        return templates.TemplateResponse("chat.html", {"request": request})
    return HTMLResponse(BASIC_HTML)

@app.post("/search")
async def go_chat(request: Request):
    form = await request.form()
    query = (form.get("query") or "").strip()
    return RedirectResponse(url=f"/chatui?query={query}", status_code=303)

# ===== وظائف الذكاء =====
def safe_run(message: str) -> str:
    try:
        return omni_answer(message or "")
    except Exception as e:
        return f"⚠️ خطأ أثناء المعالجة: {e}"

@app.get("/ask")
async def ask(query: str = ""):
    result = safe_run(query)
    return JSONResponse({"query": query, "result": result})

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        message = data.get("message", "")
    except Exception:
        message = ""
    result = safe_run(message)
    return JSONResponse({"answer": result})

# ===== Health Check =====
@app.get("/healthz")
async def healthz():
    return {"status": "ok", "app": APP_TITLE}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
