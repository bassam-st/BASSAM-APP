# main.py — Bassam AI v7 (Skills Router: Math/Physics/Chemistry/Electrical/Network + Smart + Search + Images)
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os, html

# استيراد المسجّل (الراوتر) الذي يختار المهارة الأنسب
from src.skills.registry import route_to_skill, is_mathy

app = FastAPI(title="Bassam AI v7")

# ملفات ثابتة (CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ========== واجهة HTML مع MathJax ==========
HOME_HTML = """
<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🤖 بسام الذكي v7</title>
<link rel="stylesheet" href="/static/styles.css">
<script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
<script id="MathJax-script" async
  src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

<div class="container">
  <div class="header">
    <h1>🤖 بسام الذكي v7</h1>
    <div class="sub">مهارات مجانية: رياضيات، فيزياء، كيمياء، كهرباء، شبكات — مع خطوات واضحة</div>
  </div>
  <div class="content">
    <form method="post" action="/search">
      <label>اكتب سؤالك أو مسألتك:</label>
      <input name="query" type="text" required
             placeholder="مثال: حل 2*x**2 - 3*x + 1 = 0 | اشتق x*sin(x) | تكامل cos(x) من 0 إلى pi | v=u+at: احسب v إذا u=5, a=2, t=3 | احسب الكتلة المولية لـ H2SO4 | CIDR 192.168.1.0/24">
      <div class="mode" id="modeBox">
        <label class="pill active"><input style="display:none" type="radio" name="mode" value="smart" checked>🤖 ذكي</label>
        <label class="pill"><input style="display:none" type="radio" name="mode" value="math">📊 رياضيات</label>
        <label class="pill"><input style="display:none" type="radio" name="mode" value="search">🔎 بحث</label>
        <label class="pill"><input style="display:none" type="radio" name="mode" value="images">🖼️ صور</label>
      </div>
      <button class="btn">🚀 ابدأ</button>
      <div class="hint">تلميح: استخدم <kbd>x**2</kbd> للأسس، <kbd>sqrt(x)</kbd> للجذر، <kbd>pi</kbd> لِـπ.</div>
    </form>
  </div>
  <div class="footer">BASSAM AI v7 — مجاني، وخفيف، وقابل للتوسّع</div>
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
<link rel="stylesheet" href="/static/styles.css">
<body class="body">
<div class="card">{inner}
<p style="margin-top:14px"><a href="/" class="back">⬅ الرجوع</a></p></div></body></html>"""

# ========== بحث/صور مجاني ==========
try:
    from duckduckgo_search import DDGS
except Exception:
    DDGS = None

def do_web_search(q: str) -> str:
    if DDGS is None:
        return "<h2>🔍 البحث غير مُفعل</h2><p>ثبّت duckduckgo_search.</p>"
    items = []
    with DDGS() as ddgs:
        for r in ddgs.text(q, max_results=8, region="xa-ar"):
            items.append(
                f"<li><a href='{html.escape(r.get('href',''))}' target='_blank'>"
                f"{html.escape(r.get('title',''))}</a><br><small>{html.escape(r.get('body',''))}</small></li>"
            )
    return "<h2>🔍 نتائج البحث</h2><ul class='result'>" + ("".join(items) or "<li>لا نتائج</li>") + "</ul>"

def _summarize_ar(text: str, max_sent=6) -> str:
    import re
    sents = re.split(r'(?<=[.!؟\?])\s+', text.strip())
    if not sents: return text
    words = re.findall(r'[\w\u0600-\u06FF]+', text.lower())
    stop = set(["في","من","على","عن","الى","إلى","أن","إن","كان","كانت","هذا","هذه","ذلك","هناك","هو","هي","ما","لم","لن","قد","ثم","كما","مع","كل","أي","أو","و","يا","لا","بل","بين","بعد","قبل","ولكن"])
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

def smart_summary(q: str) -> str:
    if DDGS is None:
        return "<h2>🤖 ملخص ذكي</h2><p>لم أجد مصادر كافية (محرك البحث غير مفعل).</p>"
    items = []
    with DDGS() as ddgs:
        for r in ddgs.text(q, max_results=10, region="xa-ar"):
            items.append(r)
    if not items:
        return "<h2>🤖 ملخص ذكي</h2><p>لا نتائج كافية.</p>"
    joined = ". ".join([(i.get("title","") + ": " + i.get("body","")) for i in items[:10]])
    summary = _summarize_ar(joined, max_sent=6)
    links = "".join(
        f"<li><a target='_blank' href='{html.escape(i.get('href',''))}'>{html.escape(i.get('title',''))}</a></li>"
        for i in items[:6]
    )
    return f"<h2>🤖 ملخص ذكي</h2><p>{html.escape(summary)}</p><h3>روابط مفيدة:</h3><ul class='result'>{links}</ul>"

def do_image_search(q: str) -> str:
    if DDGS is None:
        return "<h2>🖼️ البحث عن الصور غير مُفعل</h2>"
    imgs = []
    with DDGS() as ddgs:
        for r in ddgs.images(q, max_results=6, size="Medium", license_image="any"):
            src = r.get("image") or r.get("thumbnail")
            if src:
                imgs.append(f"<img src='{html.escape(src)}' width='180' class='thumb'>")
    return "<h2>🖼️ صور</h2>" + ("".join(imgs) or "<p>لا توجد صور</p>")

# ========== (اختياري) Gemini ==========
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

SMART_PROMPT = (
    "أنت بسام الذكي. جاوب بالعربية الواضحة، وبخطوات مختصرة ومنظمة حين تكون مسألة علمية."
)

def do_smart_ai(q: str) -> str:
    if not gemini_ready:
        return smart_summary(q)
    try:
        resp = GEMINI_MODEL.generate_content(
            f"{SMART_PROMPT}\n\nسؤال المستخدم:\n{q}",
            generation_config={"temperature":0.25,"max_output_tokens":900}
        )
        text = (resp.text or "").strip()
        if not text:
            return smart_summary(q)
        return "<h2>🤖 رد الذكاء الاصطناعي</h2><div>" + "<br>".join(html.escape(t) for t in text.splitlines()) + "</div>"
    except Exception:
        return smart_summary(q)

# ========== خط الأنابيب الذكي ==========
def answer_pipeline(q: str, mode: str) -> str:
    m = (mode or "smart").strip().lower()

    # 1) وضع المستخدم المباشر
    if m == "math" or (m == "smart" and is_mathy(q)):
        # رياضيات عبر مهارة الرياضيات أولًا
        res = route_to_skill(q, prefer="math")
        if res: return res
        # احتياط
        return smart_summary(q)

    if m == "search":
        return do_web_search(q)

    if m == "images":
        return do_image_search(q)

    # 2) وضع ذكي: جرّب المهارات (رياضيات/فيزياء/كيمياء/كهرباء/شبكات)
    res = route_to_skill(q)
    if res: 
        return res

    # 3) فشل تحديد مهارة → ملخص مجاني / أو Gemini إن متوفر
    return do_smart_ai(q)

# ========== المسارات ==========
@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(HOME_HTML)

@app.post("/search", response_class=HTMLResponse)
async def search(query: str = Form(...), mode: str = Form("smart")):
    q = (query or "").strip()
    body = answer_pipeline(q, mode)
    return HTMLResponse(page_wrap(body, title="نتيجة بسام"))

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
