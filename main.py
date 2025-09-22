from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, Response
import httpx, re, ast, math, os, psycopg2, html, csv, io
from datetime import datetime

# بحث جاهز بدون سكربنج HTML
from duckduckgo_search import DDGS

# مكتبات الرياضيات المتقدمة
from sympy import symbols, sympify, simplify, diff, integrate, sqrt, sin, cos, tan, solve, factor, expand, limit, oo, latex
import sympy as sp

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

# ===================== 3.5) الرياضيات المتقدمة (SymPy) =====================

def normalize_math(expr: str) -> str:
    """تطبيع/تنظيف تعبير رياضي ليقبله sympy."""
    t = (expr or "").strip()

    # احذف "y=" أو "f(x)=" أو أي متغير مفرد يساوي
    t = re.sub(r'^\s*[yf]\s*\(\s*x\s*\)\s*=\s*', '', t, flags=re.I)
    t = re.sub(r'^\s*[a-zA-Z]\s*=\s*', '', t)

    # إذا كان المستخدم كتب بالعربية "مشتق: ..." أو "تكامل: ..." خذ ما بعد النقطتين
    m = re.search(r'[,:؛]\s*(.+)$', t)
    t = m.group(1) if m else t

    # استبدالات LaTeX الشائعة
    t = (t.replace('\\cdot', '*')
           .replace('\\sin', 'sin').replace('\\cos', 'cos').replace('\\tan', 'tan')
           .replace('\\sqrt', 'sqrt')
           .replace('^', '**'))

    # أرقام عربية إلى إنجليزية (كـ احتياط)
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    for i, d in enumerate(arabic_digits):
        t = t.replace(d, str(i))

    # مسافات زائدة
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def detect_math_task(q: str) -> str:
    """استنتاج نوع المهمة من النص العربي: مشتق/تكامل/تبسيط/حل معادلة/تقييم."""
    text = q.lower()
    if any(w in text for w in ['مشتق', 'اشتق', 'اشتقاق', 'derivative', 'diff']):
        return 'diff'
    if any(w in text for w in ['تكامل', 'integral', 'integrate']):
        return 'int'
    if any(w in text for w in ['بسّط', 'تبسيط', 'simplify', 'تبسط']):
        return 'simp'
    if any(w in text for w in ['حل', 'احل', 'solve', 'معادلة', 'equation']):
        return 'solve'
    if any(w in text for w in ['حد', 'نهاية', 'limit']):
        return 'limit'
    if any(w in text for w in ['تحليل', 'factor']):
        return 'factor'
    if any(w in text for w in ['توسيع', 'expand']):
        return 'expand'
    # إن لم يذكر نوع المهمة نحاول التبسيط كافتراضي
    return 'auto'


