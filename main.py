# main.py — Bassam App (v3.2 Pro) — واجهة + ذكاء + تلخيص + RAG عربي
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# استدعاء الذكاء من العقل
from src.brain.omni_brain import omni_answer

APP_TITLE = "Bassam App (v3.2)"
app = FastAPI(title=APP_TITLE, version="3.2")

# السماح بالوصول من كل مكان (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ربط المجلدات الثابتة والقوالب
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
except Exception:
    templates = None

# ====== واجهة بسيطة تشبه ChatGPT ======
BASIC_HTML = """
<!doctype html>
<html lang="ar" dir="rtl">
<meta charset="utf-8">
<title>Bassam الذكي — v3.2</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{font-family:system-ui;background:#0b1020;color:#fff;margin:0;padding:0;text-align:right}
.container{max-width:900px;margin:auto;padding:20px}
.input-row{display:flex;gap:10px;margin-top:15px}
input{flex:1;padding:10px;border-radius:8px;border:none;background:#111a33;color:#fff}
button{background:#3a6eff;color:#fff;border:none;border-radius:8px;padding:10px 16px;font-weight:bold;cursor:pointer}
.chat{background:#10182e;border-radius:12px;padding:15px;min-height:60vh;overflow:auto;margin-top:20px}
.msg{margin:8px 0;padding:10px;border-radius:10px;line-height:1.6}
.user{background:#162550}
.bot{background:#0f1a38}
</style>
<div class="container">
  <h2>🤖 بسّام الذكي — الإصدار 3.2</h2>
  <div class="chat" id="chat"><div class="msg bot">مرحبًا! اكتب سؤالك بالعربي وسأجيبك مباشرة ✨</div></div>
  <div class="input-row"><input id="q" placeholder="اكتب سؤالك هنا..."><button id="send">إرسال</button></div>
</div>
<script>
const chat=document.getElementById('chat');const q=document.getElementById('q');const send=document.getElementById('send');
function push(role,text){const d=document.createElement('div');d.className='msg '+role;d.textContent=text;chat.appendChild(d);chat.scrollTop=chat.scrollHeight;}
async function ask(){const text=q.value.trim();if(!text)return;push('user',text);q.value='';send.disabled=true;
try{const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text})});
const j=await r.json();push('bot',j.answer||'—');}catch(e){push('bot','⚠️ حدث خطأ أثناء الاتصال بالخادم.');}
finally{send.disabled=false;q.focus();}}
send.onclick=ask;q.addEventListener('keydown',e=>{if(e.key==='Enter'){ask();}});
</script>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return HTMLResponse(BASIC_HTML)

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        msg = data.get("message", "")
    except Exception:
        msg = ""
    answer = omni_answer(msg)
    return JSONResponse({"answer": answer})

@app.get("/ask")
async def ask(q: str = ""):
    return JSONResponse({"answer": omni_answer(q)})

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "app": APP_TITLE}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
