# main.py — Bassam AI (Free: Math + Search Summarizer + Images) — Arabic UI

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import os, re, html, math
from typing import List, Tuple

app = FastAPI(title="Bassam AI")

# =========================
# واجهة رئيسية (HTML)
# =========================
HOME_HTML = """
<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🤖 بسام الذكي</title>
<style>
*{box-sizing:border-box} body{font-family:Segoe UI,Tahoma,Arial,sans-serif;background:#f5f7ff;margin:0}
.container{max-width:900px;margin:30px auto;background:#fff;border-radius:16px;box-shadow:0 12px 30px rgba(0,0,0,.08);overflow:hidden}
.header{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:28px 24px}
.header h1{margin:0 0 4px;font-size:28px}
.sub{opacity:.9}
.content{padding:22px}
label{font-weight:600;color:#222}
input[type=text]{width:100%;padding:14px;border:2px solid #e8ebf2;border-radius:12px;margin:8px 0 6px;font-size:16px}
.mode{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:12px 0 16px}
.mode label{display:flex;align-items:center;justify-content:center;gap:8px;border:2px solid #e8ebf2;border-radius:12px;padding:10px;cursor:pointer}
.mode .active{background:#667eea;color:#fff;border-color:#667eea}
.btn{width:100%;padding:14px;border:0;border-radius:12px;background:#4f46e5;color:#fff;font-weight:700;font-size:16px;cursor:pointer}
.hint{font-size:12px;color:#555}
.result a{color:#2563eb;text-decoration:none}
.result li{margin:8px 0}
.card{background:#fff;border-radius:14px;box-shadow:0 10px 28px rgba(0,0,0,.08);padding:20px}
img.thumb{border-radius:10px;display:block}
kbd{background:#eef;border-radius:6px;padding:2px 6px}
.footer{padding:14px 22px;border-top:1px solid #f0f2f7;color:#6b7280;text-align:center}
</style>
<div class="container">
  <div class="header">
    <h1>🤖 بسام الذكي</h1>
    <div class="sub">مساعد مجاني للرياضيات، والبحث، وتلخيص النتائج — بالعربية</div>
  </div>
  <div class="content">
    <form method="post" action="/search">
      <label>اكتب سؤالك أو مسألتك:</label>
      <input name="query" type="text" required placeholder="مثال: حل 2*x**2 + 3*x - 2 = 0 | اشتق x*sin(x) | تكامل cos(x) من 0 إلى pi | ما هو الذكاء الاصطناعي؟">
      <div class="hint">تلميح: استخدم <kbd>x**2</kbd> للأسس، <kbd>sqrt(x)</kbd> للجذر، <kbd>pi</kbd> لِـπ.</div>

      <div class="mode" id="modeBox">
        <label class="active"><input style="display:none" type="radio" name="mode" value="smart" checked>🤖 ذكي</label>
        <label><input style="display:none" type="radio" name="mode" value="math">📊 رياضيات</label>
        <label><input style="display:none" type="radio" name="mode" value="search">🔎 بحث</label>
        <label><input style="display:none" type="radio" name="mode" value="images">🖼️ صور</label>
      </div>
      <button class="btn">🚀 ابدأ</button>
    </form>
  </div>
  <div class="footer">BASSAM AI — مجاني وخفيف</div>
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
# 1) محرّك رياضيات (SymPy)
# =========================
from sympy import symbols, Eq, S, sympify, diff, integrate, solveset, Poly
from sympy import sin, cos, tan, log, sqrt, pi
from sympy.polys.polytools import factor
from sympy.core.numbers import Float

X = symbols("x")
SAFE = {"x": X, "pi": pi, "sin": sin, "cos": cos, "tan": tan, "log": log, "sqrt": sqrt}

def _pretty_roots(expr):
    """تحويل RootOf إلى جذور عددية (إن كان متعدد حدود) بدقة 6 منازل"""
    try:
        p = Poly(expr, X)
        vals = [complex(r) for r in p.nroots(n=50)]
        out = []
        for c in vals:
            if abs(c.imag) < 1e-12:
                out.append(f"{c.real:.6f}")
            else:
                out.append(f"{c.real:.6f} {'+' if c.imag>=0 else '-'} {abs(c.imag):.6f}i")
        return out
    except Exception:
        return None

def solve_math(query: str) -> str:
    q = (query or "").strip()
    # حل معادلة
    m = re.search(r"حل\s+(.*)=(.*)", q)
    if m:
        left = sympify(m.group(1), locals=SAFE); right = sympify(m.group(2), locals=SAFE)
        eq = Eq(left, right); sol = solveset(eq, X, domain=S.Complexes)
        # إن كان من نوع RootOf حوله أرقام:
        numeric = None
        if hasattr(sol, 'free_symbols') or str(sol).find('RootOf')>=0:
            numeric = _pretty_roots(left-right)
        body = f"<h2>📌 حل المعادلة</h2><p>{html.escape(str(eq))}</p>"
        body += "<h3>الحل (رمزي):</h3><pre>"+html.escape(str(sol))+"</pre>"
        if numeric:
            body += "<h3>تقريب عددي للجذور:</h3><ul>"+ "".join(f"<li>{r}</li>" for r in numeric) +"</ul>"
        return body

    # مشتقة
    m = re.search(r"(اشتق|مشتقة)\s+(.*)", q)
    if m:
        expr = sympify(m.group(2), locals=SAFE)
        d = diff(expr, X)
        return f"<h2>📌 المشتقة</h2><p>f(x)=<code>{html.escape(str(expr))}</code></p><h3>f'(x)=</h3><pre>{html.escape(str(d))}</pre>"

    # تكامل محدد
    m = re.search(r"تكامل\s+(.*)\s+من\s+(.*)\s+إلى\s+(.*)", q)
    if m:
        expr = sympify(m.group(1), locals=SAFE); a = sympify(m.group(2), locals=SAFE); b = sympify(m.group(3), locals=SAFE)
        val = integrate(expr, (X, a, b))
        return f"<h2>📌 التكامل المحدد</h2><p>∫<sub>{html.escape(str(a))}</sub><sup>{html.escape(str(b))}</sup> {html.escape(str(expr))} dx</p><h3>النتيجة:</h3><pre>{html.escape(str(val))}</pre>"

    # تكامل غير محدد
    m = re.search(r"تكامل\s+(.*)", q)
    if m:
        expr = sympify(m.group(1), locals=SAFE); F = integrate(expr, X)
        return f"<h2>📌 التكامل</h2><p>∫ {html.escape(str(expr))} dx</p><h3>النتيجة:</h3><pre>{html.escape(str(F))} + C</pre>"

    # تبسيط/تحليل
    if any(k in q for k in ["بسّط","بسط","simplify"]):
        expr = sympify(q.replace("بسّط","").replace("بسط","").replace("simplify","").strip(), locals=SAFE)
        return f"<h2>📌 تبسيط</h2><pre>{html.escape(str(expr.simplify()))}</pre>"

    if any(k in q for k in ["حلّل","حلل","factor"]):
        expr = sympify(q.replace("حلّل","").replace("حلل","").replace("factor","").strip(), locals=SAFE)
        return f"<h2>📌 تحليل</h2><pre>{html.escape(str(factor(expr)))}</pre>"

    # إذا لم تتطابق صيغة خاصة، حاول تقييم/تبسيط مباشر
    try:
        expr = sympify(q, locals=SAFE)
        return f"<h2>📌 تبسيط/تقييم</h2><pre>{html.escape(str(expr.simplify()))}</pre>"
    except Exception as e:
        return f"<h2>تعذر فهم المسألة</h2><pre>{html.escape(str(e))}</pre>"

# =========================
# 2) بحث وصور (DuckDuckGo) + مُلخِّص عربي مجاني
# =========================
try:
    from duckduckgo_search import DDGS
except Exception:
    DDGS = None

def _summarize_ar(text: str, max_sent=6) -> str:
    """مُلحّص خفيف: يختار أهم الجُمل حسب تكرار الكلمات (بدون مكتبات ثقيلة)."""
    import re
    sents = re.split(r'(?<=[.!؟\?])\s+', text.strip())
    if not sents: return text
    words = re.findall(r'[\w\u0600-\u06FF]+', text.lower())
    stop = set(["في","من","على","عن","الى","إلى","أن","إن","كان","كانت","هذا","هذه","ذلك","هناك","هو","هي","ما","لم","لن","قد","ثم","كما","مع","كل","أي","أو","و","يا","لا","بل","بين","بعد","قبل","على","هناك","هذه","وهذا","ولكن"])
    scores = {}
    for w in words:
        if w in stop: continue
        scores[w] = scores.get(w,0)+1
    def score_sent(s):
        ws = re.findall(r'[\w\u0600-\u06FF]+', s.lower())
        return sum(scores.get(w,0) for w in ws)/ (len(ws)+1)
    ranked = sorted(sents, key=score_sent, reverse=True)
    keep = sorted(ranked[:max_sent], key=lambda x: sents.index(x))
    return " ".join(keep)

def do_web_search(q: str) -> Tuple[str, List[dict]]:
    if DDGS is None:
        return "<h2>🔍 البحث غير مُفعل</h2><p>ثبّت duckduckgo-search.</p>", []
    items = []
    previews = []
    with DDGS() as ddgs:
        for r in ddgs.text(q, max_results=8, region="xa-ar"):
            items.append(r)
            previews.append(f'<li><a target="_blank" href="{html.escape(r.get("href",""))}">{html.escape(r.get("title",""))}</a><br><small>{html.escape(r.get("body",""))}</small></li>')
    body = "<h2>نتائج البحث 🔎</h2><ul class='result'>" + ("".join(previews) or "<li>لا نتائج</li>") + "</ul>"
    return body, items

def do_image_search(q: str) -> str:
    if DDGS is None:
        return "<h2>🖼️ البحث عن الصور غير مُفعل</h2>"
    cards = []
    with DDGS() as ddgs:
        for r in ddgs.images(q, max_results=8, size="Medium", license_image="any"):
            src = r.get("image") or r.get("thumbnail"); title = r.get("title","")
            if src:
                cards.append(f"<div style='display:inline-block;margin:6px'><img class='thumb' src='{html.escape(src)}' width='180'><small>{html.escape(title)}</small></div>")
    return "<h2>🖼️ صور</h2>" + ("".join(cards) or "<p>لا توجد صور</p>")

def do_smart_free(q: str) -> str:
    """مسار ذكي مجاني:
       1) حاول رياضيات
       2) ابحث في الويب + لخّص عربياً
    """
    # 1) محاولة رياضيات إن كانت العبارة رياضية واضحة
    if any(t in q for t in ["حل","تكامل","اشتق","مشتقة","factor","بسّط","بسط","=","sin","cos","tan","sqrt","**","log","pi"]):
        math_html = solve_math(q)
        # إن ظهر فشل واضح، كمل للبحث
        if "تعذر" not in math_html:
            return math_html

    # 2) بحث + تلخيص
    results_html, items = do_web_search(q)
    if not items:
        return "<h2>🤖 ملخص ذكي (وضع مجاني)</h2><p>لم أجد إجابة مؤكدة؛ جرّب إعادة الصياغة.</p><h3>روابط ذات صلة:</h3><p>لا روابط كافية</p>"
    # جمع نصوص قصيرة للتلخيص
    joined = ". ".join([i.get("title","")+": "+i.get("body","") for i in items[:10]])
    summary = _summarize_ar(joined, max_sent=6)
    return f"<h2>🤖 ملخص ذكي (مجاني)</h2><p>{html.escape(summary)}</p><h3>روابط مفيدة:</h3>" + results_html

# =========================
# (اختياري) Gemini إذا كان المفتاح موجوداً
# =========================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_gemini_ready = False
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _G_MODEL = genai.GenerativeModel("gemini-1.5-flash")
        _gemini_ready = True
    except Exception:
        _gemini_ready = False

SMART_PROMPT = (
    "أنت بسام الذكي. جاوب بالعربية الواضحة، نقاط موجزة عند الحاجة، "
    "واستخدم أمثلة سريعة. إن كان السؤال رياضيًا قدّم خطوات مختصرة للحل."
)

def do_smart(q: str) -> str:
    if not _gemini_ready:
        # الوضع المجاني الذكي
        return do_smart_free(q)
    try:
        prompt = f"{SMART_PROMPT}\n\nسؤال المستخدم:\n{q}"
        resp = _G_MODEL.generate_content(prompt, generation_config={"temperature":0.3,"max_output_tokens":900})
        text = (resp.text or "").strip()
        if not text:
            return do_smart_free(q)
        html_text = "<br>".join(html.escape(text).splitlines())
        return f"<h2>🤖 رد الذكاء الاصطناعي</h2><div>{html_text}</div>"
    except Exception:
        # إن تعطل Gemini نرجع للمجاني
        return do_smart_free(q)

# =========================
# المسارات
# =========================
@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(HOME_HTML)

@app.post("/search", response_class=HTMLResponse)
async def search(query: str = Form(...), mode: str = Form("smart")):
    q = (query or "").strip()
    m = (mode or "smart").strip().lower()
    if m == "math":
        body = solve_math(q)
    elif m == "search":
        body, _ = do_web_search(q)
    elif m == "images":
        body = do_image_search(q)
    else:
        body = do_smart(q)   # ذكي: رياضيات → بحث+تلخيص، ومع مفتاح Gemini يستخدمه تلقائيًا
    return HTMLResponse(page_wrap(body, title="نتيجة بسام"))

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