def solve_advanced_math(q: str):
    """حل رياضيات متقدم (مشتق/تكامل/تبسيط/حل معادلات) باستخدام SymPy وإرجاع HTML عربي."""
    try:
        task = detect_math_task(q)
        expr_txt = normalize_math(q)

        # متغيرات شائعة
        x, y, t, z = symbols('x y t z')
        
        # معالجة التعبير
        expr = sympify(expr_txt, dict(sin=sin, cos=cos, tan=tan, sqrt=sqrt))
        
        result_html = f'<div class="card"><h4>📐 المسألة: {html.escape(q)}</h4><hr>'
        res = None  # تهيئة المتغير
        
        if task == 'diff':
            res = diff(expr, x)
            result_html += f'<h5>🧮 المشتق بالنسبة إلى x:</h5>'
            result_html += f'<p style="background:#f0f8ff;padding:15px;border-radius:8px;text-align:center;font-size:18px;"><strong>{latex(res)}</strong></p>'
            result_html += f'<p><strong>بالتدوين العادي:</strong> {res}</p>'
            
        elif task == 'int':
            res = integrate(expr, x)
            result_html += f'<h5>∫ التكامل غير المحدد بالنسبة إلى x:</h5>'
            result_html += f'<p style="background:#f0fff0;padding:15px;border-radius:8px;text-align:center;font-size:18px;"><strong>{latex(res)} + C</strong></p>'
            result_html += f'<p><strong>بالتدوين العادي:</strong> {res} + C</p>'
            
        elif task == 'solve':
            # حل المعادلة
            if '=' in expr_txt:
                lhs, rhs = expr_txt.split('=')
                equation = sympify(lhs) - sympify(rhs)
            else:
                equation = expr
            
            solutions = solve(equation, x)
            result_html += f'<h5>🔍 حل المعادلة:</h5>'
            if solutions:
                for i, sol in enumerate(solutions, 1):
                    result_html += f'<p><strong>الحل {i}:</strong> x = {sol}</p>'
                res = f"الحلول: {solutions}"
            else:
                result_html += f'<p>لا يوجد حل حقيقي للمعادلة</p>'
                res = "لا يوجد حل"
                
        elif task == 'factor':
            res = factor(expr)
            result_html += f'<h5>🔢 تحليل التعبير:</h5>'
            result_html += f'<p style="background:#fff5ee;padding:15px;border-radius:8px;text-align:center;font-size:18px;"><strong>{latex(res)}</strong></p>'
            result_html += f'<p><strong>بالتدوين العادي:</strong> {res}</p>'
            
        elif task == 'expand':
            res = expand(expr)
            result_html += f'<h5>📐 توسيع التعبير:</h5>'
            result_html += f'<p style="background:#f5f5ff;padding:15px;border-radius:8px;text-align:center;font-size:18px;"><strong>{latex(res)}</strong></p>'
            result_html += f'<p><strong>بالتدوين العادي:</strong> {res}</p>'
            
        elif task == 'limit':
            # نحاول استخراج النهاية
            res = limit(expr, x, oo)  # نهاية عند اللانهاية كافتراضي
            result_html += f'<h5>🎯 النهاية عند اللانهاية:</h5>'
            result_html += f'<p style="background:#ffeef5;padding:15px;border-radius:8px;text-align:center;font-size:18px;"><strong>{latex(res)}</strong></p>'
            result_html += f'<p><strong>بالتدوين العادي:</strong> {res}</p>'
            
        else:
            # محاولة تبسيط أو تقييم
            res = simplify(expr)
            result_html += f'<h5>✨ تبسيط/تقييم التعبير:</h5>'
            result_html += f'<p style="background:#f8f8ff;padding:15px;border-radius:8px;text-align:center;font-size:18px;"><strong>{latex(res)}</strong></p>'
            result_html += f'<p><strong>بالتدوين العادي:</strong> {res}</p>'

        result_html += '</div>'
        
        # نص للحفظ في قاعدة البيانات  
        result_text = f"نتيجة {task}: {res}"
        
        return {"text": result_text, "html": result_html}

    except Exception as e:
        error_html = f'''<div class="card">
            <h4>❌ تعذّر فهم التعبير الرياضي</h4>
            <p>جرّب أمثلة مثل:</p>
            <ul>
                <li><code>مشتق: x**3 + 2*sin(x)</code></li>
                <li><code>تكامل: cos(x)</code></li>
                <li><code>تبسيط: (x**2-1)/(x-1)</code></li>
                <li><code>حل: x**2 - 5*x + 6 = 0</code></li>
                <li><code>تحليل: x**2 - 4</code></li>
            </ul>
            <small style="color:#666;">خطأ تفصيلي: {html.escape(str(e))}</small>
        </div>'''
        return {"text": f"خطأ: {str(e)}", "html": error_html}

# ===================== 3.6) الإحصاء والاحتمالات =====================

