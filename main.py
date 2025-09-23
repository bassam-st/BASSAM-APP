from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
import httpx, re, ast, math, os, psycopg2, html, csv, io, base64
from datetime import datetime

# بحث جاهز بدون سكربنج HTML
from duckduckgo_search import DDGS

# مكتبات الرياضيات المتقدمة + الرسوم البيانية
from sympy import (
    symbols, Matrix, sympify, simplify, diff, integrate, sqrt, sin, cos, tan,
    solve, Eq, factor, expand, limit, oo, series, det, latex,
    ln, log, pi, lambdify
)
try:
    from sympy.matrices import matrix_rank as rank
except ImportError:
    def rank(matrix):
        return matrix.rank()
import sympy as sp

# الرسم البياني والحوسبة العلمية
import numpy as np
import matplotlib
matplotlib.use("Agg")  # لا GUI backend
import matplotlib.pyplot as plt

# ترجمة تلقائية
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False
    def to_ar(text): return text

# نظام الذكاء الاصطناعي
try:
    from gemini import answer_with_ai, smart_math_help, is_gemini_available
    GEMINI_AVAILABLE = True
except Exception as e:
    # حتى لو كان هناك خطأ في ملف gemini.py، لا نوقف التطبيق
    GEMINI_AVAILABLE = False
    def answer_with_ai(question: str): return None
    def smart_math_help(question: str): return None
    def is_gemini_available() -> bool: return False

# ==== إعدادات FastAPI ====
app = FastAPI(title="Bassam Smart App - Ultimate Edition", version="5.0")

# إعداد الملفات الثابتة (Static Files)
@app.get("/service-worker.js")
async def get_service_worker():
    """خدمة ملف Service Worker للـ PWA"""
    return FileResponse("service-worker.js", media_type="application/javascript")

@app.get("/manifest.json")
async def get_manifest():
    """خدمة ملف Manifest للـ PWA"""
    return FileResponse("manifest.json", media_type="application/json")

# ===================== قاعدة البيانات (PostgreSQL) =====================
def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise Exception("DATABASE_URL environment variable not found")
    return psycopg2.connect(db_url)

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
async def startup_event():
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
AR_CHARS_RE = re.compile(r'[\u0600-\u06FF]')

def is_arabic(s: str) -> bool:
    return bool(AR_CHARS_RE.search(s or ""))

def to_ar(text: str) -> str:
    """ترجمة النص للعربية إذا لم يكن عربياً"""
    try:
        if not TRANSLATOR_AVAILABLE or not text: return text
        if is_arabic(text): return text
        return GoogleTranslator(source='auto', target='ar').translate(text)
    except Exception:
        return text

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
    "pi": math.pi
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

