from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, Response
import httpx, re, ast, math, os, psycopg2, html, csv, io
from datetime import datetime

# بحث جاهز بدون سكربنج HTML
from duckduckgo_search import DDGS

# ==== إعدادات FastAPI ====
app = FastAPI(title="Bassam App", version="3.1")

# ===================== قاعدة البيانات (PostgreSQL) =====================
def get_db_connection():
    # يتطلب وجود DATABASE_URL في بيئة Replit (يظهر لك في تبويب Database)
    return psycopg2.connect(os.environ["DATABASE_URL"])

def init_db_pg():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS question_history(
                        id SERIAL PRIMARY KEY,
                        question TEXT NOT NULL,
                        answer   TEXT NOT NULL,
                        mode     TEXT NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                """)
                conn.commit()
    except Exception as e:
        print("DB init error:", e)

@app.on_event("startup")
def _startup():
    init_db_pg()

def save_question_history(question: str, answer: str, mode: str = "summary"):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO question_history (question, answer, mode) VALUES (%s,%s,%s)",
                    (question, answer, mode)
                )
                conn.commit()
    except Exception as e:
        print("save_history error:", e)

def get_question_history(limit: int = 50):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, question, answer, mode, created_at
                    FROM question_history
                    ORDER BY id DESC
                    LIMIT %s
                """, (limit,))
                return cur.fetchall()
    except Exception as e:
        print("get_history error:", e)
        return []

# ===================== أدوات عامة =====================
AR_NUM = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
def _to_float(s: str):
    s = (s or "").strip().translate(AR_NUM).replace(",", "")
    try: return float(s)
    except: return None

# ===================== 1) آلة حاسبة موسعة =====================
REPL = {"÷":"/","×":"*","−":"-","–":"-","—":"-","^":"**","أس":"**","اس":"**","جذر":"sqrt","الجذر":"sqrt","√":"sqrt","%":"/100"}
def _normalize_expr(s: str) -> str:
    s = (s or "").strip()
    for k, v in REPL.items(): s = s.replace(k, v)
    s = s.replace("على","/").replace("في","*").translate(AR_NUM)
    return s.replace("٬","").replace(",","")

_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.USub, ast.UAdd,
    ast.Call, ast.Load, ast.Name, ast.FloorDiv
)
SAFE_FUNCS = {
    "sqrt": math.sqrt,
    "sin": lambda x: math.sin(math.radians(x)),
    "cos": lambda x: math.cos(math.radians(x)),
    "tan": lambda x: math.tan(math.radians(x)),
    "log": lambda x, base=10: math.log(x, base),
    "ln": math.log,
    "exp": math.exp,
}
def _safe_eval(expr: str) -> float:
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES): raise ValueError("رموز غير مدعومة")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_FUNCS:
                raise ValueError("دالة غير مسموحة")
        if isinstance(node, ast.Name) and node.id not in SAFE_FUNCS:
            raise ValueError("اسم غير مسموح")
    return eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}}, SAFE_FUNCS)

def _analyze_expression(original: str, expr: str, final_result: float):
    safe_original = html.escape(original)
    steps_html = f'<div class="card"><h4>📐 المسألة: {safe_original}</h4><hr><h5>🔍 الحل:</h5>'
    import re
    step = 1
    current_expr = expr

    for pattern, func_name, func in [
        (r'sin\(([^)]+)\)','sin',lambda x: math.sin(math.radians(x))),
        (r'cos\(([^)]+)\)','cos',lambda x: math.cos(math.radians(x))),
        (r'tan\(([^)]+)\)','tan',lambda x: math.tan(math.radians(x))),
        (r'sqrt\(([^)]+)\)','sqrt',math.sqrt),
        (r'ln\(([^)]+)\)','ln',math.log),
        (r'log\(([^)]+)\)','log',lambda x: math.log(x,10)),
    ]:
        for m in list(re.finditer(pattern, current_expr)):
            try:
                v = float(m.group(1)); r = func(v)
                steps_html += f'<p><strong>{step}.</strong> {func_name}({v}) = <span style="color:#2196F3">{r:.4f}</span></p>'
                current_expr = current_expr.replace(m.group(0), str(r)); step += 1
            except: pass

    steps_html += f'<hr><h4 style="color:#4facfe;text-align:center;">🎯 النتيجة: <span style="font-size:1.3em;">{final_result:.6g}</span></h4></div>'
    return steps_html

