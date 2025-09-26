# src/core/math_engine.py — v2 (خطوات + تنبيه درجة عالية + LaTeX)
import re, html
import sympy as sp
from sympy import symbols, sympify, Eq, solveset, S, diff, integrate, factor, pi, sin, cos, tan, log, sqrt
from sympy import Poly

X = symbols("x")
SAFE = {"x": X, "pi": pi, "sin": sin, "cos": cos, "tan": tan, "log": log, "sqrt": sqrt}

def _latex(expr):
    try:
        return sp.latex(expr)
    except Exception:
        return str(expr)

def _warn_degree(deg: int) -> str:
    if deg is not None and deg > 6:
        return (
            "<div class='tag'>تنبيه</div>"
            "<div>درجة كثيرة الحدود كبيرة "
            f"(deg = {deg})، لذا الجذور العددية تقريبية وقد تتطلب دقة أعلى.</div>"
        )
    return ""

def _roots_numeric(expr, tol_im=1e-10, prec=20):
    """جذور عددية (إن أمكن) مع فصل حقيقي/عقدي."""
    try:
        p = Poly(expr, X)
        nrs = p.nroots(n=30, maxsteps=250, tol=1e-20, maxstepsmax=500, prec=prec)
    except Exception:
        return [], []
    reals, cmplx = [], []
    for r in nrs:
        rN = sp.N(r, prec)
        if abs(sp.im(rN)) < tol_im:
            reals.append(rN)
        else:
            cmplx.append(rN)
    return reals, cmplx

def _steps_linear(a, b):
    return (
        "<h3>الخطوات:</h3>"
        r"<div>$$ a\,x + b = 0 \Rightarrow x = -\frac{b}{a} $$</div>"
        f"<div>حيث $$ a={_latex(a)},\\; b={_latex(b)} $$</div>"
    )

def _steps_quadratic(a, b, c, disc, x1, x2):
    return (
        "<h3>الخطوات (القانون العام):</h3>"
        r"<div>$$ ax^2+bx+c=0 \Rightarrow x=\frac{-b\pm\sqrt{b^2-4ac}}{2a} $$</div>"
        f"<div>حيث $$ a={_latex(a)},\\; b={_latex(b)},\\; c={_latex(c)} $$</div>"
        f"<div>مميّز المعادلة $$ \\Delta = {_latex(disc)} $$</div>"
        f"<div>الجذران (رمزياً): $$ x_1={_latex(x1)},\\; x_2={_latex(x2)} $$</div>"
    )

def _list_roots(title, roots):
    if not roots:
        return f"<h3>{title}</h3><div>لا توجد جذور.</div>"
    body = "<br>".join(f"$$ x \\approx {_latex(r)} $$" for r in roots)
    return f"<h3>{title}</h3><div>{body}</div>"