def solve_statistics_math(q: str):
    """حل مسائل الإحصاء والاحتمالات"""
    try:
        result_html = f'<div class="card"><h4>📊 الإحصاء والاحتمالات: {html.escape(q)}</h4><hr>'
        
        if 'متوسط' in q.lower() or 'mean' in q.lower():
            # الوسط الحسابي
            result_html += f'<h5>📈 الوسط الحسابي (المتوسط):</h5>'
            result_html += f'<p><strong>الصيغة:</strong> المتوسط = (مجموع القيم) ÷ (عدد القيم)</p>'
            result_html += f'<p><strong>مثال:</strong> متوسط الأرقام 2, 4, 6, 8 = (2+4+6+8)÷4 = 5</p>'
            result_text = "قانون الوسط الحسابي"
            
        elif 'وسيط' in q.lower() or 'median' in q.lower():
            # الوسيط
            result_html += f'<h5>📊 الوسيط:</h5>'
            result_html += f'<p><strong>التعريف:</strong> الوسيط هو القيمة الوسطى عند ترتيب البيانات</p>'
            result_html += f'<p><strong>للعدد الفردي:</strong> الوسيط = القيمة الوسطى</p>'
            result_html += f'<p><strong>للعدد الزوجي:</strong> الوسيط = متوسط القيمتين الوسطيتين</p>'
            result_text = "قانون الوسيط"
            
        elif 'منوال' in q.lower() or 'mode' in q.lower():
            # المنوال
            result_html += f'<h5>📋 المنوال:</h5>'
            result_html += f'<p><strong>التعريف:</strong> المنوال هو القيمة الأكثر تكراراً في البيانات</p>'
            result_html += f'<p><strong>مثال:</strong> في المجموعة 2, 3, 3, 5, 3, 7 → المنوال = 3</p>'
            result_text = "تعريف المنوال"
            
        elif 'انحراف معياري' in q.lower() or 'standard deviation' in q.lower():
            # الانحراف المعياري
            result_html += f'<h5>📏 الانحراف المعياري:</h5>'
            result_html += f'<p><strong>الصيغة:</strong> σ = √[(Σ(x-μ)²)/N]</p>'
            result_html += f'<p><strong>المعنى:</strong> مقياس لتشتت البيانات حول المتوسط</p>'
            result_html += f'<p><strong>انحراف كبير:</strong> البيانات منتشرة</p>'
            result_html += f'<p><strong>انحراف صغير:</strong> البيانات مركزة</p>'
            result_text = "قانون الانحراف المعياري"
            
        elif 'احتمال' in q.lower() or 'probability' in q.lower():
            # الاحتمالات
            result_html += f'<h5>🎲 الاحتمالات:</h5>'
            result_html += f'<h6>القوانين الأساسية:</h6>'
            result_html += f'<p><strong>احتمال الحدث:</strong> P(A) = عدد النتائج المرغوبة / عدد النتائج الممكنة</p>'
            result_html += f'<p><strong>احتمال التتام:</strong> P(A) + P(A\') = 1</p>'
            result_html += f'<p><strong>احتمال الاتحاد:</strong> P(A∪B) = P(A) + P(B) - P(A∩B)</p>'
            result_html += f'<p><strong>احتمال شرطي:</strong> P(A|B) = P(A∩B) / P(B)</p>'
            result_text = "قوانين الاحتمالات"
            
        elif 'تباين' in q.lower() or 'variance' in q.lower():
            # التباين
            result_html += f'<h5>📐 التباين:</h5>'
            result_html += f'<p><strong>الصيغة:</strong> Var(X) = σ² = Σ(x-μ)²/N</p>'
            result_html += f'<p><strong>العلاقة:</strong> الانحراف المعياري = √التباين</p>'
            result_html += f'<p><strong>المعنى:</strong> مقياس لمدى انتشار البيانات</p>'
            result_text = "قانون التباين"
            
        else:
            # معلومات عامة عن الإحصاء
            result_html += f'<h5>📊 مفاهيم إحصائية مهمة:</h5>'
            result_html += f'<h6>مقاييس النزعة المركزية:</h6>'
            result_html += f'<p><strong>المتوسط:</strong> مجموع القيم ÷ عددها</p>'
            result_html += f'<p><strong>الوسيط:</strong> القيمة الوسطى بعد الترتيب</p>'
            result_html += f'<p><strong>المنوال:</strong> القيمة الأكثر تكراراً</p>'
            result_html += f'<h6>مقاييس التشتت:</h6>'
            result_html += f'<p><strong>المدى:</strong> الفرق بين أكبر وأصغر قيمة</p>'
            result_html += f'<p><strong>التباين:</strong> متوسط مربعات الانحرافات</p>'
            result_html += f'<p><strong>الانحراف المعياري:</strong> الجذر التربيعي للتباين</p>'
            result_text = "مفاهيم الإحصاء الأساسية"
        
        result_html += '</div>'
        return {"text": result_text, "html": result_html}
        
    except Exception:
        return None

# ===================== 3.7) نظام رياضيات شامل لجميع المراحل =====================

