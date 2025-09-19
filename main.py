from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx, re, ast, math
from bs4 import BeautifulSoup

app = FastAPI(title="Bassam App", version="2.0")

# ربط الملفات
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

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
        val = _safe_eval(expr)
        out = f"النتيجة ≈ {val:,.6f}".replace(",", "،")
        html = f'<div class="card"><strong>النتيجة:</strong> {out}</div>'
        return {"text": out, "html": html}
    except Exception:
        return None

# ===================== 2) محولات وحدات =====================
# أوزان
WEIGHT_ALIASES = {"كيلو":"kg","كيلوجرام":"kg","كجم":"kg","كغ":"kg","kg":"kg","جرام":"g","غ":"g","g":"g","ملغم":"mg","mg":"mg","رطل":"lb","باوند":"lb","lb":"lb","أوقية":"oz","اونصة":"oz","oz":"oz","طن":"t","t":"t"}
W_TO_KG = {"kg":1.0,"g":0.001,"mg":1e-6,"lb":0.45359237,"oz":0.028349523125,"t":1000.0}

# أطوال
LENGTH_ALIASES = {"مم":"mm","mm":"mm","سم":"cm","cm":"cm","م":"m","متر":"m","m":"m","كم":"km","km":"km","إنش":"in","بوصة":"in","in":"in","قدم":"ft","ft":"ft","ياردة":"yd","yd":"yd","ميل":"mi","mi":"mi"}
L_TO_M = {"mm":0.001,"cm":0.01,"m":1.0,"km":1000.0,"in":0.0254,"ft":0.3048,"yd":0.9144,"mi":1609.344}

# أحجام سائلة
VOLUME_ALIASES = {"مل":"ml","ml":"ml","ل":"l","لتر":"l","l":"l","كوب":"cup","cup":"cup","ملعقة":"tbsp","tbsp":"tbsp","ملعقة صغيرة":"tsp","tsp":"tsp","غالون":"gal","gal":"gal"}
V_TO_L = {"ml":0.001,"l":1.0,"cup":0.236588,"tbsp":0.0147868,"tsp":0.0049289,"gal":3.78541}

# مساحات
AREA_ALIASES = {"م2":"m2","متر مربع":"m2","cm2":"cm2","سم2":"cm2","km2":"km2","كم2":"km2","ft2":"ft2","قدم2":"ft2","in2":"in2","إنش2":"in2","ha":"ha","هكتار":"ha","mi2":"mi2","ميل2":"mi2"}
A_TO_M2 = {"m2":1.0,"cm2":0.0001,"km2":1_000_000.0,"ft2":0.092903,"in2":0.00064516,"ha":10_000.0,"mi2":2_589_988.11}

# حجوم مكعبة
VOLUME3_ALIASES = {"م3":"m3","متر مكعب":"m3","cm3":"cm3","سم3":"cm3","l":"l","ل":"l","ml":"ml","مل":"ml","ft3":"ft3","قدم3":"ft3","in3":"in3","إنش3":"in3","gal":"gal","غالون":"gal"}
V3_TO_M3 = {"m3":1.0,"cm3":1e-6,"l":0.001,"ml":1e-6,"ft3":0.0283168,"in3":1.6387e-5,"gal":0.00378541}

# نوع الوحدة
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

# ===================== 3) مسارات التطبيق =====================
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/", response_class=HTMLResponse)
async def run(request: Request, question: str = Form(...), mode: str = Form("summary")):
    q = (question or "").strip()
    answer_text = ""; result_panel = ""

    # آلة حاسبة
    calc = try_calc_ar(q)
    if calc:
        return templates.TemplateResponse("index.html", {"request":request,"q":q,"mode":mode,"answer_text":calc["text"],"result_panel":calc["html"]})

    # تحويل وحدات
    conv = convert_query_ar(q)
    if conv:
        return templates.TemplateResponse("index.html", {"request":request,"q":q,"mode":mode,"answer_text":conv["text"],"result_panel":conv["html"]})

    # بحث/أسعار/صور من DuckDuckGo
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get("https://duckduckgo.com/html/", params={"q": q})
            soup = BeautifulSoup(r.text,"html.parser")
            snippets=[re.sub(r"\s+"," ",el.get_text()) for el in soup.select(".result__snippet")]
            links=[a.get("href") for a in soup.select(".result__a")]

        if mode=="summary":
            parts=snippets[:3]
            answer_text=" ".join(parts) if parts else "لم أجد ملخصًا."
            result_panel="<br>".join(parts) if parts else "لم أجد ملخصًا."
        elif mode=="prices":
            parts=[]
            for s,a in zip(snippets,links):
                if any(x in s for x in ["$","USD","SAR","ر.س","AED","د.إ","EGP","ج.م"]):
                    parts.append(f"{s} — <a target='_blank' href='{a}'>فتح المصدر</a>")
                if len(parts)>=8: break
            answer_text=" ".join(parts) if parts else "لم أجد أسعارًا واضحة."
            result_panel="<br>".join(parts) if parts else "لم أجد أسعارًا."
        elif mode=="images":
            result_panel=f"<div class='card'><a target='_blank' href='https://duckduckgo.com/?q={q}&iax=images&ia=images'>افتح نتائج الصور 🔗</a></div>"
            answer_text="نتائج صور — افتح الرابط."
        else:
            answer_text="وضع غير معروف"; result_panel="وضع غير معروف"
    except Exception as e:
        answer_text=f"خطأ: {e}"; result_panel=answer_text

    return templates.TemplateResponse("index.html", {"request":request,"q":q,"mode":mode,"answer_text":answer_text,"result_panel":result_panel})

@app.get("/healthz")
async def healthz():
    return {"status":"ok"}