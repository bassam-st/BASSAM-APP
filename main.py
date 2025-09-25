# main.py — Bassam AI (Math + Search + Images + Gemini Smart)

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import html, re, os

# ===== واجهة =====
app = FastAPI(title="Bassam AI")

# ---------------- (ضع هنا HOME_HTML كما هو عندك) ----------------
# ... نفس HOME_HTML السابق بدون تغيير ...
# ----------------------------------------------------------------

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
        # تنسيق أسطر بسيطة
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
    else:  # smart
        body = do_smart(q)
    return HTMLResponse(page_wrap(body, title="نتيجة بسام"))

@app.get("/upload", response_class=HTMLResponse)
async def upload_page():
    return HTMLResponse(page_wrap("<h2>📷 رفع صورة</h2><p>ميزة قيد التطوير.</p>", title="رفع صورة"))

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
