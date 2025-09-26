# src/skills/math_v7.py — Math Skill v7 (LaTeX + steps)
import re, html, sympy as sp
from sympy import symbols, sympify, Eq, solveset, S, diff, integrate, factor, pi, sin, cos, tan, log, sqrt, Poly

X = symbols("x")
SAFE = {"x": X, "pi": pi, "sin": sin, "cos": cos, "tan": tan, "log": log, "sqrt": sqrt}

def _latex(e): 
    try: return sp.latex(e)
    except: return str(e)

def can_handle(q: str) -> bool:
    keys = ("حل","مشتقة","اشتق","تكامل","بسّط","بسط","factor","=","sin","cos","tan","sqrt","**","log","pi")
    qn = q.replace(" ","")
    return any(k in q for k in keys) or any(ch in qn for ch in ["=","∫","^","**"])

def _warn_degree(deg):
    return ("<div class='tag'>تنبيه</div>"
            f"<div>درجة كثيرة الحدود = {deg}، الجذور تقريبية.</div>") if (deg and deg>6) else ""

def _roots_numeric(expr, tol_im=1e-10, prec=30):
    try:
        p = Poly(expr, X)
        nrs = p.nroots(n=30, maxsteps=250, tol=1e-20, prec=prec)
    except Exception:
        return [], []
    reals, cmplx = [], []
    for r in nrs:
        rN = sp.N(r, prec)
        (reals if abs(sp.im(rN))<tol_im else cmplx).append(rN)
    return reals, cmplx

def solve(q: str) -> str:
    q = q.strip()

    # حل معادلة
    m = re.search(r"حل\s+(.*)=(.*)", q)
    if m:
        left = sympify(m.group(1), locals=SAFE)
        right = sympify(m.group(2), locals=SAFE)
        eq = Eq(left, right)
        head = f"<h2>📌 حل المعادلة</h2><div>$$ {_latex(eq)} $$</div>"

        poly = (left - right).as_poly(X)
        if poly is not None:
            fact_html = ""
            try:
                fac = factor(poly.as_expr())
                if fac != poly.as_expr():
                    fact_html = f"<div class='tag'>تفكيك</div><div>$$ {_latex(fac)} $$</div>"
            except: pass

            deg = poly.degree()
            warn = _warn_degree(deg)
            if deg == 1:
                a, b = poly.all_coeffs()
                sol = -b/a
                steps = ("<h3>الخطوات:</h3>"
                         r"<div>$$ a x + b = 0 \Rightarrow x = -\frac{b}{a} $$</div>"
                         f"<div>حيث $$ a={_latex(a)},\\; b={_latex(b)} $$</div>")
                return head + fact_html + warn + steps + f"<h3>الحل:</h3><div>$$ x = {_latex(sp.N(sol,14))} $$</div>"
            if deg == 2:
                a, b, c = poly.all_coeffs()
                disc = b**2 - 4*a*c
                x1 = (-b + sp.sqrt(disc)) / (2*a)
                x2 = (-b - sp.sqrt(disc)) / (2*a)
                steps = ("<h3>الخطوات (القانون العام):</h3>"
                         r"<div>$$ x=\frac{-b\pm\sqrt{b^2-4ac}}{2a} $$</div>"
                         f"<div>حيث $$ a={_latex(a)},\\; b={_latex(b)},\\; c={_latex(c)} $$</div>"
                         f"<div>$$ \\Delta = {_latex(disc)} $$</div>")
                roots = [sp.N(x1,14), sp.N(x2,14)]
