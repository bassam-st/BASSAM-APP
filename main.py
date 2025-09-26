# main.py — Bassam AI (Modular) — يستخدم محركات مجلد core/
# - عرض رياضي جميل بـ MathJax
# - محرك الرياضيات من core.math_engine
# - الذكاء الاصطناعي من core.ai_engine (Gemini) + Fallback مجاني
# - بحث وصور (DDG) + كاش خفيف

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import html, os, re, time

# ===== تطبيق FastAPI =====
app = FastAPI(title="Bassam AI")

# ===== استيراد محركاتك من core/ =====
# math_engine: يحتوي الدالة solve_math_problem(query) التي تعيد dict منسّق
# ai_engine: يحتوي الكائن ai_engine وفيه answer_question() و generate_response()
try:
    from core.math_engine import math_engine
except Exception as e:
    math_engine = None
    print(f"⚠️ لم أستطع استيراد core.math_engine: {e}")

try:
    from core.ai_engine import ai_engine
except Exception as e:
    ai_engine = None
    print(f"⚠️ لم أستطع استيراد core.ai_engine: {e}")

# ===== SymPy (لصياغة LaTeX عند الحاجة) =====
from sympy import sympify, latex

# ===== DuckDuckGo =====
try:
    from duckduckgo_search import DDGS
except Exception:
    DDGS = None

# ===== كاش خفيف داخل الذاكرة =====
_cache = {}  # key -> (expires_ts, html)

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