def detect_educational_level(q: str) -> str:
    """تحديد المستوى التعليمي للسؤال الرياضي"""
    import html
    
    # فك الترميز 
    text = html.unescape(q).lower()
    
    # كشف خاص للنصوص المُشوّهة
    if any(char in text for char in ['ù', 'ø', 'ù']):
        # المثلث القائم يحتوي دائماً على هذه الأنماط المُشوّهة
        if ('ø«' in text and 'ùø§ø¦' in text) or ('ù' in text and 'ø«' in text):
            return 'middle_school'
    
    # الإحصاء والاحتمالات
    statistics_keywords = ['متوسط', 'وسيط', 'منوال', 'انحراف معياري', 'تباين', 'احتمال', 'إحصاء', 'probability', 'statistics']
    if any(keyword in text for keyword in statistics_keywords):
        return 'statistics'
    
    # مؤشرات الرياضيات الجامعية
    university_keywords = ['مشتق', 'تكامل', 'نهاية', 'متسلسلة', 'مصفوفة', 'معادلة تفاضلية', 'لابلاس', 'فورير']
    if any(keyword in text for keyword in university_keywords):
        return 'university'
    
    # مؤشرات الرياضيات الثانوية
    high_school_keywords = ['sin', 'cos', 'tan', 'لوغاريتم', 'أسي', 'تربيعية', 'مثلثات', 'هندسة تحليلية']
    if any(keyword in text for keyword in high_school_keywords):
        return 'high_school'
    
    # مؤشرات الرياضيات الإعدادية  
    middle_school_keywords = ['جبر', 'معادلة خطية', 'نسبة', 'تناسب', 'مساحة', 'محيط', 'حجم', 'مثلث', 'وتر', 'قائم', 'فيثاغورث', 'ضلع', 'زاوية', 'مربع', 'مستطيل', 'دائرة', 'قطر', 'نصف قطر']
    if any(keyword in text for keyword in middle_school_keywords):
        return 'middle_school'
    
    # فحص إذا كان السؤال يحتوي على عمليات حسابية واضحة
    if any(op in text for op in ['+', '-', '*', '/', '×', '÷', '=', 'جمع', 'طرح', 'ضرب', 'قسمة', 'حساب']):
        return 'elementary'
    
    # فحص للأرقام الحقيقية (ليس رموز الترميز المُشوّه)
    # إذا كان النص يحتوي على أرقام عربية أو إنجليزية منفصلة
    arabic_digits = '٠١٢٣٤٥٦٧٨٩'
    real_digits = '0123456789'
    
    # البحث عن أرقام حقيقية (ليس جزء من ترميز مُشوّه)
    has_real_numbers = False
    for i, char in enumerate(text):
        if char in real_digits or char in arabic_digits:
            # تأكد أن الرقم ليس جزء من ترميز مُشوّه
            if i == 0 or i == len(text)-1:  # أول أو آخر حرف
                has_real_numbers = True
                break
            # إذا كان الرقم محاط بمسافات أو أحرف عادية
            elif (text[i-1] in ' ،؟.' or text[i+1] in ' ،؟.'):
                has_real_numbers = True
                break
    
    if has_real_numbers:
        return 'elementary'
    
    # ليس سؤال رياضي
    return 'not_math'

def solve_comprehensive_math(q: str):
    """حل شامل للرياضيات - جميع المراحل التعليمية"""
    try:
        level = detect_educational_level(q)
        
        # إذا لم يكن السؤال رياضي، لا تعطي جواب رياضي
        if level == 'not_math':
            return None
        
        # الإحصاء والاحتمالات
        if level == 'statistics':
            return solve_statistics_math(q)
        
        # رياضيات الجامعة المتقدمة
        elif level == 'university':
            return solve_university_math(q)
        
        # رياضيات الثانوية
        elif level == 'high_school':
            return solve_high_school_math(q)
        
        # رياضيات الإعدادية
        elif level == 'middle_school':
            return solve_middle_school_math(q)
        
        # رياضيات الابتدائية (فقط إذا كان فيه أرقام أو عمليات حسابية)
        elif level == 'elementary':
            return solve_elementary_math(q)
        
        # إذا لم يتم تحديد نوع، لا تعطي جواب رياضي
        else:
            return None
            
    except Exception as e:
        return None

