# -*- coding: utf-8 -*-
"""
Math Skill v7 — Arabic understanding + LaTeX steps
يعالج:
- أوامر طبيعية بالعربية: "أوجد مشتق x^3", "بسّط (x-1)/(x^2-1)", "حل x^2-5x+6=0"
- اشتقاق/تكامل/تبسيط/تحليل/تقييم/حل معادلات
- مخرجات بصيغة HTML + LaTeX
"""

import re, html
import sympy as sp
from sympy import (
    symbols, sympify, Eq, S, diff, integrate, factor, pi,
    sin, cos, tan, log, sqrt, Poly
)

# -------------------------------------------------
# إعدادات ومساعدات عامة
# -------------------------------------------------
X = symbols("x")
SAFE = {
    "x": X, "pi": pi, "sin": sin, "cos": cos, "tan": tan,
    "log": log, "sqrt": sqrt, "e": sp.E
}

def _latex(e):
    try:
        return sp.latex(e)
    except Exception:
        return str(e)

def _h2(title): return f"<h2>{title}</h2>"
def _tag(title): return f"<div class='tag'>{title}</div>"
def _err(msg):  return f"<div class='err'>{html.escape(msg)}</div>"

def can_handle(q: str) -> bool:
    """يُستخدم من المسجّل لاختيار هذه المهارة للطلبات الرياضية."""
    keys = ("حل","مشتق","مشتقة","اشتق","تكامل","بسّط","بسط","factor","=",
            "sin","cos","tan","sqrt","**","log","pi","^","جذر","جا","جتا")
    qn = q.replace(" ", "")
    return any(k in q for k in keys) or any(ch in qn for ch in ["=","∫","^","**"])

# -------------------------------------------------
# طبقة فهم العربية (intents + normalization)
# -------------------------------------------------
ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

FUNC_MAP = {
    r"\bجا\s*\(": "sin(",
    r"\bجتا\s*\(": "cos(",
    r"\bظا\s*\(": "tan(",
    r"\bلوغ\s*\(": "log(",
    r"\bجذر\s*\(": "sqrt(",
    r"\bجذر\b": "sqrt",
    r"\bس\b": "x",   # دعم س بدل x
}

INTENT_SYNONYMS = {
    "derivative": ["مشتق", "مشتقة", "اشتق", "أوجد مشتق", "اوجد مشتق"],
    "integral":   ["تكامل", "أوجد تكامل", "اوجد تكامل"],
    "simplify":   ["بسّط", "بسط", "تبسيط", "اختصر"],
    "factor":     ["حلل", "تحليل", "تفكيك", "عامل"],
    "solve":      ["حل", "حل المعادلة", "جذور"],
    "evaluate":   ["احسب", "قيّم", "قيمة", "عوّض", "عند"],
}

RE_WRT   = re.compile(r"(بالنسبة\s*إ?لى?\s*)([a-zA-Z\u0621-\u064A])")
RE_ATVAL = re.compile(r"(?:عند|إذا\s*كان|لو)\s*([a-zA-Z])\s*=\s*([\-]?\d+(?:\.\d+)?)")

def normalize_expression(expr: str) -> str:
    expr = expr.translate(ARABIC_DIGITS)
    expr = expr.replace("^", "**")
    # دوال عربية -> إنجليزية
    for pat, repl in FUNC_MAP.items():
        expr = re.sub(pat, repl, expr)
    # 2x -> 2*x و x2 -> x*2
    expr = re.sub(r"(\d)([a-zA-Z])", r"\1*\2", expr)
    expr = re.sub(r"([a-zA-Z])(\d)", r"\1*\2", expr)
    # علامات زائدة
    return re.sub(r"\s+", " ", expr.strip(" :،.؛")).strip()

def detect_intent(text: str) -> str | None:
    for intent, words in INTENT_SYNONYMS.items():
        for w in words:
            if w in text:
                return intent
    return None

def extract_wrt_var(text: str) -> str | None:
    m = RE_WRT.search(text)
    return m.group(2) if m else None

def extract_eval_point(text: str):
    m = RE_ATVAL.search(text)
    if m:
        var, val = m.group(1), float(m.group(2))
        return var, val
    return None, None

