from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
import httpx, re, ast, math
from bs4 import BeautifulSoup

# --- للتلخيص والترتيب ---
try:
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.parsers.plaintext import PlainTextParser
    from sumy.summarizers.text_rank import TextRankSummarizer
    from rank_bm25 import BM25Okapi
    from rapidfuzz import fuzz
    import numpy as np
    SUMY_AVAILABLE = True
except ImportError:
    SUMY_AVAILABLE = False

app = FastAPI(title="Bassam App", version="3.0")

# ===================== أدوات عامة =====================
AR_NUM = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
def _to_float(s: str):
    s = (s or "").strip().translate(AR_NUM).replace(",", "")
    try: return float(s)
    except: return None

# ===================== 1) آلة حاسبة موسعة =====================
REPL = {
    "÷": "/", "×": "*", "−": "-", "–": "-", "—": "-",
    "^": "**", "أس": "**", "اس": "**",
    "جذر": "sqrt", "الجذر": "sqrt", "√": "sqrt",
    "%": "/100",
}
def _normalize_expr(s: str) -> str:
    s = (s or "").strip()
    for k, v in REPL.items():
        s = s.replace(k, v)
    s = s.replace("على", "/").replace("في", "*")
    s = s.translate(AR_NUM)
    s = s.replace("٬", "").replace(",", "")
    return s

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
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError("رموز غير مدعومة")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_FUNCS:
                raise ValueError("دالة غير مسموحة")
        if isinstance(node, ast.Name) and node.id not in SAFE_FUNCS:
            raise ValueError("اسم غير مسموح")
    return eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}}, SAFE_FUNCS)

def try_calc_ar(question: str):
    if not question: return None
    has_digit = any(ch.isdigit() for ch in question.translate(AR_NUM))
    has_op = any(op in question for op in ["+", "-", "×", "÷", "*", "/", "^", "أس", "√", "جذر", "(", ")", "%"])
    if not (has_digit and has_op): return None
    
    expr = _normalize_expr(question)
    try:
        # حساب النتيجة النهائية
        final_result = _safe_eval(expr)
        
        # تحليل التعبير وعرض الخطوات
        steps = _analyze_expression(question, expr, final_result)
        
        return {"text": f"النتيجة النهائية: {final_result}", "html": steps}
    except Exception:
        return None