def try_calc_ar(question: str):
    if not question: return None
    has_digit = any(ch.isdigit() for ch in question.translate(AR_NUM))
    has_func  = any(f in question.lower() for f in ["sin","cos","tan","log","ln","sqrt","جذر"])
    has_op    = any(op in question for op in ["+","-","×","÷","*","/","^","أس","√","(",")","%"])
    if not (has_digit and (has_op or has_func)): return None
    expr = _normalize_expr(question)
    try:
        res = _safe_eval(expr)
        return {"text": f"النتيجة النهائية: {res}", "html": _analyze_expression(question, expr, res)}
    except: 
        return None

# ===================== 2) محولات وحدات =====================
WEIGHT_ALIASES = {"كيلو":"kg","كيلوجرام":"kg","كجم":"kg","كغ":"kg","kg":"kg","جرام":"g","غ":"g","g":"g","ملغم":"mg","mg":"mg","رطل":"lb","باوند":"lb","lb":"lb","أوقية":"oz","اونصة":"oz","oz":"oz","طن":"t","t":"t"}
W_TO_KG = {"kg":1.0,"g":0.001,"mg":1e-6,"lb":0.45359237,"oz":0.028349523125,"t":1000.0}
LENGTH_ALIASES = {"مم":"mm","mm":"mm","سم":"cm","cm":"cm","م":"m","متر":"m","m":"m","كم":"km","km":"km","إنش":"in","بوصة":"in","in":"in","قدم":"ft","ft":"ft","ياردة":"yd","yd":"yd","ميل":"mi","mi":"mi"}
L_TO_M = {"mm":0.001,"cm":0.01,"m":1.0,"km":1000.0,"in":0.0254,"ft":0.3048,"yd":0.9144,"mi":1609.344}
VOLUME_ALIASES = {"مل":"ml","ml":"ml","ل":"l","لتر":"l","l":"l","كوب":"cup","cup":"cup","ملعقة":"tbsp","tbsp":"tbsp","ملعقة صغيرة":"tsp","tsp":"tsp","غالون":"gal","gal":"gal"}
V_TO_L = {"ml":0.001,"l":1.0,"cup":0.236588,"tbsp":0.0147868,"tsp":0.0049289,"gal":3.78541}
AREA_ALIASES = {"م2":"m2","متر مربع":"m2","cm2":"cm2","سم2":"cm2","km2":"km2","كم2":"km2","ft2":"ft2","قدم2":"ft2","in2":"in2","إنش2":"in2","ha":"ha","هكتار":"ha","mi2":"mi2","ميل2":"mi2"}
A_TO_M2 = {"m2":1.0,"cm2":0.0001,"km2":1_000_000.0,"ft2":0.092903,"in2":0.00064516,"ha":10_000.0,"mi2":2_589_988.11}
VOLUME3_ALIASES = {"م3":"m3","متر مكعب":"m3","cm3":"cm3","سم3":"cm3","l":"l","ل":"l","ml":"ml","مل":"ml","ft3":"ft3","قدم3":"ft3","in3":"in3","إنش3":"in3","gal":"gal","غالون":"gal"}
V3_TO_M3 = {"m3":1.0,"cm3":1e-6,"l":0.001,"ml":1e-6,"ft3":0.0283168,"in3":1.6387e-5,"gal":0.00378541}
ALL_ALIASES = {**WEIGHT_ALIASES,**LENGTH_ALIASES,**VOLUME_ALIASES,**AREA_ALIASES,**VOLUME3_ALIASES}
TYPE_OF_UNIT = {}
for k,v in WEIGHT_ALIASES.items(): TYPE_OF_UNIT[v]="W"
for k,v in LENGTH_ALIASES.items(): TYPE_OF_UNIT[v]="L"
for k,v in VOLUME_ALIASES.items(): TYPE_OF_UNIT[v]="Vs"
for k,v in AREA_ALIASES.items(): TYPE_OF_UNIT[v]="A"
for k,v in VOLUME3_ALIASES.items(): TYPE_OF_UNIT[v]="V3"
CONV_RE = re.compile(r'(?:كم\s*يساوي\s*)?([\d\.,]+)\s*(\S+)\s*(?:إلى|ل|=|يساوي|بال|بـ)\s*(\S+)', re.IGNORECASE)
def _norm_unit(u: str): return ALL_ALIASES.get((u or "").strip().lower().translate(AR_NUM), "")
def convert_query_ar(query: str):
    m = CONV_RE.search((query or "").strip())
    if not m: return None
    val_s,u_from_s,u_to_s = m.groups()
    value=_to_float(val_s); u_from=_norm_unit(u_from_s); u_to=_norm_unit(u_to_s)
    if value is None or not u_from or not u_to: return None
    t_from=TYPE_OF_UNIT.get(u_from); t_to=TYPE_OF_UNIT.get(u_to)
    if not t_from or t_from!=t_to: return None
    if t_from=="W": res=(value*W_TO_KG[u_from])/W_TO_KG[u_to]
    elif t_from=="L": res=(value*L_TO_M[u_from])/L_TO_M[u_to]
    elif t_from=="Vs": res=(value*V_TO_L[u_from])/V_TO_L[u_to]
    elif t_from=="A": res=(value*A_TO_M2[u_from])/A_TO_M2[u_to]
    elif t_from=="V3": res=(value*V3_TO_M3[u_from])/V3_TO_M3[u_to]
    else: return None
    text=f"{value:g} {u_from_s} ≈ {res:,.6f} {u_to_s}"
    html_out=f'<div class="card"><strong>النتيجة:</strong> {html.escape(text)}</div>'
    return {"text":text,"html":html_out}