def strip_command_words(text: str) -> str:
    garbage = [
        "أوجد","اوجد","احسب","قيّم","قيمة","حل المعادلة","حل","بسّط","بسط",
        "حلل","تحليل","تكامل","مشتق","المعادلة","المسألة","بالنسبة إلى","بالنسبة الى"
    ]
    s = text
    for g in garbage:
        s = s.replace(g, " ")
    return re.sub(r"\s+", " ", s).strip(" :،.؛")

def understand_arabic_math_query(user_text: str):
    text = user_text.translate(ARABIC_DIGITS)
    intent = detect_intent(text)
    wrt = extract_wrt_var(text)
    at = extract_eval_point(text)
    expr_part = strip_command_words(text)
    if not expr_part and ":" in text:
        expr_part = text.split(":", 1)[1]
    expr = normalize_expression(expr_part)

    if not intent:
        intent = "solve" if "=" in expr else "simplify"
    if intent in ("derivative","integral") and not wrt:
        wrt = "x"

    return {"intent": intent, "expr": expr, "wrt": wrt, "at": at if at!=(None,None) else None}

# -------------------------------------------------
# مساعدات للحلول
# -------------------------------------------------
def _warn_degree(deg):
    return (_tag("تنبيه") + f"<div>درجة كثيرة الحدود = {deg}، الجذور قد تكون تقريبية.</div>") if (deg and deg>6) else ""

def _roots_numeric(expr, tol_im=1e-10, prec=30):
    try:
        p = Poly(expr, X)
        nrs = p.nroots(n=50, maxsteps=400, tol=1e-25, prec=prec)
    except Exception:
        return [], []
    reals, cmplx = [], []
    for r in nrs:
        rN = sp.N(r, prec)
        (reals if abs(sp.im(rN))<tol_im else cmplx).append(rN)
    return reals, cmplx

# -------------------------------------------------
# حل معادلات بخطوات (يدعم درجتين 1 و 2 بتفصيل، ثم عام/تقريبي)
# -------------------------------------------------
def solve_equation_html(left, right) -> str:
    eq = Eq(left, right)
    head = _h2("📌 حل المعادلة") + f"<div>$$ {_latex(eq)} $$</div>"

    poly = (left - right).as_poly(X)
    fact_html = ""
    if poly is not None:
        try:
            fac = factor(poly.as_expr())
            if fac != poly.as_expr():
                fact_html = _tag("تفكيك") + f"<div>$$ {_latex(fac)} $$</div>"
        except Exception:
            pass

        deg = poly.degree()
        warn = _warn_degree(deg)

        if deg == 1:
            a, b = poly.all_coeffs()  # a*x + b
            sol = -b/a
            steps = (
                "<h3>الخطوات:</h3>"
                r"<div>$$ a x + b = 0 \Rightarrow x = -\frac{b}{a} $$</div>"
                f"<div>حيث $$ a={_latex(a)},\\; b={_latex(b)} $$</div>"
            )
            return head + fact_html + warn + steps + f"<h3>الحل:</h3><div>$$ x = {_latex(sp.N(sol,14))} $$</div>"

        if deg == 2:
            a, b, c = poly.all_coeffs()  # a*x^2 + b*x + c
            disc = b**2 - 4*a*c
            x1 = (-b + sp.sqrt(disc)) / (2*a)
            x2 = (-b - sp.sqrt(disc)) / (2*a)
            steps = (
                "<h3>الخطوات (القانون العام):</h3>"
                r"<div>$$ x=\frac{-b\pm\sqrt{b^2-4ac}}{2a} $$</div>"
                f"<div>حيث $$ a={_latex(a)},\\; b={_latex(b)},\\; c={_latex(c)} $$</div>"
                f"<div>المميّز $$ \\Delta = {_latex(disc)} $$</div>"
            )
            roots = [sp.N(x1,14), sp.N(x2,14)]
            return head + fact_html + steps + f"<h3>الجذور:</h3><div>$$ {_latex(roots)} $$</div>"

        # عام: محاولة جذور دقيقة ثم تقريبية
        try:
            exact = sp.solve(poly.as_expr(), X)
        except Exception:
            exact = []
        reals, cmplx = _roots_numeric(poly.as_expr())
        body = (
            fact_html + warn +
            ( _tag("جذور دقيقة") + f"<div>$$ {_latex(exact)} $$</div>" if exact else "" ) +
            ( _tag("جذور حقيقية (تقريبية)") + f"<div>$$ {_latex([sp.N(r,14) for r in reals])} $$</div>" if reals else "" ) +
            ( _tag("جذور مركّبة (تقريبية)") + f"<div>$$ {_latex([sp.N(c,14) for c in cmplx])} $$</div>" if cmplx else "" )
        )
        return head + body

    # ليست كثيرة حدود بـ x -> حل عام من Sympy
    try:
        sols = sp.solve(sp.Eq(left, right), X, dict=True)
        return head + _tag("الحل") + f"<div>$$ {_latex(sols)} $$</div>"
    except Exception as e:
        return head + _err(f"تعذّر الحل: {e}")

