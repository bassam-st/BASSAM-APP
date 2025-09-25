# src/core/math_engine.py
import re, html
import sympy as sp
from sympy import symbols, sympify, Eq, solveset, S, diff, integrate, factor, pi, sin, cos, tan, log, sqrt

X = symbols("x")
SAFE = {"x": X, "pi": pi, "sin": sin, "cos": cos, "tan": tan, "log": log, "sqrt": sqrt}

def _latex(expr):
    try:
        return sp.latex(expr)
    except Exception:
        return str(expr)

def solve_query(q: str) -> str:
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
                    fact_html = f"<div class='tag'>التفكيك:</div><div>$$ {_latex(fac)} $$</div>"
            except Exception:
                pass

            deg = poly.degree()
            steps_html = ""
            roots_real, roots_cmplx = [], []

            if deg == 1:
                a, b = poly.all_coeffs()  # ax + b
                sol = -b/a
                steps_html = (
                    "<h3>الخطوات:</h3>"
                    r"<div>$$ x = -\frac{b}{a} $$</div>"
                    f"<div>حيث $$ a={_latex(a)},\ b={_latex(b)} $$</div>"
                )
                roots_real = [sol.evalf(12)]
            elif deg == 2:
                a, b, c = poly.all_coeffs()
                disc = b**2 - 4*a*c
                x1 = (-b + sp.sqrt(disc)) / (2*a)
                x2 = (-b - sp.sqrt(disc)) / (2*a)
                steps_html = (
                    "<h3>الخطوات (القانون العام):</h3>"
                    r"<div>$$ x=\frac{-b\pm\sqrt{b^2-4ac}}{2a} $$</div>"
                    f"<div>حيث $$ a={_latex(a)},\ b={_latex(b)},\ c={_latex(c)} $$</div>"
                    f"<div>$$ \\Delta = {_latex(disc)} $$</div>"
                )
                vals = [sp.N(x1, 12), sp.N(x2, 12)]
                roots_real  = [r for r in vals if abs(sp.im(r)) < 1e-12]
                roots_cmplx = [r for r in vals if abs(sp.im(r)) >= 1e-12]
            else:
                nrs = poly.nroots(n=15, maxsteps=200)
                roots_real  = [sp.N(r, 12) for r in nrs if abs(sp.im(r)) < 1e-10]
                roots_cmplx = [sp.N(r, 12) for r in nrs if abs(sp.im(r)) >= 1e-10]
                steps_html = "<h3>الطريقة:</h3><div>اُستخدمت طريقة عددية nroots من SymPy.</div>"

            real_html = "<br>".join(f"$$ x \\approx {_latex(r)} $$" for r in roots_real) or "لا توجد جذور حقيقية."
            cmplx_html = "<br>".join(f"$$ x \\approx {_latex(r)} $$" for r in roots_cmplx) or "لا توجد جذور عقدية."

            return (
                head + fact_html + steps_html +
                "<h3>الجذور الحقيقية (تقريبًا):</h3><div>" + real_html + "</div>" +
                "<h3>الجذور العقدية (تقريبًا):</h3><div>" + cmplx_html + "</div>"
            )

        # ليست كثيرة حدود
        sol = solveset(eq, X, domain=S.Complexes)
        return head + "<h3>الحل الرمزي:</h3><div>$$ " + _latex(sol) + " $$</div>"

    # مشتقة
    m = re.search(r"(اشتق|مشتقة)\s+(.*)", q)
    if m:
        expr = sympify(m.group(2), locals=SAFE)
        d = diff(expr, X)
        return (
            "<h2>📌 المشتقة</h2>"
            f"<div>$$ f(x) = {_latex(expr)} $$</div>"
            f"<div>$$ f'(x) = {_latex(d)} $$</div>"
        )

    # تكامل محدد
    m = re.search(r"تكامل\s+(.*)\s+من\s+(.*)\s+إلى\s+(.*)", q)
    if m:
        expr = sympify(m.group(1), locals=SAFE)
        a = sympify(m.group(2), locals=SAFE)
        b = sympify(m.group(3), locals=SAFE)
        val = integrate(expr, (X, a, b))
        F = integrate(expr, X)
        return (
            "<h2>📌 التكامل المحدد</h2>"
            f"<div>$$ \\int_{{{_latex(a)}}}^{{{_latex(b)}}} {_latex(expr)}\\,dx $$</div>"
            f"<div class='tag'>دالة أصلية:</div><div>$$ F(x) = {_latex(F)} $$</div>"
            f"<h3>النتيجة:</h3><div>$$ {_latex(val)} $$</div>"
        )

    # تكامل غير محدد
    m = re.search(r"تكامل\s+(.*)", q)
    if m:
        expr = sympify(m.group(1), locals=SAFE)
        F = integrate(expr, X)
        return (
            "<h2>📌 التكامل</h2>"
            f"<div>$$ \\int {_latex(expr)}\\,dx = {_latex(F)} + C $$</div>"
        )

    # تبسيط/تقييم
    try:
        expr = sympify(q, locals=SAFE)
        simp = sp.simplify(expr)
        return (
            "<h2>📌 تبسيط/تقييم</h2>"
            f"<div>$$ {_latex(expr)} $$</div>"
            "<div class='tag'>النتيجة:</div>"
            f"<div>$$ {_latex(simp)} $$</div>"
        )
    except Exception as e:
        return f"<h2>تعذر فهم المسألة</h2><pre>{html.escape(str(e))}</pre>"