# ===================== 3) التلخيص =====================
try:
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.parsers.plaintext import PlainTextParser
    from sumy.summarizers.text_rank import TextRankSummarizer
    from rank_bm25 import BM25Okapi
    from rapidfuzz import fuzz
    import numpy as np
    SUMY_AVAILABLE = True
except Exception:
    SUMY_AVAILABLE = False

AR_SPLIT_RE = re.compile(r'(?<=[\.\!\?\؟])\s+|\n+')
def _sent_tokenize_ar(text: str):
    sents = [s.strip() for s in AR_SPLIT_RE.split(text or "") if len(s.strip())>0]
    return [s for s in sents if len(s)>=20]

def summarize_advanced(question: str, page_texts: list, max_final_sents=4):
    # تبسيط: لو SUMY غير مثبتة، خذ أفضل الجُمل المتاحة فقط
    candidate_sents = []
    for t in page_texts:
        candidate_sents.extend(_sent_tokenize_ar(t)[:200])
    if not candidate_sents: return ""
    if not SUMY_AVAILABLE:
        return " ".join(candidate_sents[:max_final_sents])

    def tok(s):
        s = s.lower()
        s = re.sub(r"[^\w\s\u0600-\u06FF]+"," ", s)
        return s.split()
    import numpy as np
    from rank_bm25 import BM25Okapi
    bm25 = BM25Okapi([tok(s) for s in candidate_sents])
    idx = np.argsort(bm25.get_scores(tok(question)))[::-1][:12]
    chosen = [candidate_sents[i] for i in idx]
    from sumy.parsers.plaintext import PlainTextParser
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.summarizers.text_rank import TextRankSummarizer
    parser = PlainTextParser.from_string(" ".join(chosen), Tokenizer("english"))
    summ = TextRankSummarizer()
    out = " ".join(str(s) for s in summ(parser.document, max_final_sents)).strip()
    return out or " ".join(chosen[:max_final_sents])