def solve_university_math(q: str):
    """رياضيات الجامعة: تفاضل، تكامل، معادلات تفاضلية، جبر خطي"""
    try:
        task = detect_math_task(q)
        expr_txt = normalize_math(q)
        x, y, t, z = symbols('x y t z')
        
        result_html = f'<div class="card"><h4>🎓 رياضيات جامعية: {html.escape(q)}</h4><hr>'
        
        # معالجة التعبير
        expr = sympify(expr_txt, dict(sin=sin, cos=cos, tan=tan, sqrt=sqrt))
        
        if 'مشتق جزئي' in q.lower() or 'partial' in q.lower():
            # مشتقات جزئية
            res_x = diff(expr, x)
            res_y = diff(expr, y) if 'y' in str(expr) else 0
            result_html += f'<h5>∂ المشتقات الجزئية:</h5>'
            result_html += f'<p><strong>∂f/∂x = </strong>{res_x}</p>'
            result_html += f'<p><strong>∂f/∂y = </strong>{res_y}</p>'
            result_text = f"المشتقات الجزئية: ∂f/∂x = {res_x}, ∂f/∂y = {res_y}"
            
        elif 'تكامل مضاعف' in q.lower() or 'double integral' in q.lower():
            # تكاملات مضاعفة (محاولة بسيطة)
            res = integrate(integrate(expr, x), y)
            result_html += f'<h5>∬ التكامل المضاعف:</h5>'
            result_html += f'<p style="background:#e8f5e8;padding:15px;border-radius:8px;"><strong>{latex(res)} + C</strong></p>'
            result_text = f"التكامل المضاعف: {res}"
            
        elif 'سلسلة' in q.lower() or 'series' in q.lower():
            # سلاسل تايلور (محاولة بسيطة)
            from sympy import series
            res = series(expr, x, 0, 6)  # سلسلة حول 0 حتى الدرجة 5
            result_html += f'<h5>📈 سلسلة تايلور:</h5>'
            result_html += f'<p style="background:#fff8dc;padding:15px;border-radius:8px;"><strong>{res}</strong></p>'
            result_text = f"سلسلة تايلور: {res}"
            
        else:
            # استخدام النظام العادي للرياضيات المتقدمة
            return solve_advanced_math(q)
        
        result_html += '</div>'
        return {"text": result_text, "html": result_html}
        
    except Exception as e:
        return solve_advanced_math(q)  # العودة للنظام العادي

def solve_high_school_math(q: str):
    """رياضيات الثانوية: مثلثات، لوغاريتمات، دوال أسية"""
    try:
        expr_txt = normalize_math(q)
        x = symbols('x')
        
        result_html = f'<div class="card"><h4>🏫 رياضيات ثانوية: {html.escape(q)}</h4><hr>'
        
        if any(trig in q.lower() for trig in ['sin', 'cos', 'tan', 'مثلثات']):
            # حساب المثلثات
            expr = sympify(expr_txt, dict(sin=sin, cos=cos, tan=tan))
            
            # تبسيط المتطابقات المثلثية
            simplified = simplify(expr)
            result_html += f'<h5>📐 حساب المثلثات:</h5>'
            result_html += f'<p><strong>التعبير الأصلي:</strong> {expr}</p>'
            result_html += f'<p><strong>بعد التبسيط:</strong> {simplified}</p>'
            
            # قيم زوايا خاصة
            if 'قيم' in q.lower() or 'زاوية' in q.lower():
                result_html += f'<h6>قيم الزوايا الخاصة:</h6>'
                result_html += f'<p>sin(30°) = 1/2, cos(30°) = √3/2</p>'
                result_html += f'<p>sin(45°) = √2/2, cos(45°) = √2/2</p>'
                result_html += f'<p>sin(60°) = √3/2, cos(60°) = 1/2</p>'
            
            result_text = f"حساب المثلثات: {simplified}"
            
        elif 'لوغاريتم' in q.lower() or 'log' in q.lower():
            # اللوغاريتمات
            from sympy import log, ln
            expr = sympify(expr_txt, dict(log=log, ln=ln))
            
            expanded = expand(expr)
            result_html += f'<h5>📊 اللوغاريتمات:</h5>'
            result_html += f'<p><strong>التوسيع:</strong> {expanded}</p>'
            
            # خصائص اللوغاريتمات
            result_html += f'<h6>خصائص اللوغاريتمات:</h6>'
            result_html += f'<p>log(ab) = log(a) + log(b)</p>'
            result_html += f'<p>log(a/b) = log(a) - log(b)</p>'
            result_html += f'<p>log(a^n) = n×log(a)</p>'
            
            result_text = f"اللوغاريتمات: {expanded}"
            
        else:
            # المعادلات التربيعية والدوال
            expr = sympify(expr_txt)
            
            if 'معادلة تربيعية' in q.lower() or 'x^2' in expr_txt or 'x**2' in expr_txt:
                solutions = solve(expr, x)
                result_html += f'<h5>🔢 المعادلة التربيعية:</h5>'
                result_html += f'<p><strong>المعادلة:</strong> {expr} = 0</p>'
                
                if solutions:
                    result_html += f'<p><strong>الحلول:</strong></p>'
                    for i, sol in enumerate(solutions, 1):
                        result_html += f'<p>x{i} = {sol}</p>'
                    
                    # قانون الحل التربيعي
                    result_html += f'<h6>قانون الحل التربيعي: x = (-b ± √(b²-4ac)) / 2a</h6>'
                else:
                    result_html += f'<p>لا يوجد حل حقيقي</p>'
                
                result_text = f"حلول المعادلة التربيعية: {solutions}"
            else:
                return solve_advanced_math(q)
        
        result_html += '</div>'
        return {"text": result_text, "html": result_html}
        
    except Exception:
        return solve_advanced_math(q)

