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
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',Tahoma,Arial,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:20px;direction:rtl}
    .container{max-width:800px;margin:0 auto;background:#fff;border-radius:20px;box-shadow:0 20px 40px rgba(0,0,0,.1);overflow:hidden}
    .header{background:linear-gradient(135deg,#4facfe 0%,#00f2fe 100%);color:#fff;padding:40px 30px;text-align:center}
    .header h1{font-size:2.4em;margin-bottom:8px}
    .content{padding:28px}
    .form-group{margin-bottom:16px}
    label{display:block;margin-bottom:8px;font-weight:bold;color:#333}
    input[type="text"]{width:100%;padding:14px;border:2px solid #e1e5e9;border-radius:10px;font-size:16px}
    input[type="text"]:focus{border-color:#4facfe;outline:none}
    .mode-selector{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:14px 0}
    .mode-btn{padding:12px;border:2px solid #e1e5e9;background:#fff;border-radius:10px;cursor:pointer;text-align:center;font-weight:bold;display:flex;align-items:center;justify-content:center;gap:8px}
    .mode-btn.active{background:#4facfe;color:#fff;border-color:#4facfe}
    .submit-btn{width:100%;padding:16px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff;border:none;border-radius:12px;font-size:18px;font-weight:bold;cursor:pointer}
    .hint{color:#555;font-size:12px;margin-top:6px}
    .math-keyboard{display:none;flex-wrap:wrap;gap:8px;margin:8px 0 14px 0}
    .math-keyboard button{border:1px solid #dbe1e7;background:#fff;border-radius:8px;padding:8px 10px;cursor:pointer;font-size:14px}
    .features{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:18px;margin-top:22px}
    .feature{background:#f8f9fa;padding:16px;border-radius:10px;text-align:center}
    .footer{background:#f8f9fa;padding:18px;text-align:center;color:#666;border-top:1px solid #eee}
    a.link{color:#4f46e5;text-decoration:none}
    .result a{color:#2563eb;text-decoration:none}
    .result li{margin:8px 0}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🤖 بسام الذكي</h1>
      <p>مساعدك للبحث والرياضيات والذكاء الاصطناعي</p>
    </div>
    <div class="content">
      <p style="margin-bottom:10px">📷 تبي تحل من صورة؟ <a class="link" href="/upload">جرّب حل مسألة من صورة</a></p>
      <form method="post" action="/search">
        <div class="form-group">
          <label for="query">اطرح سؤالك أو مسألتك:</label>
          <input id="query" name="query" type="text" placeholder="مثال: حل 2*x**2 + 3*x - 2 = 0 | تكامل sin(x) من 0 إلى pi | اشتق 3*x**2 + 5*x - 7" required>
          <div class="hint">تلميح: استخدم x**2 للأسس، sqrt(x) للجذر، pi لِـπ.</div>
        </div>
        <div id="math-kbd" class="math-keyboard">
          <button type="button" onclick="ins('**')">^ برمجي ( ** )</button>
          <button type="button" onclick="ins('sqrt()')">√ الجذر</button>
          <button type="button" onclick="ins('pi')">π</button>
          <button type="button" onclick="ins('sin()')">sin</button>
          <button type="button" onclick="ins('cos()')">cos</button>
          <button type="button" onclick="ins('tan()')">tan</button>
          <button type="button" onclick="ins('ln()')">ln</button>
          <button type="button" onclick="templ('solve')">حل معادلة</button>
          <button type="button" onclick="templ('diff')">مشتقة</button>
          <button type="button" onclick="templ('int')">تكامل محدد</button>
        </div>
        <div class="mode-selector">
          <label class="mode-btn active"><input type="radio" name="mode" value="smart" checked style="display:none">🤖 ذكي</label>
          <label class="mode-btn"><input type="radio" name="mode" value="search" style="display:none">🔍 بحث</label>
          <label class="mode-btn"><input type="radio" name="mode" value="math" style="display:none">📊 رياضيات</label>
          <label class="mode-btn"><input type="radio" name="mode" value="images" style="display:none">🖼️ صور</label>
        </div>
        <button type="submit" class="submit-btn">🚀 ابدأ</button>
      </form>
      <div class="features">
        <div class="feature"><h3>🤖 ذكاء اصطناعي</h3><p>إجابات ذكية بالعربية</p></div>
        <div class="feature"><h3>📊 رياضيات</h3><p>مشتقات، تكاملات، حلول</p></div>
        <div class="feature"><h3>🔍 بحث</h3><p>بحث وتلخيص المحتوى</p></div>
        <div class="feature"><h3>🌐 دعم العربية</h3><p>مصمم للمستخدم العربي</p></div>
      </div>
    </div>
    <div class="footer"><p>تطبيق بسام الذكي - BASSAM AI APP</p></div>
  </div>
  <script>
    document.querySelectorAll('.mode-btn').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        document.querySelectorAll('.mode-btn').forEach(b=>b.classList.remove('active'));
        btn.classList.add('active'); btn.querySelector('input').checked = true; toggleKbd();
      });
    });
    function ins(s){const el=document.getElementById('query');const st=el.selectionStart,en=el.selectionEnd;
      el.value=el.value.slice(0,st)+s+el.value.slice(en); el.focus(); const p=st+s.length; el.setSelectionRange(p,p);}
    function templ(k){const el=document.getElementById('query');let t=""; if(k==='solve') t="حل 2*x**2 + 3*x - 2 = 0";
      if(k==='diff') t="اشتق 3*x**2 + 5*x - 7"; if(k==='int') t="تكامل sin(x) من 0 إلى pi";
      el.value=t; el.focus(); el.setSelectionRange(t.length,t.length);}
    function toggleKbd(){const mode=document.querySelector('input[name="mode"]:checked').value;
      document.getElementById('math-kbd').style.display=(mode==='math')?'flex':'none';}
    window.addEventListener('DOMContentLoaded', ()=>{document.getElementById('query').focus(); toggleKbd();});
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
        return f"<h2>📌 حل المعادلة</h2><p>{html.escape(str(Eq(left,right)))}</p><h3>الحل:</h3><pre>{html.escape(str(sol))}</pre>"
    m = re.search(r"(اشتق|مشتقة)\s+(.*)", q)
    if m:
        expr = sympify(m.group(2), locals=SAFE); d = diff(expr, X)
        return f"<h2>📌 المشتقة</h2><p>f(x)=<code>{html.escape(str(expr))}</code></p><h3>f'(x)=</h3><pre>{html.escape(str(d))}</pre>"
    m = re.search(r"تكامل\s+(.*)\s+من\s+(.*)\s+إلى\s+(.*)", q)
    if m:
        expr = sympify(m.group(1), locals=SAFE); a = sympify(m.group(2), locals=SAFE); b = sympify(m.group(3), locals=SAFE)
        val = integrate(expr, (X, a, b))
        return f"<h2>📌 التكامل المحدد</h2><p>∫<sub>{html.escape(str(a))}</sub><sup>{html.escape(str(b))}</sup> {html.escape(str(expr))} dx</p><h3>النتيجة:</h3><pre>{html.escape(str(val))}</pre>"
    m = re.search(r"تكامل\s+(.*)", q)
    if m:
        expr = sympify(m.group(1), locals=SAFE); F = integrate(expr, X)
        return f"<h2>📌 التكامل</h2><p>∫ {html.escape(str(expr))} dx</p><h3>النتيجة:</h3><pre>{html.escape(str(F))} + C</pre>"
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
        return "<h2>🔍 البحث غير مُفعل</h2><p>ثبّت duckduckgo-search.</p>"
    items = []
    with DDGS() as ddgs:
        for r in ddgs.text(q, max_results=8):
            items.append(f'<li><a target="_blank" href="{html.escape(r.get("href",""))}">{html.escape(r.get("title",""))}</a><br><small>{html.escape(r.get("body",""))}</small></li>')
    return "<h2>🔍 نتائج البحث</h2><ul class='result'>" + ("\n".join(items) or "<li>لا نتائج</li>") + "</ul>"

def do_image_search(q: str) -> str:
    if DDGS is None:
        return "<h2>🖼️ البحث عن الصور غير مُفعل</h2>"
    cards = []
    with DDGS() as ddgs:
        for r in ddgs.images(q, max_results=8, size="Medium", license_image="any"):
            src = r.get("image") or r.get("thumbnail"); title = r.get("title","")
            if src:
                cards.append(f"<div style='display:inline-block;margin:6px'><img src='{html.escape(src)}' width='180' style='border-radius:8px;display:block'><small>{html.escape(title)}</small></div>")
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

SMART_SYSTEM = (
    "أنت بسام الذكي. جاوب بالعربية المبسطة، نقاط موجزة عند الحاجة، "
    "مع أمثلة قصيرة وكود بسيط إذا لزم. عند المسائل الرياضية قدّم خطوات مختصرة."
)

def do_smart(q: str) -> str:
    if not gemini_ready:
        return "<h2>🤖 الذكاء الاصطناعي غير مفعّل</h2><p>أضف متغير البيئة <code>GEMINI_API_KEY</code> في Render.</p>"
    try:
        prompt = f"{SMART_SYSTEM}\n\nسؤال المستخدم:\n{q}"
        resp = GEMINI_MODEL.generate_content(
            prompt,
            generation_config={"temperature": 0.3, "max_output_tokens": 900},
        )
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

@app.get("/upload", response_class=HTMLResponse)
async def upload_page():
    return HTMLResponse(page_wrap("<h2>📷 رفع صورة</h2><p>ميزة قيد التطوير.</p>", title="رفع صورة"))

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