def _analyze_expression(original: str, expr: str, final_result: float):
    """تحليل التعبير الرياضي وعرض الخطوات التفصيلية مثل ChatGPT"""
    steps_html = f'<div class="card"><h4>📐 المسألة: {original}</h4><hr>'
    
    import re
    step_num = 1
    calculations = []
    
    # البحث عن الدوال الرياضية وحسابها بالتفصيل
    func_patterns = [
        (r'sin\(([^)]+)\)', 'sin', lambda x: math.sin(math.radians(x))),
        (r'cos\(([^)]+)\)', 'cos', lambda x: math.cos(math.radians(x))),
        (r'tan\(([^)]+)\)', 'tan', lambda x: math.tan(math.radians(x))),
        (r'sqrt\(([^)]+)\)', 'sqrt', math.sqrt),
        (r'ln\(([^)]+)\)', 'ln', math.log),
        (r'log\(([^)]+)\)', 'log', lambda x: math.log(x, 10)),
    ]
    
    current_expr = expr
    
    # خطوة 1: حساب الدوال الرياضية
    steps_html += f'<h5>🔍 الحل:</h5>'
    
    for pattern, func_name, func in func_patterns:
        matches = list(re.finditer(pattern, current_expr))
        for match in matches:
            try:
                value = float(match.group(1))
                result = func(value)
                
                if func_name in ['sin', 'cos', 'tan']:
                    # إضافة تفاصيل أكثر للدوال المثلثية
                    if func_name == 'sin' and value == 30:
                        steps_html += f'<p><strong>{step_num}.</strong> sin(30°) = <span style="color: #2196F3;">0.5</span> ✓</p>'
                    elif func_name == 'cos' and value == 60:
                        steps_html += f'<p><strong>{step_num}.</strong> cos(60°) = <span style="color: #2196F3;">0.5</span> ✓</p>'
                    elif func_name in ['sin', 'cos'] and value == 45:
                        steps_html += f'<p><strong>{step_num}.</strong> {func_name}(45°) = √2/2 ≈ <span style="color: #2196F3;">{result:.4f}</span> ✓</p>'
                    else:
                        steps_html += f'<p><strong>{step_num}.</strong> {func_name}({value}°) = <span style="color: #2196F3;">{result:.4f}</span></p>'
                else:
                    steps_html += f'<p><strong>{step_num}.</strong> {func_name}({value}) = <span style="color: #2196F3;">{result:.4f}</span></p>'
                
                calculations.append((func_name, value, result))
                current_expr = current_expr.replace(match.group(0), str(result))
                step_num += 1
                
            except:
                continue
    
    # البحث عن العمليات الخاصة (جذور، أسس)
    if '√' in original or 'جذر' in original:
        sqrt_matches = re.finditer(r'√(\d+)', original)
        for match in sqrt_matches:
            value = float(match.group(1))
            result = math.sqrt(value)
            steps_html += f'<p><strong>{step_num}.</strong> √{value} = <span style="color: #2196F3;">{result:.4f}</span></p>'
            step_num += 1
    
    # خطوة 2: إظهار العمليات التفصيلية
    if len(calculations) > 0:
        steps_html += f'<h5>🧮 التطبيق في المعادلة:</h5>'
        
        # إعادة كتابة المعادلة مع النتائج
        display_expr = original
        for func_name, value, result in calculations:
            if func_name in ['sin', 'cos', 'tan']:
                pattern = f'{func_name}({value})'
                if value == 30 and func_name == 'sin':
                    replacement = f'<span style="color: #2196F3;">0.5</span>'
                elif value == 60 and func_name == 'cos':
                    replacement = f'<span style="color: #2196F3;">0.5</span>'
                elif value == 45 and func_name in ['sin', 'cos']:
                    replacement = f'<span style="color: #2196F3;">{result:.4f}</span>'
                else:
                    replacement = f'<span style="color: #2196F3;">{result:.4f}</span>'
                display_expr = display_expr.replace(pattern, replacement)
        
        steps_html += f'<p><strong>{step_num}.</strong> {display_expr}</p>'
        step_num += 1
        
        # خطوة 3: الحساب النهائي إذا كان هناك عمليات
        if '*' in current_expr or '+' in current_expr:
            # إظهار عمليات الضرب أولاً
            if '*' in current_expr:
                multiply_parts = current_expr.split('*')
                if len(multiply_parts) == 2:
                    try:
                        val1, val2 = float(multiply_parts[0].strip()), float(multiply_parts[1].strip())
                        multiply_result = val1 * val2
                        steps_html += f'<p><strong>{step_num}.</strong> {val1:.4f} × {val2:.4f} = <span style="color: #4CAF50;">{multiply_result:.4f}</span></p>'
                        current_expr = current_expr.replace(f'{multiply_parts[0]}*{multiply_parts[1]}', str(multiply_result))
                        step_num += 1
                    except:
                        pass
            
            # ثم إظهار عمليات الجمع
            if '+' in current_expr:
                parts = current_expr.split('+')
                if len(parts) > 1:
                    try:
                        values = [float(p.strip()) for p in parts]
                        sum_display = ' + '.join([f'{v:.1f}' for v in values])
                        steps_html += f'<p><strong>{step_num}.</strong> {sum_display} = <span style="color: #4CAF50;">{final_result:.1f}</span></p>'
                    except:
                        pass
    
    # النتيجة النهائية
    steps_html += f'<hr><h4 style="color: #4facfe; text-align: center;">🎯 إذن المجموع: <span style="font-size: 1.3em;">{final_result:.1f}</span></h4></div>'
    
    return steps_html

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
def _norm_unit(u: str):
    return ALL_ALIASES.get((u or "").strip().lower().translate(AR_NUM), "")
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
    html=f'<div class="card"><strong>النتيجة:</strong> {text}</div>'
    return {"text":text,"html":html}