# ===================== 4) HTML (واجهة) =====================
def render_page(q="", mode="summary", result_panel=""):
    active = lambda m: "active" if mode==m else ""
    checked= lambda m: "checked" if mode==m else ""
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🤖 تطبيق بسام</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Tahoma,Arial;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:20px;direction:rtl}}
.container{{max-width:800px;margin:0 auto;background:#fff;border-radius:15px;box-shadow:0 10px 30px rgba(0,0,0,.1);overflow:hidden}}
.header{{background:linear-gradient(135deg,#4facfe 0%,#00f2fe 100%);color:#fff;padding:30px;text-align:center;position:relative}}
.history-btn{{position:absolute;top:20px;left:20px;padding:10px 20px;background:rgba(255,255,255,.2);color:#fff;text-decoration:none;border-radius:25px;border:2px solid rgba(255,255,255,.3)}}
.content{{padding:30px}}
input[type=text]{{width:100%;padding:15px;border:2px solid #e1e5e9;border-radius:10px;font-size:16px}}
.mode-selector{{display:flex;gap:10px;margin:20px 0;flex-wrap:wrap}}
.mode-btn{{flex:1;min-width:120px;padding:12px 20px;border:2px solid #e1e5e9;background:#fff;border-radius:8px;cursor:pointer;text-align:center;font-weight:bold}}
.mode-btn.active{{background:#4facfe;color:#fff;border-color:#4facfe}}
.submit-btn{{width:100%;padding:15px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff;border:none;border-radius:10px;font-size:18px;font-weight:bold;cursor:pointer}}
.result{{margin-top:30px;padding:20px;background:#f8f9fa;border-radius:10px;border-right:4px solid #4facfe}}
.card{{background:#fff;padding:20px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.1);margin:10px 0}}
.footer{{text-align:center;padding:20px;color:#666;border-top:1px solid #eee}}
</style></head>
<body>
<div class="container">
  <div class="header">
    <a href="/history" class="history-btn">📚 السجل</a>
    <h1>🤖 تطبيق بسام</h1><p>آلة حاسبة، محول وحدات، وبحث ذكي</p>
  </div>
  <div class="content">
    <form method="post" action="/">
      <label for="question">اسأل بسام:</label>
      <input type="text" id="question" name="question" placeholder="مثال: 5 + 3 × 2 / تحويل 70 كيلو إلى رطل / أين تقع الصين؟" value="{html.escape(q)}" required>
      <div class="mode-selector">
        <label class="mode-btn {active('summary')}"><input type="radio" name="mode" value="summary" {checked('summary')} style="display:none">📄 ملخص</label>
        <label class="mode-btn {active('prices')}"><input type="radio" name="mode" value="prices"  {checked('prices')}  style="display:none">💰 أسعار</label>
        <label class="mode-btn {active('images')}"><input type="radio" name="mode" value="images"  {checked('images')}  style="display:none">🖼️ صور</label>
      </div>
      <button type="submit" class="submit-btn">🔍 ابحث</button>
    </form>
    {f'<div class="result"><h3>النتيجة:</h3>{result_panel}</div>' if result_panel else ''}
  </div>
  <div class="footer"><p>تطبيق بسام v3.1</p></div>
</div>
<script>
document.querySelectorAll('.mode-btn').forEach(btn=>{btn.addEventListener('click',()=>{document.querySelectorAll('.mode-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');btn.querySelector('input').checked=true;});});
document.getElementById('question').focus();
</script>
</body></html>"""

# ===================== المسارات =====================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    q = request.query_params.get("q", "")
    mode = request.query_params.get("mode", "summary")
    return render_page(q, mode)

@app.post("/", response_class=HTMLResponse)
async def run(question: str = Form(...), mode: str = Form("summary")):
    q = (question or "").strip()
    if not q: return render_page()

    # 1) آلة حاسبة
    calc = try_calc_ar(q)
    if calc:
        save_question_history(q, calc["text"], "calculator")
        return render_page(q, mode, calc["html"])

    # 2) تحويل وحدات
    conv = convert_query_ar(q)
    if conv:
        save_question_history(q, conv["text"], "converter")
        return render_page(q, mode, conv["html"])

    # 3) بحث/أسعار/صور (DuckDuckGo API)
    try:
        results = []
        async with DDGS() as ddgs:
            for r in ddgs.text(q, region="xa-ar", safesearch="moderate", max_results=12):
                results.append(r)

        snippets = [re.sub(r"\s+", " ", (r.get("body") or "")) for r in results]
        links    = [r.get("href") for r in results]

        if mode == "summary":
            texts = [s for s in snippets if s][:5]
            final_answer = summarize_advanced(q, texts, max_final_sents=4) or \
                           (" ".join(texts[:3]) if texts else "لم أجد ملخصًا.")
            panel = f'<div class="card">{html.escape(final_answer)}</div>'
            save_question_history(q, final_answer, "summary")
            return render_page(q, mode, panel)

        elif mode == "prices":
            parts = []
            for s, a in zip(snippets, links):
                if any(x in s for x in ["$", "USD", "SAR", "ر.س", "AED", "د.إ", "EGP", "ج.م", "ريال", "درهم", "جنيه"]):
                    link = f'<a target="_blank" href="{html.escape(a or "#")}">فتح المصدر</a>'
                    parts.append(f'<div class="card">{html.escape(s)} — {link}</div>')
                if len(parts) >= 8: break
            panel = "".join(parts) if parts else '<div class="card">لم أجد أسعارًا واضحة.</div>'
            save_question_history(q, f"وجدت {len(parts)} نتيجة للأسعار", "prices")
            return render_page(q, mode, panel)

        elif mode == "images":
            panel = f'<div class="card"><a target="_blank" href="https://duckduckgo.com/?q={html.escape(q)}&iax=images&ia=images">افتح نتائج الصور 🔗</a></div>'
            save_question_history(q, "بحث عن الصور", "images")
            return render_page(q, mode, panel)

        else:
            return render_page(q, mode, '<div class="card">وضع غير معروف</div>')

    except Exception as e:
        panel = f'<div class="card">خطأ أثناء البحث: {html.escape(str(e))}</div>'
        save_question_history(q, f"خطأ: {e}", mode)
        return render_page(q, mode, panel)

@app.get("/history", response_class=HTMLResponse)
async def history():
    rows = get_question_history(50)
    html_rows = ""
    for (qid, question, answer, mode, created_at) in rows:
        dt = (created_at.strftime("%Y/%m/%d %H:%M") if hasattr(created_at, "strftime")
              else str(created_at))
        html_rows += f"""
        <div class="card">
          <div><strong>📝 سؤال:</strong> {html.escape(question)}</div>
          <div style="margin-top:6px"><strong>💡 إجابة:</strong> {html.escape(answer[:300])}{'...' if len(answer)>300 else ''}</div>
          <div style="margin-top:6px; color:#666">وضع: {html.escape(mode)} — ⏱️ {dt}</div>
          <a href="/?q={html.escape(question)}&mode={html.escape(mode)}" style="display:inline-block;margin-top:8px">🔄 استخدم السؤال</a>
        </div>
        """
    page = f"""<!DOCTYPE html><html lang="ar" dir="rtl"><head>
    <meta charset="utf-8"><title>سجل الأسئلة</title>
    <style>body{{font-family:Tahoma,Arial;background:#f5f7fb;padding:20px}}.card{{background:#fff;padding:14px;border-radius:10px;margin:10px 0;box-shadow:0 2px 10px rgba(0,0,0,.05)}}</style>
    </head><body><h2>📚 سجل الأسئلة</h2>{html_rows or '<p>لا يوجد سجل بعد.</p>'}</body></html>"""
    return HTMLResponse(page)

@app.get("/history/export")
def export_history(limit: int = 1000):
    rows = get_question_history(limit)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["id","question","answer","mode","created_at"])
    for r in rows[::-1]: w.writerow(r)
    return Response(out.getvalue().encode("utf-8-sig"),
                    media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition":"attachment; filename=bassam_history.csv"})

@app.get("/healthz")
async def healthz():
    return {"status":"ok"}