def solve_query(q: str) -> str:
    q = (q or "").strip()

    # ===== حل معادلة =====
    m = re.search(r"حل\s+(.*)=(.*)", q)
    if m:
        left = sympify(m.group(1), locals=SAFE)
        right = sympify(m.group(2), locals=SAFE)
        eq = Eq(left, right)

        head = f"<h2>📌 حل المعادلة</h2><div>$$ {_latex(eq)} $$</div>"

        # حاول كـ polynomial
        poly = (left - right).as_poly(X)
        if poly is not None:
            fact_html = ""
            try:
                fac = factor(poly.as_expr())
                if fac != poly.as_expr():
                    fact_html = f"<div class='tag'>تفكيك</div><div>$$ {_latex(fac)} $$</div>"
            except Exception:
                pass

            deg = poly.degree()
            warn = _warn_degree(deg)
            steps_html = ""
            real_roots, cmplx_roots = [], []

            if deg == 1:
                # ax + b = 0
                a, b = poly.all_coeffs()
                sol = -b/a
                steps_html = _steps_linear(a, b)
                real_roots = [sp.N(sol, 12)]
            elif deg == 2:
                # ax^2 + bx + c
                a, b, c = poly.all_coeffs()
                disc = b**2 - 4*a*c
                x1 = (-b + sp.sqrt(disc)) / (2*a)
                x2 = (-b - sp.sqrt(disc)) / (2*a)
                steps_html = _steps_quadratic(a, b, c, disc, x1, x2)
                vals = [sp.N(x1, 14), sp.N(x2, 14)]
                real_roots = [r for r in vals if abs(sp.im(r)) < 1e-12]
                cmplx_roots = [r for r in vals if abs(sp.im(r)) >= 1e-12]
            else:
                steps_html = "<h3>الطريقة العددية</h3><div>اُستخدمت دالة nroots من SymPy لإيجاد جذور تقريبية.</div>"
                real_roots, cmplx_roots = _roots_numeric(poly.as_expr(), prec=30)

            return (
                head + fact_html + warn + steps_html +
                _list_roots("الجذور الحقيقية (تقريبًا)", real_roots) +
                _list_roots("الجذور العقدية (تقريبًا)", cmplx_roots)
            )

        # لو ليست كثيرة حدود: حل رمزي عام
        sol = solveset(eq, X, domain=S.Complexes)
        return head + "<h3>الحل الرمزي:</h3><div>$$ " + _latex(sol) + " $$</div>"

    # ===== مشتقة =====
    m = re.search(r"(اشتق|مشتقة)\s+(.*)", q)
    if m:
        expr = sympify(m.group(2), locals=SAFE)
        d = diff(expr, X)
        steps = (
            "<h3>ملاحظات</h3>"
            "<ul>"
            "<li>استخدم قواعد الاشتقاق: مجموع، حاصل ضرب، السلسلة… حسب الحاجة.</li>"
            "<li>يمكن التحقق بتعويض قيم عددية مقارنة بميل المماس.</li>"
            "</ul>"
        )
        return (
            "<h2>📌 المشتقة</h2>"
            f"<div>$$ f(x) = {_latex(expr)} $$</div>"
            f"<div>$$ f'(x) = {_latex(d)} $$</div>"
            + steps
        )

    # ===== تكامل محدد =====
    m = re.search(r"تكامل\s+(.*)\s+من\s+(.*)\s+إلى\s+(.*)", q)
    if m:
        expr = sympify(m.group(1), locals=SAFE)
        a = sympify(m.group(2), locals=SAFE)
        b = sympify(m.group(3), locals=SAFE)
        F = integrate(expr, X)
        val = integrate(expr, (X, a, b))
        steps = (
            "<h3>الخطوات</h3>"
            r"<div>$$ \int_a^b f(x)\,dx = F(b) - F(a) $$</div>"
            f"<div>حيث $$ F'(x)=f(x),\\ a={_latex(a)},\\ b={_latex(b)} $$</div>"
        )
        return (
            "<h2>📌 التكامل المحدد</h2>"
            f"<div>$$ \\int_{{{_latex(a)}}}^{{{_latex(b)}}} {_latex(expr)}\\,dx $$</div>"
            f"<div class='tag'>دالة أصلية:</div><div>$$ F(x) = {_latex(F)} $$</div>"
            + steps +
            f"<h3>النتيجة:</h3><div>$$ {_latex(val)} $$</div>"
        )

    # ===== تكامل غير محدد =====
    m = re.search(r"تكامل\s+(.*)", q)
    if m:
        expr = sympify(m.group(1), locals=SAFE)
        F = integrate(expr, X)
        notes = (
            "<h3>ملاحظات</h3>"
            "<ul><li>أضف ثابت التكامل C دائمًا.</li>"
            "<li>يمكن التحقق بالتفاضل: إذا اشتقّيت F يفترض أن تعود إلى f.</li></ul>"
        )
        return (
            "<h2>📌 التكامل</h2>"
            f"<div>$$ \\int {_latex(expr)}\\,dx = {_latex(F)} + C $$</div>"
            + notes
        )

    # ===== تبسيط/تقييم عام =====
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
        return (
            "<h2>تعذّر فهم المسألة</h2>"
            "<div>تأكد من الصيغة. أمثلة مفيدة:</div>"
            "<ul>"
            "<li>حل 2*x**2 + 3*x - 2 = 0</li>"
            "<li>اشتق x*sin(x)</li>"
            "<li>تكامل cos(x) من 0 إلى pi</li>"
            "</ul>"
            f"<pre>{html.escape(str(e))}</pre>"
        )
