# main.py — Bassam AI (Math + Search + Images + Gemini Smart)

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import html, re, os

# ===== واجهة =====
app = FastAPI(title="Bassam AI")

# ===== الصفحة الرئيسية HTML =====
HOME_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🤖 بسام الذكي - BASSAM AI APP</title>
  <style>
    body{font-family:'Segoe UI',Tahoma,Arial,sans-serif;background:#f1f5f9;direction:rtl;padding:20px}
    .container{max-width:800px;margin:auto;background:#fff;padding:20px;border-radius:14px;box-shadow:0 8px 25px rgba(0,0,0,.1)}
    .header{text-align:center;margin-bottom:20px}
    .header h1{margin-bottom:8px}
    .form-group{margin-bottom:12px}
    input[type="text"]{width:100%;padding:12px;border:1px solid #ddd;border-radius:8px}
    .mode-selector{display:flex;gap:8px;margin:10px 0}
    .mode-btn{flex:1;padding:10px;border:1px solid #ddd;border-radius:8px;text-align:center;cursor:pointer}
    .mode-btn.active{background:#4f46e5;color:#fff}
    .submit-btn{width:100%;padding:14px;background:#4f46e5;color:#fff;border:none;border-radius:8px;font-size:16px;cursor:pointer}
    .result a{color:#2563eb;text-decoration:none}
    .result li{margin:6px 0}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🤖 بسام الذكي</h1>
      <p>مساعدك للبحث والرياضيات والذكاء الاصطناعي</p>
    </div>
    <form method="post" action="/search">
      <div class="form-group">
        <input id="query" name="query" type="text" placeholder="اكتب سؤالك أو مسألتك" required>
      </div>
      <div class="mode-selector">
        <label class="mode-btn active"><input type="radio" name="mode" value="smart" checked hidden>🤖 ذكي</label>
        <label class="mode-btn"><input type="radio" name="mode" value="search" hidden>🔍 بحث</label>
        <label class="mode-btn"><input type="radio" name="mode" value="math" hidden>📊 رياضيات</label>
        <label class="mode-btn"><input type="radio" name="mode" value="images" hidden>🖼️ صور</label>
      </div>
      <button type="submit" class="submit-btn">🚀 ابدأ</button>
    </form>
  </div>
  <script>
    document.querySelectorAll('.mode-btn').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        document.querySelectorAll('.mode-btn').forEach(b=>b.classList.remove('active'));
        btn.classList.add('active'); btn.querySelector('input').checked = true;
      });
    });
  </script>
</body>
</html>
"""

def page_wrap(inner_html: str, title="نتيجة بسام"):
    return f"""<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<body style="font-family:Segoe UI,Tahoma,Arial,sans-serif;background:#f8fafc;direction:rtl;padding:20px">
<div style="max-width:900px;margin:auto;background:#fff;border-radius:14px;padding:22px;box-shadow:0 10px 30px rgba(0,0,0,.08)">
{inner_html}
<p style="margin-top:16px"><a href="/" style="color:#4f46e5">⬅ الرجوع</a></p>
</div></body></html>"""

# ===== رياضيات (SymPy) =====
from sympy import symbols, sympify, Eq, solveset, S, diff, integrate, sin, cos, tan, log, sqrt, pi
X = symbols("x")
SAFE = {"x": X, "pi": pi, "sin": sin, "cos": cos, "tan": tan, "log": log, "sqrt": sqrt}

def solve_math(query: str) -> str:
    q = query.strip()
    m = re.search(r"حل\s+(.*)=(.*)", q)
    if m:
        left = sympify(m.group(1), locals=SAFE); right = sympify(m.group(2), locals=SAFE)
        sol = solveset(Eq(left, right), X, domain=S.Complexes)
        return f"<h2>📌 حل المعادلة</h2><pre>{html.escape(str(sol))}</pre>"
    m = re.search(r"(اشتق|مشتقة)\s+(.*)", q)
    if m:
        expr = sympify(m.group(2), locals=SAFE); d = diff(expr, X)
        return f"<h2>📌 المشتقة</h2><pre>{html.escape(str(d))}</pre>"
    m = re.search(r"تكامل\s+(.*)\s+من\s+(.*)\s+إلى\s+(.*)", q)
    if m:
        expr = sympify(m.group(1), locals=SAFE); a = sympify(m.group(2), locals=SAFE); b = sympify(m.group(3), locals=SAFE)
        val = integrate(expr, (X, a, b))
        return f"<h2>📌 التكامل المحدد</h2><pre>{html.escape(str(val))}</pre>"
    try:
        expr = sympify(q, locals=SAFE)
        return f"<h2>📌 تبسيط/تقييم</h2><pre>{html.escape(str(expr.simplify()))}</pre>"
    except Exception as e:
        return f"<h2>تعذر فهم المسألة</h2><pre>{html.escape(str(e))}</pre>"

# ===== بحث وصور (DuckDuckGo) =====
try:
    from duckduckgo_search import DDGS
except Exception:
    DDGS = None

def do_web_search(q: str) -> str:
    if DDGS is None:
        return "<h2>🔍 البحث غير مُفعل</h2>"
    items = []
    with DDGS() as ddgs:
        for r in ddgs.text(q, max_results=6):
            items.append(f'<li><a target="_blank" href="{html.escape(r.get("href",""))}">{html.escape(r.get("title",""))}</a></li>')
    return "<h2>🔍 نتائج البحث</h2><ul class='result'>" + ("\n".join(items) or "<li>لا نتائج</li>") + "</ul>"

def do_image_search(q: str) -> str:
    if DDGS is None:
        return "<h2>🖼️ البحث عن الصور غير مُفعل</h2>"
    cards = []
    with DDGS() as ddgs:
        for r in ddgs.images(q, max_results=6, size="Medium", license_image="any"):
            src = r.get("image") or r.get("thumbnail")
            if src:
                cards.append(f"<img src='{html.escape(src)}' width='150' style='margin:6px;border-radius:8px'>")
    return "<h2>🖼️ صور</h2>" + ("".join(cards) or "<p>لا توجد صور</p>")

# ===== الذكاء الاصطناعي (Gemini) =====
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
    if not gemini_ready:
        return "<h2>🤖 الذكاء الاصطناعي غير مفعّل</h2><p>أضف GEMINI_API_KEY في Render.</p>"
    try:
        prompt = f"أنت بسام الذكي. جاوب بالعربية المبسطة.\n\nسؤال المستخدم:\n{q}"
        resp = GEMINI_MODEL.generate_content(prompt)
        text = resp.text or "(لا يوجد رد)"
        html_text = "<br>".join(html.escape(text).splitlines())
        return f"<h2>🤖 رد الذكاء الاصطناعي</h2><div>{html_text}</div>"
    except Exception as e:
        return f"<h2>خطأ من واجهة Gemini</h2><pre>{html.escape(str(e))}</pre>"

# ===== المسارات =====
@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(HOME_HTML)

@app.post("/search", response_class=HTMLResponse)
async def search(query: str = Form(...), mode: str = Form("smart")):
    q = query.strip(); m = mode.strip().lower()
    if m == "math":
        body = solve_math(q)
    elif m == "search":
        body = do_web_search(q)
    elif m == "images":
        body = do_image_search(q)
    else:
        body = do_smart(q)
    return HTMLResponse(page_wrap(body, title="نتيجة بسام"))

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