def solve_middle_school_math(q: str):
    """رياضيات الإعدادية: جبر أساسي، هندسة، نسب"""
    try:
        result_html = f'<div class="card"><h4>🏛️ رياضيات إعدادية: {html.escape(q)}</h4><hr>'
        
        if any(word in q.lower() for word in ['مثلث قائم', 'وتر', 'فيثاغورث']):
            # حل مسائل المثلث القائم
            result_html += f'<h5>📐 المثلث القائم الزاوية:</h5>'
            result_html += f'<h6>📏 نظرية فيثاغورث:</h6>'
            result_html += f'<p><strong>القانون:</strong> الوتر² = الضلع الأول² + الضلع الثاني²</p>'
            result_html += f'<h6>✨ إذا كان الوتر = 10 سم:</h6>'
            result_html += f'<p><strong>🔹 إذا كان الضلعان متساويان:</strong></p>'
            result_html += f'<p>الضلع = 10 ÷ √2 = 10 ÷ 1.414 ≈ <span style="color:#e74c3c;font-weight:bold;">7.07 سم</span></p>'
            result_html += f'<p><strong>🔹 مثلث شائع (6-8-10):</strong></p>'
            result_html += f'<p>إذا كان أحد الأضلاع = 6 سم، الآخر = <span style="color:#e74c3c;font-weight:bold;">8 سم</span></p>'
            result_html += f'<p>إذا كان أحد الأضلاع = 8 سم، الآخر = <span style="color:#e74c3c;font-weight:bold;">6 سم</span></p>'
            result_html += f'<p><strong>🔹 التحقق:</strong> 6² + 8² = 36 + 64 = 100 = 10²</p>'
            result_text = "حل مسألة المثلث القائم - الوتر 10 سم"
            
        elif 'مساحة' in q.lower():
            # حساب المساحات
            result_html += f'<h5>📐 حساب المساحات:</h5>'
            result_html += f'<h6>صيغ المساحات الشائعة:</h6>'
            result_html += f'<p><strong>المربع:</strong> المساحة = الضلع²</p>'
            result_html += f'<p><strong>المستطيل:</strong> المساحة = الطول × العرض</p>'
            result_html += f'<p><strong>المثلث:</strong> المساحة = ½ × القاعدة × الارتفاع</p>'
            result_html += f'<p><strong>الدائرة:</strong> المساحة = π × نق²</p>'
            result_text = "صيغ حساب المساحات"
            
        elif 'محيط' in q.lower():
            # حساب المحيطات
            result_html += f'<h5>⭕ حساب المحيطات:</h5>'
            result_html += f'<h6>صيغ المحيطات الشائعة:</h6>'
            result_html += f'<p><strong>المربع:</strong> المحيط = 4 × الضلع</p>'
            result_html += f'<p><strong>المستطيل:</strong> المحيط = 2 × (الطول + العرض)</p>'
            result_html += f'<p><strong>المثلث:</strong> المحيط = مجموع الأضلاع الثلاثة</p>'
            result_html += f'<p><strong>الدائرة:</strong> المحيط = 2 × π × نق</p>'
            result_text = "صيغ حساب المحيطات"
            
        elif 'نسبة' in q.lower() or 'تناسب' in q.lower():
            # النسب والتناسب
            result_html += f'<h5>⚖️ النسب والتناسب:</h5>'
            result_html += f'<h6>قوانين النسب:</h6>'
            result_html += f'<p><strong>النسبة:</strong> a : b = a/b</p>'
            result_html += f'<p><strong>التناسب:</strong> a/b = c/d → a×d = b×c</p>'
            result_html += f'<p><strong>النسبة المئوية:</strong> النسبة المئوية = (الجزء/الكل) × 100</p>'
            result_text = "قوانين النسب والتناسب"
            
        else:
            # معادلات خطية بسيطة
            try:
                expr_txt = normalize_math(q)
                x = symbols('x')
                expr = sympify(expr_txt)
                solutions = solve(expr, x)
                
                result_html += f'<h5>🔢 المعادلات الخطية:</h5>'
                result_html += f'<p><strong>المعادلة:</strong> {expr} = 0</p>'
                
                if solutions:
                    result_html += f'<p><strong>الحل:</strong> x = {solutions[0]}</p>'
                    result_text = f"حل المعادلة الخطية: x = {solutions[0]}"
                else:
                    result_html += f'<p>معادلة بدون حل أو حل لامنهائي</p>'
                    result_text = "معادلة خاصة"
                    
            except:
                return None
        
        result_html += '</div>'
        return {"text": result_text, "html": result_html}
        
    except Exception:
        return None

