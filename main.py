# main.py — Bassam AI (Math + Smart + Search + Images)
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import os, html

from src.core import math_engine

# =========================
# تهيئة التطبيق
# =========================
app = FastAPI(title="Bassam AI")

# =========================
# واجهة HTML (مع MathJax)
# =========================
HOME_HTML = """
<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🤖 بسام الذكي</title>
<script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
<script id="MathJax-script" async
  src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
<style>
*{box-sizing:border-box} body{font-family:Segoe UI,Tahoma,Arial,sans-serif;background:#f5f7ff;margin:0}
.container{max-width:900px;margin:30px auto;background:#fff;border-radius:16px;box-shadow:0 12px 30px rgba(0,0,0,.08);overflow:hidden}
.header{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:28px 24px;text-align:center}
.header h1{margin:0 0 4px;font-size:28px}
.sub{opacity:.9}
.content{padding:22px}
label{font-weight:600;color:#222}
input[type=text]{width:100%;padding:14px;border:2px solid #e8ebf2;border-radius:12px;margin:8px 0 6px;font-size:16px}
.mode{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:12px 0 16px}
.mode label{display:flex;align-items:center;justify-content:center;gap:8px;border:2px solid #e8ebf2;border-radius:12px;padding:10px;cursor:pointer}
.mode .active{background:#667eea;color:#fff;border-color:#667eea}
.btn{width:100%;padding:14px;border:0;border-radius:12px;background:#4f46e5;color:#fff;font-weight:700;font-size:16px;cursor:pointer}
.result a{color:#2563eb;text-decoration:none}
.result li{margin:8px 0}
.card{background:#fff;border-radius:14px;box-shadow:0 10px 28px rgba(0,0,0,.08);padding:20px}
.footer{padding:14px 22px;border-top:1px solid #f0f2f7;color:#6b7280;text-align:center}
</style>
<div class="container">
  <div class="header">
    <h1>🤖 بسام الذكي</h1>
    <div class="sub">مساعد مجاني للرياضيات، البحث، والذكاء الاصطناعي</div>
  </div>
  <div class="content">
    <form method="post" action="/search">
      <label>اكتب سؤالك أو مسألتك:</label>
      <input name="query" type="text" required placeholder="مثال: حل x**2 - 5*x + 6 = 0 | اشتق x*sin(x) | تكامل cos(x) من 0 إلى pi">
      <div class="mode" id="modeBox">
        <label class="active"><input style="display:none" type="radio" name="mode" value="smart" checked>🤖 ذكي</label>
        <label><input style="display:none" type="radio" name="mode" value="math">📊 رياضيات</label>
        <label><input style="display:none" type="radio" name="mode" value="search">🔎 بحث</label>
        <label><input style="display:none" type="radio" name="mode" value="images">🖼️ صور</label>
      </div>
      <button class="btn">🚀 ابدأ</button>
    </form>
  </div>
  <div class="footer">BASSAM AI © مجاني</div>
</div>
<script>
document.querySelectorAll('#modeBox label').forEach(l=>{
  l.addEventListener('click', ()=>{
    document.querySelectorAll('#modeBox label').forEach(x=>x.classList.remove('active'));
    l.classList.add('active'); l.querySelector('input').checked = true;
  })
})
</script>
"""

def page_wrap(inner: str, title="نتيجة بسام"):
    return f"""<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<body style="background:#f5f7ff;font-family:Segoe UI,Tahoma,Arial,sans-serif;margin:0;padding:20px">
<div class="card" style="max-width:900px;margin:auto">{inner}
<p style="margin-top:14px"><a href="/" style="color:#4f46e5;text-decoration:none">⬅ الرجوع</a></p></div></body></html>"""

# =========================
# بحث وصور (DuckDuckGo)
# =========================
try:
    from duckduckgo_search import DDGS
except Exception:
    DDGS = None

def do_web_search(q: str) -> str:
    if DDGS is None:
        return "<h2>🔍 البحث غير مُفعل</h2>"
    items = []
    with DDGS() as ddgs:
        for r in ddgs.text(q, max_results=6, region="xa-ar"):
            items.append(f"<li><a href='{html.escape(r['href'])}' target='_blank'>{html.escape(r['title'])}</a><br><small>{html.escape(r['body'])}</small></li>")
    return "<h2>نتائج البحث</h2><ul>" + ("".join(items) or "<li>لا نتائج</li>") + "</ul>"

def do_image_search(q: str) -> str:
    if DDGS is None:
        return "<h2>🖼️ البحث عن الصور غير مُفعل</h2>"
    imgs = []
    with DDGS() as ddgs:
        for r in ddgs.images(q, max_results=6):
            src = r.get("image") or r.get("thumbnail")
            if src:
                imgs.append(f"<img src='{html.escape(src)}' width='180' style='margin:6px;border-radius:8px'>")
    return "<h2>🖼️ صور</h2>" + ("".join(imgs) or "<p>لا توجد صور</p>")

# =========================
# ذكاء اصطناعي (Gemini اختياري)
# =========================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_ready = False
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        GEMINI_MODEL = genai.GenerativeModel("gemini-1.5-flash")
        gemini_ready = True
    except Exception:
        gemini_ready = False

def do_smart(q: str) -> str:
    if gemini_ready:
        try:
            resp = GEMINI_MODEL.generate_content(
                f"أنت بسام الذكي. جاوب بالعربية الواضحة مع خطوات عند الحاجة:\n{q}",
                generation_config={"temperature":0.3,"max_output_tokens":700}
            )
            return "<h2>🤖 رد الذكاء الاصطناعي</h2><div>" + "<br>".join(resp.text.splitlines()) + "</div>"
        except Exception:
            pass
    # fallback مجاني: جرّب الرياضيات أو البحث
    math_try = math_engine.solve_query(q)
    if "تعذر" not in math_try:
        return math_try
    return do_web_search(q)

# =========================
# المسارات
# =========================
@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(HOME_HTML)

@app.post("/search", response_class=HTMLResponse)
async def search(query: str = Form(...), mode: str = Form("smart")):
    q = (query or "").strip()
    if mode=="math":
        body = math_engine.solve_query(q)
    elif mode=="search":
        body = do_web_search(q)
    elif mode=="images":
        body = do_image_search(q)
    else:
        body = do_smart(q)
    return HTMLResponse(page_wrap(body, title="نتيجة بسام"))

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