# ===================== 3) تلخيص متقدم =====================
AR_SPLIT_RE = re.compile(r'(?<=[\.\!\?\؟])\s+|\n+')
def _sent_tokenize_ar(text: str):
    sents = [s.strip() for s in AR_SPLIT_RE.split(text or "") if len(s.strip()) > 0]
    return [s for s in sents if len(s) >= 20]
def bm25_rank_sentences(question: str, sentences: list, top_k=12):
    if not SUMY_AVAILABLE:
        return sentences[:top_k]
    def tok(s): 
        s = s.lower()
        s = re.sub(r"[^\w\s\u0600-\u06FF]+", " ", s)
        return s.split()
    corpus_tokens = [tok(s) for s in sentences]
    bm25 = BM25Okapi(corpus_tokens) if corpus_tokens else None
    if not bm25: return sentences[:top_k]
    scores = bm25.get_scores(tok(question))
    idx = np.argsort(scores)[::-1][:top_k]
    return [sentences[i] for i in idx]
def fuzz_boost(question: str, sentences: list, top_k=6):
    if not SUMY_AVAILABLE:
        return sentences[:top_k]
    scored = [(fuzz.token_set_ratio(question, s), s) for s in sentences]
    scored.sort(reverse=True, key=lambda x: x[0])
    return [s for _, s in scored[:top_k]]
def textrank_summary(text: str, max_sentences=4):
    if SUMY_AVAILABLE:
        try:
            parser = PlainTextParser.from_string(text, Tokenizer("english"))
            summarizer = TextRankSummarizer()
            if len(text.split()) < 80:
                return text.strip()
            summary_sents = summarizer(parser.document, max_sentences)
            return " ".join(str(s).strip() for s in summary_sents)
        except:
            pass
    # fallback - simple sentence selection
    sentences = text.split('.')
    return '. '.join(sentences[:max_sentences]).strip()
def summarize_advanced(question: str, page_texts: list, max_final_sents=4):
    candidate_sents = []
    for t in page_texts:
        sents = _sent_tokenize_ar(t)[:200]
        candidate_sents.extend(sents)
    if not candidate_sents: return ""
    bm25_top = bm25_rank_sentences(question, candidate_sents, top_k=30)
    boosted = fuzz_boost(question, bm25_top, top_k=12)
    merged = " ".join(boosted)
    draft = textrank_summary(merged, max_sentences=max_final_sents)
    if len(draft.split()) < 30:
        return " ".join(boosted[:max_final_sents])
    return draft

# ===================== 4) مسارات التطبيق =====================