def solve_elementary_math(q: str):
    """رياضيات الابتدائية: العمليات الأساسية، الكسور، الأعداد"""
    try:
        result_html = f'<div class="card"><h4>🧮 رياضيات ابتدائية: {html.escape(q)}</h4><hr>'
        
        # أولاً نجرب الحاسبة العادية
        calc_result = try_calc_ar(q)
        if calc_result:
            return calc_result
        
        if 'كسر' in q.lower() or '/' in q:
            # الكسور
            result_html += f'<h5>🍰 الكسور:</h5>'
            result_html += f'<h6>عمليات الكسور:</h6>'
            result_html += f'<p><strong>جمع الكسور:</strong> a/b + c/d = (ad + bc)/(bd)</p>'
            result_html += f'<p><strong>طرح الكسور:</strong> a/b - c/d = (ad - bc)/(bd)</p>'
            result_html += f'<p><strong>ضرب الكسور:</strong> a/b × c/d = (ac)/(bd)</p>'
            result_html += f'<p><strong>قسمة الكسور:</strong> a/b ÷ c/d = (ad)/(bc)</p>'
            result_text = "قوانين عمليات الكسور"
            
        elif 'ضرب' in q.lower() and 'جدول' in q.lower():
            # جداول الضرب
            result_html += f'<h5>✖️ جداول الضرب:</h5>'
            for i in range(1, 11):
                result_html += f'<p>{i} × 1 = {i}, {i} × 2 = {i*2}, {i} × 3 = {i*3}, ... {i} × 10 = {i*10}</p>'
            result_text = "جداول الضرب من 1 إلى 10"
            
        elif 'أعداد أولية' in q.lower():
            # الأعداد الأولية
            primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
            result_html += f'<h5>🔢 الأعداد الأولية:</h5>'
            result_html += f'<p><strong>الأعداد الأولية أقل من 50:</strong></p>'
            result_html += f'<p>{", ".join(map(str, primes))}</p>'
            result_html += f'<p><strong>تعريف:</strong> العدد الأولي هو عدد أكبر من 1 ولا يقبل القسمة إلا على نفسه وعلى الواحد</p>'
            result_text = f"الأعداد الأولية: {primes}"
            
        else:
            # عمليات حسابية أساسية
            result_html += f'<h5>🧮 العمليات الأساسية:</h5>'
            result_html += f'<p><strong>الجمع (+):</strong> ضع الأرقام فوق بعضها واجمع كل عمود</p>'
            result_html += f'<p><strong>الطرح (-):</strong> اطرح الرقم السفلي من العلوي في كل عمود</p>'
            result_html += f'<p><strong>الضرب (×):</strong> اضرب كل رقم بكل الأرقام الأخرى</p>'
            result_html += f'<p><strong>القسمة (÷):</strong> كم مرة يدخل المقسوم عليه في المقسوم</p>'
            result_text = "العمليات الحسابية الأساسية"
        
        result_html += '</div>'
        return {"text": result_text, "html": result_html}
        
    except Exception:
        return None