# -------------------------------------------------
# موجِّه الأوامر العربية
# -------------------------------------------------
def run_arabic_math(q: str) -> str:
    info = understand_arabic_math_query(q)
    intent, expr, wrt, at = info["intent"], info["expr"], info["wrt"], info["at"]

    try:
        sy = sympify(expr, locals=SAFE)
    except Exception as e:
        return _err(f"تعذّر فهم التعبير: {expr}\n{e}")

    head = _tag("المسألة") + f"<div>$$ {_latex(sy)} $$</div>"

    try:
        if intent == "derivative":
            v = symbols(wrt) if wrt else X
            res = diff(sy, v)
            steps = "<h3>ملاحظة:</h3><div>تم الاشتقاق بالنسبة إلى $$%s$$.</div>" % _latex(v)
            return _h2("📐 المشتق") + head + steps + f"<h3>النتيجة:</h3><div>$$ {_latex(res)} $$</div>"

        if intent == "integral":
            v = symbols(wrt) if wrt else X
            res = integrate(sy, v)
            return _h2("∫ التكامل") + head + f"<h3>النتيجة:</h3><div>$$ {_latex(res)} + C $$</div>"

        if intent == "factor":
            res = factor(sy)
            return _h2("🧩 التحليل") + head + f"<h3>النتيجة:</h3><div>$$ {_latex(res)} $$</div>"

        if intent == "simplify":
            res = sp.simplify(sy)
            return _h2("🧹 تبسيط") + head + f"<h3>النتيجة:</h3><div>$$ {_latex(res)} $$</div>"

        if intent == "evaluate":
            if at:
                var, val = at
                v = symbols(var)
                val_res = sp.N(sy.subs({v: val}), 14)
                more = f"<div>عند $$ {var}={val} $$</div>"
                return _h2("🧮 تقييم") + head + more + f"<h3>القيمة:</h3><div>$$ {_latex(val_res)} $$</div>"
            else:
                val_res = sp.N(sy, 14)
                return _h2("🧮 تقييم") + head + f"<h3>القيمة:</h3><div>$$ {_latex(val_res)} $$</div>"

        if intent == "solve":
            if "=" in expr:
                left, right = expr.split("=", 1)
                L = sympify(left,  locals=SAFE)
                R = sympify(right, locals=SAFE)
                return solve_equation_html(L, R)
            # صيغة بدون علامة = : اعتبرها f(x)=0
            return solve_equation_html(sy, 0)

        return _h2("ℹ️ نتيجة") + head + f"<div>$$ {_latex(sy)} $$</div>"

    except Exception as e:
        return _err(f"حدث خطأ أثناء المعالجة: {e}")

# -------------------------------------------------
# نقطة دخول موحّدة تُستعمل من الراوتر
# -------------------------------------------------
def run_math_query(q: str) -> str:
    q_clean = q.strip()
    # لو فيه كلمات مفاتيح عربية، جرّب الفهم الجديد
    if any(w in q_clean for w in ["مشتق","مشتقة","تكامل","حل","حلل","بسّط","بسط","قيمة","قيّم","عند"]):
        return run_arabic_math(q_clean)
    # fallback: حاول كفهم عربي أيضًا
    return run_arabic_math(q_clean)