def render_page(q="", mode="summary", result_panel=""):
    """إنشاء صفحة HTML"""
    active_summary = "active" if mode == "summary" else ""
    active_prices = "active" if mode == "prices" else ""  
    active_images = "active" if mode == "images" else ""
    
    checked_summary = "checked" if mode == "summary" else ""
    checked_prices = "checked" if mode == "prices" else ""
    checked_images = "checked" if mode == "images" else ""
    
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 تطبيق بسام</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            direction: rtl;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 10px; }}
        .header p {{ font-size: 1.1rem; opacity: 0.9; }}
        .content {{ padding: 30px; }}
        .form-group {{ margin-bottom: 20px; }}
        label {{ display: block; margin-bottom: 8px; font-weight: bold; color: #333; }}
        input[type="text"] {{
            width: 100%;
            padding: 15px;
            border: 2px solid #e1e5e9;
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.3s ease;
        }}
        input[type="text"]:focus {{
            outline: none;
            border-color: #4facfe;
            box-shadow: 0 0 0 3px rgba(79, 172, 254, 0.1);
        }}
        .mode-selector {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .mode-btn {{
            flex: 1;
            min-width: 120px;
            padding: 12px 20px;
            border: 2px solid #e1e5e9;
            background: white;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
            font-weight: bold;
        }}
        .mode-btn:hover {{
            border-color: #4facfe;
            background: #f8fbff;
        }}
        .mode-btn.active {{
            background: #4facfe;
            color: white;
            border-color: #4facfe;
        }}
        .submit-btn {{
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        .submit-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }}
        .result {{
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border-right: 4px solid #4facfe;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin: 10px 0;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            border-top: 1px solid #eee;
        }}
        @media (max-width: 600px) {{
            .mode-selector {{ flex-direction: column; }}
            .mode-btn {{ min-width: auto; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 تطبيق بسام</h1>
            <p>آلة حاسبة، محول وحدات، وبحث ذكي</p>
        </div>
        
        <div class="content">
            <form method="post" action="/">
                <div class="form-group">
                    <label for="question">اسأل بسام:</label>
                    <input type="text" 
                           id="question" 
                           name="question" 
                           placeholder="مثال: 5 + 3 × 2 أو كم يساوي كيلو بالرطل؟ أو ما هو الذكاء الاصطناعي؟"
                           value="{q}"
                           required>
                </div>
                
                <div class="mode-selector">
                    <label class="mode-btn {active_summary}">
                        <input type="radio" name="mode" value="summary" {checked_summary} style="display: none;">
                        📄 ملخص
                    </label>
                    <label class="mode-btn {active_prices}">
                        <input type="radio" name="mode" value="prices" {checked_prices} style="display: none;">
                        💰 أسعار
                    </label>
                    <label class="mode-btn {active_images}">
                        <input type="radio" name="mode" value="images" {checked_images} style="display: none;">
                        🖼️ صور
                    </label>
                </div>
                
                <button type="submit" class="submit-btn">🔍 ابحث</button>
            </form>
            
            {f'<div class="result"><h3>النتيجة:</h3>{result_panel}</div>' if result_panel else ''}
        </div>
        
        <div class="footer">
            <p>تطبيق بسام v3.0 - آلة حاسبة ومحول وحدات وبحث ذكي</p>
        </div>
    </div>
    
    <script>
        // تفعيل أزرار الأوضاع
        document.querySelectorAll('.mode-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                btn.querySelector('input').checked = true;
            }});
        }});
        
        // تركيز تلقائي على خانة البحث
        document.getElementById('question').focus();
    </script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return render_page()

@app.post("/", response_class=HTMLResponse) 
async def run(question: str = Form(...), mode: str = Form("summary")):
    q = (question or "").strip()
    
    if not q:
        return render_page()

    # آلة حاسبة
    calc = try_calc_ar(q)
    if calc:
        return render_page(q, mode, calc["html"])

    # تحويل وحدات
    conv = convert_query_ar(q)
    if conv:
        return render_page(q, mode, conv["html"])

    # بحث/أسعار/صور
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get("https://duckduckgo.com/html/", params={"q": q})
            soup = BeautifulSoup(r.text,"html.parser")
            snippets=[re.sub(r"\s+"," ",el.get_text()) for el in soup.select(".result__snippet")]
            links=[a.get("href") for a in soup.select(".result__a")]

        if mode=="summary":
            page_texts = snippets[:3]
            final_answer = summarize_advanced(q, page_texts, max_final_sents=4)
            if not final_answer:
                final_answer = " ".join(snippets[:3]) if snippets else "لم أجد ملخصًا."
            result_panel = f'<div class="card">{final_answer}</div>'
        elif mode=="prices":
            parts=[]
            for s,a in zip(snippets,links):
                if any(x in s for x in ["$","USD","SAR","ر.س","AED","د.إ","EGP","ج.م"]):
                    parts.append(f'<div class="card">{s} — <a target="_blank" href="{a}">فتح المصدر</a></div>')
                if len(parts)>=8: break
            result_panel = "".join(parts) if parts else '<div class="card">لم أجد أسعارًا واضحة.</div>'
        elif mode=="images":
            result_panel = f'<div class="card"><a target="_blank" href="https://duckduckgo.com/?q={q}&iax=images&ia=images">افتح نتائج الصور 🔗</a></div>'
        else:
            result_panel = '<div class="card">وضع غير معروف</div>'
    except Exception as e:
        result_panel = f'<div class="card">خطأ: {e}</div>'

    return render_page(q, mode, result_panel)

@app.get("/healthz")
async def healthz():
    return {"status":"ok"}