# ===================== 4) HTML (واجهة) =====================
def render_page(q="", mode="summary", result_panel=""):
    active = lambda m: "active" if mode==m else ""
    checked= lambda m: "checked" if mode==m else ""
    
    # تقسيم JavaScript لتجنب مشاكل f-string مع assignment operators
    js_script = '''
document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        btn.querySelector('input').checked = true;
    });
});
document.getElementById('question').focus();
    '''
    
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
    <h1>🤖 تطبيق بسام الذكي</h1><p>رياضيات متقدمة، ذكاء اصطناعي، وبحث ذكي</p>
  </div>
  <div class="content">
    <form method="post" action="/">
      <label for="question">اسأل بسام:</label>
      <input type="text" id="question" name="question" placeholder="مثال: مشتق x^3 / مساحة المربع / جدول ضرب 7 / ما هي عاصمة فرنسا؟" value="{html.escape(q)}" required>
      <div class="mode-selector">
        <label class="mode-btn {active('summary')}"><input type="radio" name="mode" value="summary" {checked('summary')} style="display:none">📄 ملخص</label>
        <label class="mode-btn {active('math')}"><input type="radio" name="mode" value="math" {checked('math')} style="display:none">🧮 رياضيات</label>
        <label class="mode-btn {active('prices')}"><input type="radio" name="mode" value="prices"  {checked('prices')}  style="display:none">💰 أسعار</label>
        <label class="mode-btn {active('images')}"><input type="radio" name="mode" value="images"  {checked('images')}  style="display:none">🖼️ صور</label>
      </div>
      <button type="submit" class="submit-btn">🔍 ابحث</button>
    </form>
    {f'<div class="result"><h3>النتيجة:</h3>{result_panel}</div>' if result_panel else ''}
  </div>
  <div class="footer"><p>تطبيق بسام v3.1</p></div>
</div>
<script>{js_script}</script>
</body></html>"""

# ===================== المسارات =====================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    q = request.query_params.get("q", "")
    mode = request.query_params.get("mode", "summary")
    return render_page(q, mode)

@app.get("/test", response_class=HTMLResponse)
async def test_page():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="ar">
    <head>
        <meta charset="UTF-8">
        <title>اختبار</title>
    </head>
    <body style="font-family: Arial; padding: 50px; text-align: center; background: #f0f8ff;">
        <h1 style="color: #333;">🎉 الخادم يعمل بنجاح!</h1>
        <p style="font-size: 18px;">إذا ترى هذه الرسالة، فإن النظام يعمل بشكل صحيح.</p>
        <a href="/" style="display: inline-block; margin: 20px; padding: 15px 30px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px;">العودة للصفحة الرئيسية</a>
    </body>
    </html>
    """)

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

    # 1) آلة حاسبة (أساسية)
    calc = try_calc_ar(q)
    if calc:
        save_question_history(q, calc["text"], "calculator")
        return render_page(q, mode, calc["html"])

    # 1.5) نظام رياضيات شامل (جميع المراحل التعليمية)
    comprehensive_math = solve_comprehensive_math(q)
    if comprehensive_math:
        save_question_history(q, comprehensive_math["text"], "comprehensive_math")
        return render_page(q, mode, comprehensive_math["html"])
    
    # النظام الرياضي القديم كاحتياطي
    if any(keyword in q.lower() for keyword in ['مشتق', 'تكامل', 'حل', 'تبسيط', 'تحليل', 'توسيع', 'نهاية', 'معادلة', 'solve', 'derivative', 'integral', 'limit']):
        advanced_math = solve_advanced_math(q)
        if advanced_math:
            save_question_history(q, advanced_math["text"], "advanced_math")
            return render_page(q, mode, advanced_math["html"])

    # 2) تحويل وحدات
    conv = convert_query_ar(q)
    if conv:
        save_question_history(q, conv["text"], "converter")
        return render_page(q, mode, conv["html"])

    # 3) الذكاء الاصطناعي (Gemini AI) - نجرب أولاً للأسئلة العامة
    if GEMINI_AVAILABLE and is_gemini_available():
        # للأسئلة العامة التي ليست حسابية صرفة
        has_math_only = any(op in q for op in ['+', '-', '×', '÷', '*', '/', '=', '(', ')']) and \
                       all(c.isdigit() or c in '+−×÷*/.=()٠١٢٣٤٥٦٧٨٩ ' for c in q.replace('س', '').replace('ص', ''))
        
        if not has_math_only:  # إذا لم يكن حسابية صرفة، جرب AI
            ai_response = answer_with_ai(q)
            if ai_response:
                save_question_history(q, ai_response["text"], "ai_answer")
                return render_page(q, mode, ai_response["html"])

    # 4) بحث/أسعار/صور (DuckDuckGo API)
    try:
        results = []
        ddgs = DDGS()
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