# ===== الصفحة الرئيسية (مع MathJax) =====
HOME_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🤖 بسام الذكي - BASSAM AI APP</title>

  <!-- MathJax لعرض الرياضيات -->
  <script>
    window.MathJax = { tex: { inlineMath: [['$', '$'], ['\\\\(', '\\\\)']] } };
  </script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

  <style>
    body{font-family:'Segoe UI',Tahoma,Arial,sans-serif;background:#f1f5f9;direction:rtl;padding:20px}
    .card{max-width:840px;margin:auto;background:#fff;padding:22px;border-radius:16px;box-shadow:0 10px 30px rgba(0,0,0,.08)}
    .header{text-align:center;margin-bottom:16px}
    .header h1{margin:0 0 6px}
    .form-group{margin-bottom:12px}
    input[type="text"]{width:100%;padding:12px;border:1px solid #e5e7eb;border-radius:10px;font-size:16px}
    .hint{color:#666;font-size:12px;margin-top:6px}
    .modes{display:flex;gap:8px;margin:12px 0}
    .modes label{flex:1;padding:10px;border:1px solid #e5e7eb;border-radius:10px;text-align:center;cursor:pointer}
    .modes label.active{background:#4f46e5;color:#fff;border-color:#4f46e5}
    .submit{width:100%;padding:14px;background:#4f46e5;color:#fff;border:none;border-radius:10px;font-size:16px;cursor:pointer}
    .result a{color:#2563eb;text-decoration:none}
    .result li{margin:6px 0}
  </style>
</head>
<body>
  <div class="card">
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

      <div class="modes">
        <label class="active"><input type="radio" name="mode" value="smart" hidden checked>🤖 ذكي</label>
        <label><input type="radio" name="mode" value="search" hidden>🔍 بحث</label>
        <label><input type="radio" name="mode" value="math" hidden>📊 رياضيات</label>
        <label><input type="radio" name="mode" value="images" hidden>🖼️ صور</label>
      </div>

      <button type="submit" class="submit">🚀 ابدأ</button>
    </form>
  </div>

  <script>
    document.querySelectorAll('.modes label').forEach(btn=>{
      btn.addEventListener('click', ()=>{
        document.querySelectorAll('.modes label').forEach(b=>b.classList.remove('active'));
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

# ================================
# أدوات تنسيق نتائج الرياضيات
# ================================
def _to_latex_safe(txt: str) -> str:
    """يحاول تحويل string إلى LaTeX؛ وإن فشل يعرضه كنص."""
    try:
        expr = sympify(txt)
        return f"\\[{latex(expr)}\\]"
    except Exception:
        return f"<pre>{html.escape(txt)}</pre>"

def render_math_result(res: dict) -> str:
    """يحوّل dict القادم من core.math_engine إلى HTML أنيق مع MathJax."""
    if not isinstance(res, dict):
        return "<h2>⚠️ نتيجة غير مفهومة من محرك الرياضيات</h2>"

    op = res.get("operation", "نتيجة رياضية")
    parts = [f"<h2>📌 {html.escape(op)}</h2>"]

    # معادلة
    if "equation" in res:
        parts.append(_to_latex_safe(res["equation"]))

    # التعبير/المتحول
    if "expression" in res:
        parts.append(_to_latex_safe(res["expression"]))

    # مشتقة/تكامل/تبسيط …
    if "derivative" in res:
        parts.append(f"<h3>المشتقة:</h3>{_to_latex_safe(res['derivative'])}")
    if "integral" in res:
        parts.append(f"<h3>التكامل:</h3>{_to_latex_safe(res['integral'])}")
    if "definite_integral" in res:
        parts.append(f"<h3>قيمة التكامل المحدد:</h3><pre>{html.escape(str(res['definite_integral']))}</pre>")
    if "simplified" in res:
        parts.append(f"<h3>بعد التبسيط:</h3>{_to_latex_safe(res['simplified'])}")
    if "factored" in res:
        parts.append(f"<h3>بعد التحليل:</h3>{_to_latex_safe(res['factored'])}")

    # حلول
    sols = res.get("solutions")
    if sols:
        items = []
        for s in sols:
            items.append(_to_latex_safe(s))
        parts.append("<h3>الحلول:</h3>" + "<div>" + "".join(items) + "</div>")

    # خطوات
    steps = res.get("steps", [])
    if steps:
        parts.append("<h3>الخطوات:</h3><ol>" + "".join([f"<li>{html.escape(step.get('text',''))}</li>" for step in steps]) + "</ol>")

    # قيَم عند نقطة
    if "value" in res:
        parts.append(f"<h3>القيمة:</h3><pre>{html.escape(str(res['value']))}</pre>")
    if "derivative_value" in res:
        parts.append(f"<h3>قيمة المشتقة عند النقطة:</h3><pre>{html.escape(str(res['derivative_value']))}</pre>")

    # أخطاء
    if res.get("success") is False or res.get("error"):
        parts.append(f"<h3>خطأ:</h3><pre>{html.escape(str(res.get('error')))}</pre>")

    return "".join(parts)

# ================================
# البحث والذكاء الاصطناعي
# ================================
def do_web_search(q: str) -> str:
    key = ("web", q); cached = cache_get(key)
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
    key = ("img", q); cached = cache_get(key)
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
    """يفضّل ai_engine (Gemini) إن توفر، وإلا يستخدم fallback المجاني."""
    # 1) جرّب ai_engine من core/ لو متاح وفعّال
    if ai_engine and getattr(ai_engine, "is_gemini_available", None):
        try:
            if ai_engine.is_gemini_available():
                data = ai_engine.answer_question(q)  # يعيد dict
                if data and data.get("answer"):
                    ans = html.escape(data["answer"]).replace("\n", "<br>")
                    return f"<h2>🤖 رد الذكاء الاصطناعي</h2><div>{ans}</div>"
        except Exception as e:
            print(f"⚠️ ai_engine فشل: {e}")

    # 2) إن لم يتوفر، استخدم fallback المجاني (بحث + تلخيص)
    return smart_fallback(q)

# ================================
# المسارات
# ================================
@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(HOME_HTML)

@app.post("/search", response_class=HTMLResponse)
async def search(query: str = Form(...), mode: str = Form("smart")):
    q = (query or "").strip()
    m = (mode or "smart").strip().lower()

    if m == "math":
        if not math_engine:
            body = "<h2>⚠️ محرك الرياضيات غير متوفر</h2>"
        else:
            try:
                res = math_engine.solve_math_problem(q)  # dict
                body = render_math_result(res)
            except Exception as e:
                body = f"<h2>خطأ في محرك الرياضيات</h2><pre>{html.escape(str(e))}</pre>"
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
    # ===== طبقات الإجابة (Fallback Pipeline) =====

def _is_good_math_result(res: dict) -> bool:
    """
    يقرّر بسرعة إذا نتيجة الرياضيات مفيدة:
    - فيها حلول/تكامل/مشتقة/تبسيط واضحة
    - ما هي مجرد رسالة خطأ
    """
    if not isinstance(res, dict):
        return False
    if res.get("success") is False or res.get("error"):
        return False
    # أي مفتاح ناتج مفيد:
    useful_keys = {"solutions", "integral", "definite_integral", "derivative", "simplified", "factored", "value"}
    return any(k in res and res[k] not in (None, "", []) for k in useful_keys)

def try_math_first(q: str) -> str | None:
    """يحاول حل المسألة رياضيًا عبر core.math_engine ثم يُرجع HTML إذا مفيد."""
    if not math_engine:
        return None
    try:
        res = math_engine.solve_math_problem(q)  # dict
        if _is_good_math_result(res):
            return render_math_result(res)  # HTML
    except Exception as e:
        print("Math engine error:", e)
    return None


def try_ai_second(q: str) -> str | None:
    """
    يحاول الذكاء الاصطناعي:
    - لو ai_engine موجود ومفعّل → يستخدمه
    - لو مو متوفر → يرجع None عشان ننتقل للبحث
    """
    if ai_engine and getattr(ai_engine, "is_gemini_available", None):
        try:
            if ai_engine.is_gemini_available():
                data = ai_engine.answer_question(q)  # {'answer': ...}
                if data and data.get("answer"):
                    ans = html.escape(data["answer"]).replace("\n", "<br>")
                    return f"<h2>🤖 رد الذكاء الاصطناعي</h2><div>{ans}</div>"
        except Exception as e:
            print("AI engine error:", e)
    return None


def try_web_third(q: str) -> str:
    """بحث ويب + تلخيص كـ 'ذكاء اصطناعي مجاني'."""
    if DDGS is None:
        return "<h2>🔍 البحث غير مُفعل</h2><p>ثبّت duckduckgo_search في requirements.txt</p>"

    # اجلب نتائج نصية مختصرة
    hits = []
    links_html = []
    with DDGS() as ddgs:
        for r in ddgs.text(q, max_results=6):
            title = r.get("title", "") or "نتيجة"
            body = r.get("body", "")
            href = r.get("href", "")
            if title or body:
                hits.append(f"{title}. {body}")
            if href:
                links_html.append(f'<li><a target="_blank" href="{html.escape(href)}">{html.escape(title)}</a></li>')

    # لخّص سطور النتائج (ملخّص بسيط)
    summary = simple_summarize(hits, max_sent=6) or "لم أجد إجابة مؤكدة، جرّب إعادة الصياغة أو كلمات مفتاحية أخرى."
    links_block = "<ul class='result'>" + "".join(links_html) + "</ul>" if links_html else ""

    return f"""
    <h2>🤖 ملخص ذكي (وضع مجاني)</h2>
    <div>{html.escape(summary)}</div>
    <h3>روابط ذات صلة:</h3>
    {links_block if links_block else "<p>لا روابط كافية</p>"}
    """


def answer_pipeline(q: str, mode: str) -> str:
    """
    الاستراتيجية المطلوبة:
      - لو وضع Math → Math → AI → Web
      - لو وضع Smart → AI → Web (وممكن Math إذا السؤال واضح أنه رياضي)
      - لو وضع Search/Images تبقى وظائفها كما هي
    """
    m = (mode or "smart").strip().lower()

    # Math mode صريح
    if m == "math":
        html_math = try_math_first(q)
        if html_math: return html_math
        html_ai = try_ai_second(q)
        if html_ai: return html_ai
        return try_web_third(q)

    # Smart mode: أولًا AI، ولو باين سؤال رياضي جرّب Math قبل/بعد
    if m == "smart":
        # heuristic بسيط: لو فيه كلمات رياضيات جرّب Math أول
        if re.search(r"(حل|تكامل|اشتق|مشتق|معادلة|^f\(x\)|\=|\*\*|sqrt|sin|cos|tan|log|ln)", q):
            html_math = try_math_first(q)
            if html_math: return html_math

        html_ai = try_ai_second(q)
        if html_ai: return html_ai

        # لو الذكاء مو متاح → أرجع للبحث + تلخيص
        return try_web_third(q)

    # Search / Images: نستخدم الدوال الأصلية
    if m == "search":
        return do_web_search(q)
    if m == "images":
        return do_image_search(q)

    # افتراضيًا:
    return try_web_third(q)