# ===================== 3) الرسم البياني المتقدم =====================
def plot_expr_base64(expr, var=symbols('x'), xmin=-10, xmax=10, points=400):
    """رسم التعبير الرياضي وإرجاعه كـ base64"""
    try:
        f = lambdify(var, expr, 'numpy')
        xs = np.linspace(xmin, xmax, points)
        try:
            ys = f(xs)
        except Exception:
            ys = np.array([np.nan]*len(xs))
        
        # إعداد الرسم باللغة العربية
        plt.rcParams['font.family'] = ['Arial Unicode MS', 'Tahoma', 'DejaVu Sans']
        fig, ax = plt.subplots(figsize=(8,6))
        ax.plot(xs, ys, linewidth=2, color='#4facfe')
        ax.axhline(0, color='black', linewidth=0.8)
        ax.axvline(0, color='black', linewidth=0.8)
        ax.set_title(f"الرسم البياني لـ f(x) = {expr}", fontsize=14, pad=20)
        ax.set_xlabel('x', fontsize=12)
        ax.set_ylabel('f(x)', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        # حفظ كـ base64
        buf = io.BytesIO()
        fig.tight_layout()
        fig.savefig(buf, format="png", dpi=100, bbox_inches='tight')
        plt.close(fig)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        return None

# ===================== 4) التلخيص المتقدم =====================
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
    """تلخيص متقدم باستخدام BM25 + TextRank"""
    candidate_sents = []
    for t in page_texts:
        candidate_sents.extend(_sent_tokenize_ar(t)[:200])
    if not candidate_sents: return ""
    if not SUMY_AVAILABLE:
        return " ".join(candidate_sents[:max_final_sents])

    try:
        def tok(s):
            s = s.lower()
            s = re.sub(r"[^\w\s\u0600-\u06FF]+"," ", s)
            return s.split()
        
        bm25 = BM25Okapi([tok(s) for s in candidate_sents])
        idx = np.argsort(bm25.get_scores(tok(question)))[::-1][:12]
        chosen = [candidate_sents[i] for i in idx]
        
        parser = PlainTextParser.from_string(" ".join(chosen), Tokenizer("english"))
        summ = TextRankSummarizer()
        out = " ".join(str(s) for s in summ(parser.document, max_final_sents)).strip()
        return out or " ".join(chosen[:max_final_sents])
    except:
        return " ".join(candidate_sents[:max_final_sents])

# ===================== 5) رياضيات متقدمة شاملة + مصفوفات + إحصاء =====================

def normalize_math(expr: str) -> str:
    """تطبيع التعبير الرياضي"""
    t = (expr or "").strip().translate(AR_NUM)
    
    # إزالة المفاتيح العربية والإنجليزية
    prefixes = ['مشتق:', 'تكامل:', 'حل:', 'تبسيط:', 'تحليل:', 'توسيع:', 'ارسم:', 'نهاية:', 
                'diff:', 'integral:', 'solve:', 'simplify:', 'factor:', 'expand:', 'plot:', 'limit:']
    for prefix in prefixes:
        if t.lower().startswith(prefix.lower()):
            t = t[len(prefix):].strip()
            break
    
    # تطبيع العمليات
    t = t.replace('^','**').replace('جذر','sqrt')
    t = re.sub(r'\\cdot','*', t)
    t = re.sub(r'\\(sin|cos|tan|sqrt|ln|log)','\\1', t)
    
    # تحسين المسافات - إضافة + حيث توجد مسافات بين المصطلحات
    # معالجة حالات مثل "x**3   2*x" لتصبح "x**3 + 2*x"
    t = re.sub(r'\s+(\d*[a-zA-Z])', r' + \1', t)
    # معالجة حالات أخرى
    t = re.sub(r'([a-zA-Z0-9\)])\s+([a-zA-Z])', r'\1 + \2', t)
    
    # إزالة علامة المساواة في البداية
    t = re.sub(r'^\s*[a-zA-Z]\s*(\(\s*x\s*\))?\s*=\s*', '', t)
    
    return t.strip()

def detect_task(q: str) -> str:
    """كشف نوع المهمة الرياضية"""
    s = q.lower()
    if any(w in s for w in ['ارسم','plot','رسم']):                     return 'plot'
    if any(w in s for w in ['مشتق','اشتق','derivative','diff']): return 'diff'
    if any(w in s for w in ['تكامل','integral','integrate']):    return 'int'
    if any(w in s for w in ['حد','نهاية','limit']):              return 'limit'
    if any(w in s for w in ['حل','معادلة','solve']):             return 'solve'
    if any(w in s for w in ['تبسيط','بسّط','simplify']):         return 'simp'
    if any(w in s for w in ['تحليل','factor']):                   return 'factor'
    if any(w in s for w in ['توسيع','expand']):                   return 'expand'
    if any(w in s for w in ['مصفوف','matrix','مصفوفة']):         return 'matrix'
    if any(w in s for w in ['سلسلة','series','تايلور']):         return 'series'
    if any(w in s for w in ['احصاء','إحصاء','متوسط','وسيط','منوال','انحراف','تباين','احتمال','توافيق','تباديل','ncr','npr']):
        return 'stats'
    return 'auto'

def solve_stats(q: str):
    """حل مسائل الإحصاء والاحتمالات المتقدمة"""
    s = q.translate(AR_NUM)
    nums = [float(x) for x in re.findall(r'[-+]?\d+\.?\d*', s)]
    lower = q.lower()
    
    # توافيق/تباديل
    if 'توافيق' in lower or 'ncr' in lower:
        m = re.findall(r'\d+', s)
        if len(m) >= 2:
            n, r = int(m[0]), int(m[1])
            import math
            val = math.comb(n, r)
            formula = f"C({n},{r}) = {n}! / ({r}! × ({n}-{r})!)"
            html_out = f"""<div class='card'><h4>📦 توافيق C(n,r)</h4>
            <p><strong>الصيغة:</strong> {formula}</p>
            <p><strong>النتيجة:</strong> C({n},{r}) = {val:,}</p>
            <p><strong>المعنى:</strong> عدد طرق اختيار {r} عناصر من {n} عنصر بدون اعتبار الترتيب</p></div>"""
            return {"text": f"C({n},{r}) = {val}", "html": html_out}
    
    if 'تباديل' in lower or 'npr' in lower:
        m = re.findall(r'\d+', s)
        if len(m) >= 2:
            n, r = int(m[0]), int(m[1])
            import math
            val = math.factorial(n) // math.factorial(n-r)
            formula = f"P({n},{r}) = {n}! / ({n}-{r})!"
            html_out = f"""<div class='card'><h4>🔁 تباديل P(n,r)</h4>
            <p><strong>الصيغة:</strong> {formula}</p>
            <p><strong>النتيجة:</strong> P({n},{r}) = {val:,}</p>
            <p><strong>المعنى:</strong> عدد طرق ترتيب {r} عناصر من {n} عنصر مع اعتبار الترتيب</p></div>"""
            return {"text": f"P({n},{r}) = {val}", "html": html_out}
    
    # ثنائي الحدين
    m_p = re.search(r'p\s*=\s*([0-9.]+)', s, re.I)
    m_n = re.search(r'n\s*=\s*(\d+)', s, re.I)
    m_k = re.search(r'k\s*=\s*(\d+)', s, re.I)
    if m_p and m_n and m_k:
        p = float(m_p.group(1)); n = int(m_n.group(1)); k = int(m_k.group(1))
        import math
        prob = math.comb(n,k) * (p**k) * ((1-p)**(n-k))
        html_out = f"""<div class='card'><h4>🎲 احتمال ثنائي الحدين</h4>
        <p><strong>المعطيات:</strong> n={n}, k={k}, p={p}</p>
        <p><strong>الصيغة:</strong> P(X=k) = C(n,k) × p^k × (1-p)^(n-k)</p>
        <p><strong>النتيجة:</strong> P(X={k}) = {prob:.6f}</p></div>"""
        return {"text": f"Binomial P = {prob}", "html": html_out}
    
    # مقاييس وصفية
    if nums and len(nums) >= 2:
        arr = sorted(nums)
        n = len(arr)
        mean = sum(arr)/n
        median = arr[n//2] if n%2==1 else (arr[n//2-1]+arr[n//2])/2
        
        # منوال
        from collections import Counter
        cnt = Counter(arr)
        mode = cnt.most_common(1)[0][0]
        
        # تباين وانحراف معياري
        var = sum((x-mean)**2 for x in arr)/n
        std = var**0.5
        
        # المدى
        range_val = max(arr) - min(arr)
        
        html_out = f"""<div class='card'><h4>📊 إحصاء وصفي شامل</h4>
        <p><strong>البيانات:</strong> {[round(x,2) for x in arr]}</p>
        <hr>
        <h5>مقاييس النزعة المركزية:</h5>
        <p>• <strong>المتوسط الحسابي:</strong> {mean:.4f}</p>
        <p>• <strong>الوسيط:</strong> {median:.4f}</p>
        <p>• <strong>المنوال:</strong> {mode:.4f}</p>
        <hr>
        <h5>مقاييس التشتت:</h5>
        <p>• <strong>المدى:</strong> {range_val:.4f}</p>
        <p>• <strong>التباين:</strong> {var:.4f}</p>
        <p>• <strong>الانحراف المعياري:</strong> {std:.4f}</p>
        <hr>
        <p><strong>العدد الكلي:</strong> {n} قيمة</p></div>"""
        
        return {"text": f"mean={mean:.4f}, median={median:.4f}, std={std:.4f}",
                "html": html_out}
    
    return None

def solve_advanced_math(q: str):
    """نظام رياضيات متقدم شامل"""
    try:
        task = detect_task(q)
        txt = normalize_math(q)
        x,y,t,z = symbols('x y t z')
        local = dict(sin=sin, cos=cos, tan=tan, sqrt=sqrt, ln=ln, log=log, pi=pi)

        # إحصاء/احتمالات
        if task == 'stats':
            return solve_stats(q)

        # مصفوفات
        if task == 'matrix' or 'matrix' in txt.lower():
            try:
                # استخراج المصفوفة من النص
                m = re.search(r'matrix\s*[:\[\(]\s*(\[.+\])', txt, re.I)
                if m:
                    matrix_data = m.group(1)
                else:
                    matrix_data = re.search(r'\[\[.+\]\]', txt)
                    matrix_data = matrix_data.group(0) if matrix_data else txt.replace('matrix','').strip()
                
                M = Matrix(sympify(matrix_data, locals=local))
                info = []
                info.append(f"أبعاد المصفوفة: {M.rows} × {M.cols}")
                info.append(f"الرتبة: {rank(M)}")
                
                if M.shape[0] == M.shape[1]:  # مصفوفة مربعة
                    det_val = det(M)
                    info.append(f"المحدد: {det_val}")
                    try:
                        if det_val != 0:
                            invM = M.inv()
                            info.append(f"المصفوفة قابلة للعكس")
                        else:
                            info.append("المصفوفة غير قابلة للعكس (المحدد = 0)")
                    except:
                        info.append("لا يمكن حساب المعكوس")
                
                html_out = f"""<div class='card'><h4>🧮 تحليل المصفوفة</h4>
                <h5>المصفوفة:</h5>
                <pre style="background:#f8f9fa;padding:10px;border-radius:5px;">{M}</pre>
                <hr>
                <h5>خصائص المصفوفة:</h5>""" + \
                "".join(f"<p>• <strong>{s}</strong></p>" for s in info) + "</div>"
                
                return {"text": " | ".join(info), "html": html_out}
            except Exception as e:
                return {"text": f"خطأ في المصفوفة: {e}", "html": f"<div class='card'>خطأ في تحليل المصفوفة: {e}</div>"}

        # معالجة التعبير الرياضي
        expr = sympify(txt, locals=local)
        result_html = f'<div class="card"><h4>📐 المسألة: {html.escape(q)}</h4><hr>'
        
        # رسم بياني
        if task == 'plot':
            img = plot_expr_base64(expr, x)
            if img:
                result_html += f"""<h5>📈 الرسم البياني:</h5>
                <img src='{img}' style='max-width:100%; height:auto; border-radius:8px; box-shadow:0 2px 10px rgba(0,0,0,0.1);'>"""
                result_html += f"<p><strong>الدالة:</strong> f(x) = {expr}</p></div>"
                return {"text": f"رسم: {expr}", "html": result_html}
            else:
                result_html += "<p>تعذر رسم الدالة</p></div>"
                return {"text": "خطأ في الرسم", "html": result_html}

        # مشتق
        if task == 'diff':
            res = diff(expr, x)
            result_html += f"""<h5>🧮 المشتقة الأولى:</h5>
            <p style="background:#e3f2fd;padding:15px;border-radius:8px;text-align:center;font-size:18px;">
            <strong>f'(x) = {res}</strong></p>
            <p><strong>LaTeX:</strong> {latex(res)}</p>"""
            
            # مشتقة ثانية إذا أمكن
            try:
                second_diff = diff(res, x)
                result_html += f"<p><strong>المشتقة الثانية:</strong> f''(x) = {second_diff}</p>"
            except: pass
            
            result_html += "</div>"
            return {"text": f"المشتق: {res}", "html": result_html}

        # تكامل
        if task == 'int':
            res = integrate(expr, x)
            result_html += f"""<h5>∫ التكامل غير المحدد:</h5>
            <p style="background:#e8f5e8;padding:15px;border-radius:8px;text-align:center;font-size:18px;">
            <strong>∫ f(x) dx = {res} + C</strong></p>
            <p><strong>LaTeX:</strong> {latex(res)} + C</p></div>"""
            return {"text": f"التكامل: {res} + C", "html": result_html}

        # نهاية
        if task == 'limit':
            res = limit(expr, x, oo)
            result_html += f"""<h5>🎯 النهاية عند اللانهاية:</h5>
            <p style="background:#fff3e0;padding:15px;border-radius:8px;text-align:center;font-size:18px;">
            <strong>lim(x→∞) f(x) = {res}</strong></p></div>"""
            return {"text": f"النهاية: {res}", "html": result_html}

        # سلسلة تايلور
        if task == 'series':
            res = series(expr, x, 0, 6)
            result_html += f"""<h5>📈 سلسلة تايلور حول x=0:</h5>
            <p style="background:#f3e5f5;padding:15px;border-radius:8px;text-align:center;font-size:16px;">
            <strong>{res}</strong></p>
            <p><em>سلسلة تايلور تقرب الدالة باستخدام كثيرات حدود</em></p></div>"""
            return {"text": f"سلسلة: {res}", "html": result_html}

        # تحليل
        if task == 'factor':
            res = factor(expr)
            result_html += f"""<h5>🔢 تحليل التعبير:</h5>
            <p style="background:#e1f5fe;padding:15px;border-radius:8px;text-align:center;font-size:18px;">
            <strong>{res}</strong></p></div>"""
            return {"text": f"التحليل: {res}", "html": result_html}

        # توسيع
        if task == 'expand':
            res = expand(expr)
            result_html += f"""<h5>📐 توسيع التعبير:</h5>
            <p style="background:#f1f8e9;padding:15px;border-radius:8px;text-align:center;font-size:18px;">
            <strong>{res}</strong></p></div>"""
            return {"text": f"التوسيع: {res}", "html": result_html}

        # حل معادلة
        if task == 'solve' or '=' in txt:
            if '=' in txt:
                lhs, rhs = txt.split('=', 1)
                eq = sympify(lhs, locals=local) - sympify(rhs, locals=local)
            else:
                eq = expr
            
            solutions = solve(eq, x)
            result_html += f"""<h5>🔍 حل المعادلة:</h5>"""
            if solutions:
                for i, sol in enumerate(solutions, 1):
                    result_html += f"<p><strong>الحل {i}:</strong> x = {sol}</p>"
                result_html += f"<p><strong>عدد الحلول:</strong> {len(solutions)}</p>"
            else:
                result_html += "<p>لا يوجد حل حقيقي</p>"
            result_html += "</div>"
            return {"text": f"الحلول: {solutions}", "html": result_html}

        # تبسيط تلقائي
        res = simplify(expr)
        result_html += f"""<h5>✨ تبسيط التعبير:</h5>
        <p style="background:#fafafa;padding:15px;border-radius:8px;text-align:center;font-size:18px;">
        <strong>{res}</strong></p>
        <p><strong>LaTeX:</strong> {latex(res)}</p></div>"""
        return {"text": f"التبسيط: {res}", "html": result_html}

    except Exception as e:
        error_html = f'''<div class="card">
            <h4>❌ تعذّر فهم التعبير الرياضي</h4>
            <p><strong>خطأ:</strong> {html.escape(str(e))}</p>
            <hr>
            <h5>أمثلة صحيحة:</h5>
            <ul>
                <li><code>مشتق: x**3 + 2*sin(x)</code></li>
                <li><code>تكامل: cos(x)</code></li>
                <li><code>حل: x**2 - 5*x + 6 = 0</code></li>
                <li><code>ارسم: sin(x)</code></li>
                <li><code>matrix: [[1,2],[3,4]]</code></li>
                <li><code>توافيق 10 3</code></li>
                <li><code>متوسط: 2,4,6,8</code></li>
            </ul>
        </div>'''
        return {"text": f"خطأ: {e}", "html": error_html}

# ===================== 6) نظام التعليم التدريجي =====================

def detect_educational_level(q: str) -> str:
    """تحديد المستوى التعليمي"""
    text = html.unescape(q).lower()
    
    # إحصاء واحتمالات
    statistics_keywords = ['متوسط', 'وسيط', 'منوال', 'انحراف معياري', 'تباين', 'احتمال', 'إحصاء', 'توافيق', 'تباديل']
    if any(keyword in text for keyword in statistics_keywords):
        return 'statistics'
    
    # رياضيات جامعية
    university_keywords = ['مشتق', 'تكامل', 'نهاية', 'متسلسلة', 'مصفوفة', 'معادلة تفاضلية', 'لابلاس', 'فورير', 'matrix']
    if any(keyword in text for keyword in university_keywords):
        return 'university'
    
    # رياضيات ثانوية
    high_school_keywords = ['sin', 'cos', 'tan', 'لوغاريتم', 'أسي', 'تربيعية', 'مثلثات', 'هندسة تحليلية']
    if any(keyword in text for keyword in high_school_keywords):
        return 'high_school'
    
    # رياضيات إعدادية  
    middle_school_keywords = ['جبر', 'معادلة خطية', 'نسبة', 'تناسب', 'مساحة', 'محيط', 'حجم', 'مثلث', 'فيثاغورث']
    if any(keyword in text for keyword in middle_school_keywords):
        return 'middle_school'
    
    # ابتدائي
    if any(op in text for op in ['+', '-', '*', '/', '×', '÷', '=', 'جمع', 'طرح', 'ضرب', 'قسمة']):
        return 'elementary'
    
    return 'not_math'

def solve_comprehensive_math(q: str):
    """نظام رياضيات شامل لجميع المراحل"""
    try:
        level = detect_educational_level(q)
        
        if level == 'not_math':
            return None
        
        # توجيه للمعالج المناسب
        if level in ['statistics', 'university', 'high_school']:
            return solve_advanced_math(q)
        
        # معالجة المراحل الأساسية بطريقة مبسطة
        elif level == 'middle_school':
            return solve_middle_school_math(q)
        
        elif level == 'elementary':
            return solve_elementary_math(q)
        
        return None
    except:
        return None

def solve_middle_school_math(q: str):
    """رياضيات المرحلة الإعدادية"""
    try:
        result_html = f'<div class="card"><h4>📚 رياضيات المرحلة الإعدادية</h4><hr>'
        
        # مساحة ومحيط
        if 'مساحة' in q or 'محيط' in q:
            if 'مربع' in q:
                result_html += """<h5>📐 المربع:</h5>
                <p><strong>المحيط:</strong> 4 × طول الضلع</p>
                <p><strong>المساحة:</strong> (طول الضلع)²</p>"""
            elif 'مستطيل' in q:
                result_html += """<h5>📐 المستطيل:</h5>
                <p><strong>المحيط:</strong> 2 × (الطول + العرض)</p>
                <p><strong>المساحة:</strong> الطول × العرض</p>"""
            elif 'دائرة' in q:
                result_html += """<h5>⭕ الدائرة:</h5>
                <p><strong>المحيط:</strong> 2π × نصف القطر = π × القطر</p>
                <p><strong>المساحة:</strong> π × (نصف القطر)²</p>
                <p><strong>π ≈ 3.14159</strong></p>"""
            else:
                result_html += """<h5>📐 الأشكال الهندسية الأساسية:</h5>
                <p><strong>المربع:</strong> محيط = 4س، مساحة = س²</p>
                <p><strong>المستطيل:</strong> محيط = 2(ط+ع)، مساحة = ط×ع</p>
                <p><strong>المثلث:</strong> مساحة = ½ × القاعدة × الارتفاع</p>"""
        
        # فيثاغورث
        elif 'فيثاغورث' in q or 'قائم' in q:
            result_html += """<h5>📐 نظرية فيثاغورث:</h5>
            <p><strong>في المثلث القائم الزاوية:</strong></p>
            <p><strong>الصيغة:</strong> أ² + ب² = ج²</p>
            <p>حيث ج هو الوتر (أطول ضلع)</p>
            <p><strong>مثال:</strong> إذا كان أ=3، ب=4 → ج = √(9+16) = √25 = 5</p>"""
        
        else:
            result_html += """<h5>📚 مواضيع المرحلة الإعدادية:</h5>
            <ul>
                <li><strong>الهندسة:</strong> مساحة ومحيط الأشكال</li>
                <li><strong>الجبر:</strong> المعادلات الخطية البسيطة</li>
                <li><strong>فيثاغورث:</strong> العلاقة في المثلث القائم</li>
                <li><strong>النسب والتناسب:</strong> حل المسائل العملية</li>
            </ul>"""
        
        result_html += '</div>'
        return {"text": "رياضيات إعدادية", "html": result_html}
    except:
        return None

def solve_elementary_math(q: str):
    """رياضيات المرحلة الابتدائية"""
    try:
        result_html = f'<div class="card"><h4>🎈 رياضيات المرحلة الابتدائية</h4><hr>'
        
        # جداول الضرب
        if 'جدول ضرب' in q or 'جدول' in q:
            # استخراج الرقم
            nums = re.findall(r'\d+', q)
            if nums:
                n = int(nums[0])
                result_html += f"""<h5>📊 جدول ضرب {n}:</h5>
                <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:5px;">"""
                for i in range(1, 11):
                    result_html += f"<p>{n} × {i} = {n*i}</p>"
                result_html += "</div>"
            else:
                result_html += """<h5>📊 أهمية جداول الضرب:</h5>
                <p>جداول الضرب هي أساس الرياضيات!</p>
                <p><strong>نصيحة:</strong> احفظ جداول الضرب من 1 إلى 12</p>"""
        
        # العمليات الأساسية
        else:
            result_html += """<h5>🔢 العمليات الحسابية الأساسية:</h5>
            <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;">
                <div>
                    <p><strong>➕ الجمع:</strong></p>
                    <p>5 + 3 = 8</p>
                </div>
                <div>
                    <p><strong>➖ الطرح:</strong></p>
                    <p>8 - 3 = 5</p>
                </div>
                <div>
                    <p><strong>✖️ الضرب:</strong></p>
                    <p>4 × 6 = 24</p>
                </div>
                <div>
                    <p><strong>➗ القسمة:</strong></p>
                    <p>24 ÷ 6 = 4</p>
                </div>
            </div>
            <hr>
            <h5>🎯 نصائح للحساب السريع:</h5>
            <ul>
                <li>احفظ جداول الضرب جيداً</li>
                <li>تدرب على الحساب الذهني</li>
                <li>استخدم أصابعك للعد</li>
            </ul>"""
        
        result_html += '</div>'
        return {"text": "رياضيات ابتدائية", "html": result_html}
    except:
        return None

# ===================== 7) البحث والتلخيص =====================

def web_answer_ar(q: str, mode: str):
    """بحث وتلخيص متقدم"""
    try:
        ddgs = DDGS()
        results = list(ddgs.text(q, region="xa-ar", safesearch="moderate", max_results=15))
        pairs = [(re.sub(r"\s+", " ", (r.get("body") or "")), r.get("href")) for r in results]
        ar_pairs = [p for p in pairs if is_arabic(p[0])]
        non_ar_pairs = [p for p in pairs if not is_arabic(p[0])]

        texts = [t for (t, _) in ar_pairs]
        if len(texts) < 8 and TRANSLATOR_AVAILABLE:
            texts += [to_ar(t) for (t, _) in non_ar_pairs][:8-len(texts)]

        if mode == "summary":
            final = summarize_advanced(q, texts, max_final_sents=4) or "لم أجد ملخصًا مناسبًا."
            panel = f'<div class="card"><h4>📄 ملخص ذكي</h4><p>{html.escape(final)}</p></div>'
            return {"text": final, "html": panel}

        elif mode == "prices":
            merged = ar_pairs + [(to_ar(t) if TRANSLATOR_AVAILABLE else t, url) for (t, url) in non_ar_pairs]
            parts = []
            for (s, a) in merged:
                if any(x in s for x in ["$", "USD", "SAR", "ر.س", "AED", "د.إ", "EGP", "ج.م", "ريال", "درهم", "جنيه"]):
                    link = f'<a target="_blank" href="{html.escape(a or "#")}">🔗 المصدر</a>'
                    parts.append(f'<div class="card">{html.escape(s[:300])}... — {link}</div>')
                if len(parts) >= 8: break
            panel = "".join(parts) if parts else '<div class="card">لم أجد أسعارًا واضحة.</div>'
            return {"text": f"نتائج أسعار: {len(parts)}", "html": panel}

        elif mode == "images":
            panel = f'''<div class="card"><h4>🖼️ البحث في الصور</h4>
            <a target="_blank" href="https://duckduckgo.com/?q={html.escape(q)}&iax=images&ia=images" 
               style="display:inline-block;padding:10px 20px;background:#4facfe;color:white;text-decoration:none;border-radius:5px;">
               🔍 افتح نتائج الصور</a></div>'''
            return {"text": "رابط الصور", "html": panel}

        return {"text":"وضع غير معروف","html":'<div class="card">وضع غير معروف</div>'}
    except Exception as e:
        return {"text": f"خطأ في البحث: {e}", "html": f'<div class="card">خطأ في البحث: {html.escape(str(e))}</div>'}

# ===================== 8) الواجهة =====================

def render_page(q="", mode="summary", result_panel=""):
    active = lambda m: "active" if mode==m else ""
    checked= lambda m: "checked" if mode==m else ""
    js = '''
document.querySelectorAll('.mode-btn').forEach(btn=>{
  btn.addEventListener('click',()=>{
    document.querySelectorAll('.mode-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active'); btn.querySelector('input').checked = true;
  });
});
document.getElementById('question').focus();
'''
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🤖 بسام الذكي - الإصدار الشامل</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Tahoma,Arial;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:20px;direction:rtl}}
.container{{max-width:900px;margin:0 auto;background:#fff;border-radius:16px;box-shadow:0 10px 30px rgba(0,0,0,.15);overflow:hidden}}
.header{{background:linear-gradient(135deg,#4facfe 0%,#00f2fe 100%);color:#fff;padding:30px;text-align:center;position:relative}}
.history-btn{{position:absolute;top:20px;left:20px;padding:10px 20px;background:rgba(255,255,255,.2);color:#fff;text-decoration:none;border-radius:25px;border:2px solid rgba(255,255,255,.3);transition:all 0.3s}}
.history-btn:hover{{background:rgba(255,255,255,.3)}}
.content{{padding:30px}}
input[type=text]{{width:100%;padding:16px;border:2px solid #e1e5e9;border-radius:12px;font-size:16px;transition:border-color 0.3s}}
input[type=text]:focus{{border-color:#4facfe;outline:none}}
.mode-selector{{display:flex;gap:12px;margin:20px 0;flex-wrap:wrap}}
.mode-btn{{flex:1;min-width:130px;padding:14px 20px;border:2px solid #e1e5e9;background:#fff;border-radius:10px;cursor:pointer;text-align:center;font-weight:bold;transition:all 0.3s}}
.mode-btn:hover{{background:#f8f9fa}}
.mode-btn.active{{background:#4facfe;color:#fff;border-color:#4facfe;transform:translateY(-2px)}}
.submit-btn{{width:100%;padding:16px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff;border:none;border-radius:12px;font-size:18px;font-weight:bold;cursor:pointer;transition:transform 0.3s}}
.submit-btn:hover{{transform:translateY(-2px)}}
.result{{margin-top:30px;padding:20px;background:#f8f9fa;border-radius:12px;border-right:4px solid #4facfe}}
.card{{background:#fff;padding:20px;border-radius:12px;box-shadow:0 4px 15px rgba(0,0,0,.1);margin:15px 0;line-height:1.6}}
.footer{{text-align:center;padding:20px;color:#666;border-top:1px solid #eee}}
pre{{background:#f8f9fa;padding:10px;border-radius:8px;overflow-x:auto}}
</style></head>
<body>
<div class="container">
  <div class="header">
    <a href="/history" class="history-btn">📚 السجل</a>
    <h1>🤖 بسام الذكي - مساعدك الذكي المجاني</h1>
    <p>🆓 ذكاء اصطناعي مجاني • 📊 رياضيات متقدمة • 📈 رسوم بيانية • 🔢 مصفوفات • 📋 إحصاء • 🌐 بحث ذكي</p>
  </div>
  <div class="content">
    <form method="post" action="/">
      <label for="question">اسأل بسام أي شيء - مجاناً 100%:</label>
      <input type="text" id="question" name="question" 
             placeholder="🤖 AI: ما هي أفضل طريقة للتعلم؟ • 📊 رياضيات: diff: x**3 + 2*x • 📈 رسم: plot: sin(x) • 🔢 مصفوفات: matrix: [[1,2],[3,4]]" 
             value="{html.escape(q)}" required>
      <div class="mode-selector">
        <label class="mode-btn {active('summary')}"><input type="radio" name="mode" value="summary" {checked('summary')} style="display:none">📄 ملخص</label>
        <label class="mode-btn {active('math')}"><input type="radio" name="mode" value="math" {checked('math')} style="display:none">🧮 رياضيات</label>
        <label class="mode-btn {active('prices')}"><input type="radio" name="mode" value="prices"  {checked('prices')}  style="display:none">💰 أسعار</label>
        <label class="mode-btn {active('images')}"><input type="radio" name="mode" value="images"  {checked('images')}  style="display:none">🖼️ صور</label>
      </div>
      <button type="submit" class="submit-btn">🔍 ابحث / احسب</button>
    </form>
    {f'<div class="result"><h3>النتيجة:</h3>{result_panel}</div>' if result_panel else ''}
  </div>
  <div class="footer">
    <p>🤖 تطبيق بسام الذكي v5.0 - المساعد الذكي المجاني</p>
    <p>🆓 ذكاء اصطناعي مجاني • 📊 رياضيات متقدمة • 📈 رسوم بيانية • 💯 بدون حدود</p>
  </div>
</div>
<script>{js}</script>
</body></html>"""

# ===================== 9) المسارات =====================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    q = request.query_params.get("q", "")
    mode = request.query_params.get("mode", "summary")
    return render_page(q, mode)

@app.post("/", response_class=HTMLResponse)
async def run(request: Request, question: str = Form(...), mode: str = Form("summary")):
    # تنظيف وإصلاح النص العربي
    q = (question or "").strip()
    
    # محاولة إصلاح مشكلة التشفير إذا كانت موجودة
    try:
        # إذا كان النص مُشوّه، حاول فكه
        if q and len(q) > 0 and all(ord(c) < 256 for c in q):
            q = q.encode('latin1').decode('utf-8')
    except:
        pass  # إذا فشل التحويل، استخدم النص كما هو
    
    if not q: return render_page()

    # **أولوية عليا للرياضيات المتقدمة - يجب أن تكون أولاً**
    math_keywords = ['مشتق', 'تكامل', 'حل', 'تبسيط', 'تحليل', 'توسيع', 'نهاية', 'معادلة', 'matrix', 'ارسم', 'plot', 'diff', 'integral', 'solve', 'factor', 'expand', 'derivative']
    has_advanced_math = mode == "math" or any(keyword in q.lower() for keyword in math_keywords)
    
    # إذا كان وضع الرياضيات أو يحتوي على كلمات رياضية متقدمة
    if has_advanced_math:
        advanced_math = solve_advanced_math(q)
        if advanced_math:
            save_question_history(q, advanced_math["text"], "advanced_math")
            return render_page(q, mode, advanced_math["html"])

    # 1) آلة حاسبة (أساسية) - فقط للحسابات البسيطة
    calc = try_calc_ar(q)
    if calc:
        save_question_history(q, calc["text"], "calculator")
        return render_page(q, mode, calc["html"])

    # 1.5) نظام رياضيات شامل (جميع المراحل التعليمية) - كبديل أخير
    comprehensive_math = solve_comprehensive_math(q)
    if comprehensive_math:
        save_question_history(q, comprehensive_math["text"], "comprehensive_math")
        return render_page(q, mode, comprehensive_math["html"])

    # 2) تحويل وحدات
    conv = convert_query_ar(q)
    if conv:
        save_question_history(q, conv["text"], "converter")
        return render_page(q, mode, conv["html"])

    # 3) الذكاء الاصطناعي المجاني (Gemini AI) - أولوية عالية للأسئلة العامة
    if GEMINI_AVAILABLE and is_gemini_available():
        # تحديد إذا كان السؤال رياضي بحت أم سؤال عام
        math_indicators = ['مشتق', 'تكامل', 'حل معادلة', 'matrix', 'ارسم', 'توافيق', 'تباديل']
        is_pure_math = any(indicator in q.lower() for indicator in math_indicators)
        
        # للأسئلة العامة (غير الرياضية البحتة) - اعطي AI الأولوية
        if not is_pure_math:
            ai_response = answer_with_ai(q)
            if ai_response:
                save_question_history(q, ai_response["text"], "ai_assistant")
                return render_page(q, mode, ai_response["html"])
        
        # حتى للأسئلة الرياضية، جرب AI كمساعد إضافي
        elif mode == "summary":  # في وضع الملخص، استخدم AI حتى للرياضيات
            ai_response = answer_with_ai(q)
            if ai_response:
                save_question_history(q, ai_response["text"], "ai_math_help")
                return render_page(q, mode, ai_response["html"])

    # 4) بحث/أسعار/صور (DuckDuckGo API)
    try:
        web_result = web_answer_ar(q, mode)
        save_question_history(q, web_result["text"], mode)
        return render_page(q, mode, web_result["html"])
    except Exception as e:
        error_panel = f'<div class="card"><h4>❌ خطأ في البحث</h4><p>{html.escape(str(e))}</p></div>'
        return render_page(q, mode, error_panel)

@app.get("/history", response_class=HTMLResponse)
async def history():
    rows = get_question_history(50)
    html_rows = ""
    for r in rows:
        dt = r[4].strftime("%Y/%m/%d %H:%M") if r[4] else "غير محدد"
        html_rows += f"""
        <div class="card">
          <div><strong>📝 سؤال:</strong> {html.escape(r[1])}</div>
          <div style="margin-top:8px"><strong>💡 إجابة:</strong> {html.escape(r[2][:300])}{'...' if len(r[2])>300 else ''}</div>
          <div style="margin-top:8px; color:#666"><strong>نوع:</strong> {html.escape(r[3])} — <strong>وقت:</strong> {dt}</div>
          <a href="/?q={html.escape(r[1])}&mode={html.escape(r[3])}" style="display:inline-block;margin-top:10px;padding:8px 16px;background:#4facfe;color:white;text-decoration:none;border-radius:5px;">🔄 إعادة استخدام</a>
        </div>
        """
    
    page = f"""<!DOCTYPE html><html lang="ar" dir="rtl"><head>
    <meta charset="utf-8"><title>📚 سجل الأسئلة - بسام الذكي</title>
    <style>
    body{{font-family:'Segoe UI',Tahoma,Arial;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:20px;direction:rtl}}
    .container{{max-width:900px;margin:0 auto;background:#fff;border-radius:15px;padding:30px;box-shadow:0 10px 30px rgba(0,0,0,.1)}}
    .card{{background:#f8f9fa;padding:20px;border-radius:10px;margin:15px 0;box-shadow:0 2px 10px rgba(0,0,0,.05)}}
    h1{{color:#4facfe;text-align:center;margin-bottom:30px}}
    a{{color:#4facfe;text-decoration:none}}
    .back-btn{{display:inline-block;margin-bottom:20px;padding:10px 20px;background:#4facfe;color:white;border-radius:25px;text-decoration:none}}
    </style>
    </head><body>
    <div class="container">
    <a href="/" class="back-btn">🏠 العودة للرئيسية</a>
    <h1>📚 سجل الأسئلة والإجابات</h1>
    {html_rows or '<div class="card"><p style="text-align:center;color:#666;">لا يوجد سجل بعد. ابدأ بطرح سؤال!</p></div>'}
    </div></body></html>"""
    return HTMLResponse(page)

@app.get("/health")
async def health_check():
    """نقطة فحص الصحة للإنتاج"""
    try:
        # فحص قاعدة البيانات
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

@app.get("/export")
def export_history():
    """تصدير السجل كملف CSV"""
    rows = get_question_history(1000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "السؤال", "الإجابة", "النوع", "التاريخ"])
    for r in rows:
        writer.writerow([r[0], r[1], r[2], r[3], r[4].strftime("%Y-%m-%d %H:%M:%S") if r[4] else ""])
    
    response = Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bassam_history.csv"}
    )
    return response

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)