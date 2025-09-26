# main.py — Bassam AI (Math + Search + Images + Gemini Smart + Pretty Math)

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import html, re, os, time

# ===== إنشاء التطبيق =====
app = FastAPI(title="Bassam AI")

# ===== الصفحة الرئيسية HTML (مع MathJax) =====
HOME_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🤖 بسام الذكي - BASSAM AI APP</title>

  <!-- تفعيل MathJax لعرض الرياضيات بشكل جميل -->
  <script>
    window.MathJax = { tex: { inlineMath: [['$', '$'], ['\\\\(', '\\\\)']] } };
  </script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

  <style>
    body{font-family:'Segoe UI',Tahoma,Arial,sans-serif;background:#f1f5f9;direction:rtl;padding:20px}
    .container{max-width:820px;margin:auto;background:#fff;padding:22px;border-radius:16px;box-shadow:0 10px 30px rgba(0,0,0,.08)}
    .header{text-align:center;margin-bottom:16px}
    .header h1{margin:0 0 6px}
    .hint{color:#666;font-size:12px;margin-top:6px}
    .form-group{margin-bottom:12px}
    input[type="text"]{width:100%;padding:12px;border:1px solid #e5e7eb;border-radius:10px;font-size:16px}
    .mode-selector{display:flex;gap:8px;margin:12px 0}
    .mode-btn{flex:1;padding:10px;border:1px solid #e5e7eb;border-radius:10px;text-align:center;cursor:pointer}
    .mode-btn.active{background:#4f46e5;color:#fff;border-color:#4f46e5}
    .submit-btn{width:100%;padding:14px;background:#4f46e5;color:#fff;border:none;border-radius:10px;font-size:16px;cursor:pointer}
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
        <label for="query">اطرح سؤالك أو مسألتك:</label>
        <input id="query" name="query" type="text"
               placeholder="مثال: حل 2*x**2 + 3*x - 2 = 0 | تكامل sin(x) من 0 إلى pi | اشتق 3*x**2 + 5*x - 7"
               required>
        <div class="hint">تلميح: استخدم x**2 للأسس، sqrt(x) للجذر، pi لِـπ.</div>
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
    window.addEventListener('DOMContentLoaded', ()=>{ document.getElementById('query').focus(); });
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

# ===== كاش خفيف في الذاكرة (2 دقائق) =====
_cache = {}  # key -> (expires_ts, html_text)

def cache_get(key):
    v = _cache.get(key)
    if not v: return None
    exp, data = v
    if time.time() > exp:
        _cache.pop(key, None)
        return None
    return data

def cache_set(key, data, ttl=120):
    _cache[key] = (time.time() + ttl, data)

# ===== رياضيات (SymPy) =====
from sympy import (
    symbols, sympify, Eq, solveset, S, diff, integrate,
    sin, cos, tan, log, sqrt, pi, latex
)
X = symbols("x")
SAFE = {"x": X, "pi": pi, "sin": sin, "cos": cos, "tan": tan, "log": log, "sqrt": sqrt}

def pretty_solutions(solset):
    try:
        sols = list(solset)
    except Exception:
        sols = [solset]
    items = []
    for s in sols:
        try:
            approx = s.evalf(6)
            items.append(f"\\({latex(s)} \\approx {approx}\\)")
        except Exception:
            items.append(f"\\({latex(s)}\\)")
    return ", ".join(items) if items else "لا حلول"

def latex_eq(left, right):
    return latex(Eq(left, right))

def solve_math(query: str) -> str:
    key = ("math", query.strip())
    cached = cache_get(key)
    if cached: return cached

    q = query.strip()
    # حل معادلة: "حل ... = ..."
    m = re.search(r"حل\s+(.*)=(.*)", q)
    if m:
        left = sympify(m.group(1), locals=SAFE); right = sympify(m.group(2), locals=SAFE)
        sol = solveset(Eq(left, right), X, domain=S.Complexes)
        eq_ltx = latex_eq(left, right)
        sols_html = pretty_solutions(sol)
        out = f"<h2>📌 حل المعادلة</h2><div>\\[{eq_ltx}\\]</div><h3>الحل:</h3><div>{sols_html}</div>"
        cache_set(key, out); return out

    # مشتقة
    m = re.search(r"(اشتق|مشتقة)\s+(.*)", q)
    if m:
        expr = sympify(m.group(2), locals=SAFE); d = diff(expr, X)
        out = f"<h2>📌 المشتقة</h2><div>\\[f(x)={latex(expr)}\\]</div><h3>f'(x)</h3><div>\\[{latex(d)}\\]</div>"
        cache_set(key, out); return out

    # تكامل محدد
    m = re.search(r"تكامل\s+(.*)\s+من\s+(.*)\s+إلى\s+(.*)", q)
    if m:
        expr = sympify(m.group(1), locals=SAFE); a = sympify(m.group(2), locals=SAFE); b = sympify(m.group(3), locals=SAFE)
        val = integrate(expr, (X, a, b))
        out = f"<h2>📌 التكامل المحدد</h2><div>\\[\\int_{{{latex(a)}}}^{{{latex(b)}}} {latex(expr)}\\,dx = {latex(val)}\\]</div>"
        cache_set(key, out); return out

    # تكامل غير محدد (لو كتب فقط "تكامل <تعبير>")
    m = re.search(r"تكامل\s+(.*)", q)
    if m:
        expr = sympify(m.group(1), locals=SAFE); F = integrate(expr, X)
        out = f"<h2>📌 التكامل</h2><div>\\[\\int {latex(expr)}\\,dx = {latex(F)} + C\\]</div>"
        cache_set(key, out); return out

    # تبسيط/تقييم عام
    try:
        expr = sympify(q, locals=SAFE)
        out = f"<h2>📌 تبسيط/تقييم</h2><div>\\[{latex(expr.simplify())}\\]</div>"
        cache_set(key, out); return out
    except Exception as e:
        out = f"<h2>تعذر فهم المسألة</h2><pre>{html.escape(str(e))}</pre>"
        cache_set(key, out); return out

# ===== بحث وصور (DuckDuckGo) =====
try:
    from duckduckgo_search import DDGS
except Exception:
    DDGS = None

def do_web_search(q: str) -> str:
    key = ("web", q)
    cached = cache_get(key)
    if cached: return cached

    if DDGS is None:
        return "<h2>🔍 البحث غير مُفعل</h2><p>ثبّت duckduckgo_search.</p>"
    items = []
    with DDGS() as ddgs:
        for r in ddgs.text(q, max_results=6):
            href = r.get("href",""); title = r.get("title",""); body = r.get("body","")
            items.append(f'<li><a target="_blank" href="{html.escape(href)}">{html.escape(title)}</a><br><small>{html.escape(body)}</small></li>')
    out = "<h2>🔍 نتائج البحث</h2><ul class='result'>" + ("\n".join(items) or "<li>لا نتائج</li>") + "</ul>"
    cache_set(key, out)
    return out

def do_image_search(q: str) -> str:
    key = ("img", q)
    cached = cache_get(key)
    if cached: return cached

    if DDGS is None:
        return "<h2>🖼️ البحث عن الصور غير مُفعل</h2>"
    cards = []
    with DDGS() as ddgs:
        for r in ddgs.images(q, max_results=6, size="Medium", license_image="any"):
            src = r.get("image") or r.get("thumbnail")
            if src:
                cards.append(f"<img src='{html.escape(src)}' width='150' style='margin:6px;border-radius:8px'>")
    out = "<h2>🖼️ صور</h2>" + ("".join(cards) or "<p>لا توجد صور</p>")
    cache_set(key, out)
    return out

# ===== الذكاء الاصطناعي (Gemini) + Fallback مجاني =====
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

def simple_summarize(paragraphs, max_sent=6):
    text = " ".join(paragraphs)[:2000]
    sentences = re.split(r'(?<=[.!؟])\s+', text)
    return " ".join(sentences[:max_sent]) if sentences else text[:400]

def smart_fallback(q: str) -> str:
    if DDGS is None:
        return "<h2>🤖 الذكاء غير مفعّل</h2><p>أضف GEMINI_API_KEY أو فعّل duckduckgo_search.</p>"
    hits = []
    with DDGS() as ddgs:
        for r in ddgs.text(q, max_results=6):
            title = r.get("title",""); body = r.get("body","")
            if title or body: hits.append(f"{title}. {body}")
    summary = simple_summarize(hits, max_sent=6) or "لم أجد إجابة مؤكدة، جرّب إعادة الصياغة."
    return f"<h2>🤖 ملخص ذكي (وضع مجاني)</h2><div>{html.escape(summary)}</div>"

def do_smart(q: str) -> str:
    if gemini_ready:
        try:
            prompt = f"أنت بسام الذكي. جاوب بالعربية المبسطة، وبشكل منظم.\n\nسؤال المستخدم:\n{q}"
            resp = GEMINI_MODEL.generate_content(prompt)
            text = (getattr(resp, 'text', '') or '').strip()
            if not text:
                return smart_fallback(q)
            html_text = "<br>".join(html.escape(text).splitlines())
            return f"<h2>🤖 رد الذكاء الاصطناعي</h2><div>{html_text}</div>"
        except Exception:
            return smart_fallback(q)
    else:
        return smart_fallback(q)

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
    else:  # smart
        body = do_smart(q)
    return HTMLResponse(page_wrap(body, title="نتيجة بسام"))

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
