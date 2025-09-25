# core/math_engine.py
# محرك رياضيات محلي مجاني قائم على Sympy + خطوات شرح

from __future__ import annotations
from typing import Any, Dict, List, Optional, Union

from sympy import (
    symbols, sympify, S, Eq, solveset, diff, integrate, simplify, factor,
    Matrix, det, pi, E, oo, sin, cos, tan, asin, acos, atan, log, ln, exp,
    sqrt, Abs, re, im, Rational
)
from sympy.core.symbol import Symbol
from sympy.parsing.sympy_parser import (
    standard_transformations, convert_xor,
    implicit_multiplication_application, rationalize
)

# ---------------------------------------------------
# إعدادات الأمان لـ sympify (مسموح فقط ما نُدرجه هنا)
# ---------------------------------------------------
_ALLOWED_LOCALS: Dict[str, Any] = {
    # ثوابت/دوال
    "pi": pi, "E": E, "oo": oo,
    "sin": sin, "cos": cos, "tan": tan,
    "asin": asin, "acos": acos, "atan": atan,
    "log": log, "ln": ln, "exp": exp,
    "sqrt": sqrt, "Abs": Abs, "re": re, "im": im,
    "Rational": Rational,
}

# رموز شائعة
x, y, z = symbols("x y z")
_ALLOWED_LOCALS.update({"x": x, "y": y, "z": z})

_TRANSFORMS = (
    standard_transformations + (convert_xor, implicit_multiplication_application, rationalize)
)


class MathError(Exception):
    """خطأ قابل للعرض للمستخدم."""
    pass


def _detect_var(expr_text: str) -> Symbol:
    """اختيار المتغير المناسب من النص تلقائياً (x ثم y ثم z)."""
    for v in ("x", "y", "z"):
        if v in expr_text:
            return symbols(v)
    return x


def _sympify(text: str) -> Any:
    """تحويل نص إلى كائن Sympy بشكل آمن."""
    try:
        return sympify(text, locals=_ALLOWED_LOCALS, transformations=_TRANSFORMS, evaluate=True)
    except Exception as e:
        raise MathError(f"صيغة غير مفهومة: `{text}` — {e}")


# ===========================
# 1) تقييم الدوال وقيم المشتقة
# ===========================
def evaluate_function(expr_str: str, at: Optional[Union[int, float]] = None, var: Optional[str] = None) -> Dict[str, Any]:
    v = symbols(var) if var else _detect_var(expr_str)
    expr = _sympify(expr_str)

    result: Dict[str, Any] = {
        "operation": "evaluate",
        "expression": str(expr),
        "variable": str(v)
    }

    if at is not None:
        val = expr.subs(v, at)
        result.update({"at": at, "value": float(val)})
    return result


def differentiate(expr_str: str, order: int = 1, at: Optional[Union[int, float]] = None, var: Optional[str] = None) -> Dict[str, Any]:
    if order < 1:
        raise MathError("رتبة المشتقة يجب أن تكون 1 أو أكثر.")
    v = symbols(var) if var else _detect_var(expr_str)
    expr = _sympify(expr_str)

    deriv = diff(expr, v, order)
    out: Dict[str, Any] = {
        "operation": "differentiate",
        "expression": str(expr),
        "variable": str(v),
        "order": order,
        "derivative": str(deriv)
    }
    if at is not None:
        out["at"] = at
        out["derivative_value"] = float(deriv.subs(v, at))
    return out


# ==========
# 2) التكامل
# ==========
def integrate_expr(expr_str: str, a: Optional[Union[int, float]] = None, b: Optional[Union[int, float]] = None, var: Optional[str] = None) -> Dict[str, Any]:
    v = symbols(var) if var else _detect_var(expr_str)
    expr = _sympify(expr_str)

    if a is None and b is None:
        integ = integrate(expr, v)
        return {
            "operation": "integrate",
            "expression": str(expr),
            "variable": str(v),
            "integral": str(integ)
        }
    if (a is None) ^ (b is None):
        raise MathError("للتكامل المحدد يجب تحديد الحدين معاً a و b.")
    integ = integrate(expr, (v, a, b))
    return {
        "operation": "integrate_definite",
        "expression": str(expr),
        "variable": str(v),
        "a": a,
        "b": b,
        "definite_integral": float(integ)
    }


# ===============
# 3) حل المعادلات
# ===============
def solve_equation(eq_str: str, var: Optional[str] = None) -> Dict[str, Any]:
    """
    يقبل:
      - '2*x + 1 = 5'
      - أو عبارة تساوي صفر ضمنياً: '2*x + 1' (يفترض 2*x+1 = 0)
    """
    v = symbols(var) if var else _detect_var(eq_str)
    if "=" in eq_str:
        left, right = eq_str.split("=", 1)
        left_expr = _sympify(left)
        right_expr = _sympify(right)
        equation = Eq(left_expr, right_expr)
    else:
        equation = Eq(_sympify(eq_str), S.Zero)

    sol = solveset(equation, v, domain=S.Complexes)
    # تحويل النتائج إلى نصوص سهلة
    try:
        iterable = list(sol)  # قد يفشل لو كان EmptySet/FiniteSet لها تعامل خاص
    except TypeError:
        iterable = [sol]
    pretty = [str(s) for s in iterable]

    return {
        "operation": "solve",
        "equation": str(equation),
        "variable": str(v),
        "solutions": pretty,
    }


# ===================
# 4) تبسيط/تحليل جبري
# ===================
def simplify_expr(expr_str: str) -> Dict[str, Any]:
    expr = _sympify(expr_str)
    return {"operation": "simplify", "original": str(expr), "simplified": str(simplify(expr))}


def factor_expr(expr_str: str) -> Dict[str, Any]:
    expr = _sympify(expr_str)
    return {"operation": "factor", "original": str(expr), "factored": str(factor(expr))}


# ============
# 5) مصفوفات
# ============
def matrix_det(data: List[List[Union[int, float, str]]]) -> Dict[str, Any]:
    M = Matrix([[ _sympify(str(c)) for c in row ] for row in data])
    return {"operation": "matrix_det", "matrix": str(M.tolist()), "det": float(det(M))}


def matrix_inv(data: List[List[Union[int, float, str]]]) -> Dict[str, Any]:
    M = Matrix([[ _sympify(str(c)) for c in row ] for row in data])
    invM = M.inv()
    return {
        "operation": "matrix_inv",
        "matrix": str(M.tolist()),
        "inverse": [[str(invM[i, j]) for j in range(invM.cols)] for i in range(invM.rows)]
    }


def matrix_rank(data: List[List[Union[int, float, str]]]) -> Dict[str, Any]:
    M = Matrix([[ _sympify(str(c)) for c in row ] for row in data])
    return {"operation": "matrix_rank", "matrix": str(M.tolist()), "rank": int(M.rank())}


# =======================================
# 6) مُوزِّع بسيط لفهم المطلوب من نص السؤال
# =======================================
def solve_math(query: str) -> Dict[str, Any]:
    """
    موزّع نصي بسيط جداً: يحاول فهم المطلوب من الكلمات المفتاحية بالعربية/الإنجليزية.
    إن أردت، استدعِ الدوال المتخصصة مباشرة من تطبيقك وتجاهل هذا الموزع.
    """
    q = (query or "").strip().replace("٫", ".").replace("،", ",")
    try:
        # مشتقات
        if any(k in q for k in ["مشتق", "اشتق", "deriv", "diff"]):
            # أمثلة: "اشتق 3*x**2 + 5*x - 7"، "المشتقة الثانية لـ sin(x)"
            order = 1
            for w in ["الثانية", "2", "second"]:
                if w in q:
                    order = 2
            # استخراج التعبير
            expr = q
            for tag in ["اشتق", "المشتقة", "مشتق", "deriv", "diff"]:
                expr = expr.replace(tag, "")
            if "لـ" in expr:
                expr = expr.split("لـ", 1)[-1]
            if "of" in expr:
                expr = expr.split("of", 1)[-1]
            expr = expr.strip()
            # نقطة تقييم اختيارية: "عند x=2"
            at = None
            if "عند" in q and "=" in q:
                try:
                    _, after = q.split("عند", 1)
                    v_name, v_val = after.split("=")
                    at = float(_sympify(v_val.strip()))
                except Exception:
                    at = None
            return differentiate(expr, order=order, at=at)

        # تكامل
        if any(k in q for k in ["تكامل", "integral", "∫"]):
            # أمثلة: "تكامل 2*x من 0 إلى 1", "التكامل غير المحدد لـ cos(x)"
            if "من" in q and "إلى" in q:
                head, tail = q.split("من", 1)
                expr = head.replace("تكامل", "").replace("التكامل", "").replace("∫", "").strip()
                a_txt, b_txt = tail.split("إلى", 1)
                return integrate_expr(expr, a=_sympify(a_txt.strip()), b=_sympify(b_txt.strip()))
            expr = q.replace("تكامل", "").replace("التكامل", "").replace("∫", "").strip()
            return integrate_expr(expr)

        # حلول المعادلات/الجذور
        if any(k in q for k in ["حل", "جذر", "roots", "solve", "="]):
            # مثال: "حل 2*x**2 + x - 5 = 0" أو "2*x+1=5"
            eq_txt = q.replace("حل", "").replace("roots", "").replace("solve", "").strip()
            return solve_equation(eq_txt)

        # تبسيط
        if any(k in q for k in ["بسّط", "بسط", "simplify"]):
            expr = q.replace("بسّط", "").replace("بسط", "").replace("simplify", "").strip()
            return simplify_expr(expr)

        # تحليل
        if any(k in q for k in ["حلّل", "حلل", "factor"]):
            expr = q.replace("حلّل", "").replace("حلل", "").replace("factor", "").strip()
            return factor_expr(expr)

        # تقييم مباشر: "قيّم 3*x**2+1 عند x=2" أو دالة فقط
        if "عند" in q and "=" in q:
            left, after = q.split("عند", 1)
            expr = (
                left.replace("قيم", "")
                    .replace("قيّم", "")
                    .replace("f(x)=", "")
                    .replace("g(x)=", "")
                    .strip()
            )
            v_name, v_val = after.split("=")
            v_name = v_name.strip()
            v_val = _sympify(v_val.strip())
            return evaluate_function(expr, at=float(v_val), var=v_name)

        # كافتراضي: جرّب التبسيط
        expr = q
        return {"operation": "simplify_try", "simplify_try": simplify_expr(expr)}
    except MathError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"خطأ غير متوقع: {e}"}


# ======================================
# 7) دوال "خطوات الشرح" (Steps) للعرض
# ======================================
def _steps_for_polynomial_eval(expr_str: str, at: float, value: float) -> list:
    steps = [
        {"id": "s1", "title": "تعويض", "text": f"نعوّض x = {at} في {expr_str}."},
        {"id": "s2", "title": "حساب جزئي", "text": "نحسب الحدود خطوة خطوة ثم نجمعها."},
        {"id": "s3", "title": "النتيجة", "text": f"قيمة الدالة عند x={at} تساوي {value}."}
    ]
    return steps


def wrap_result_with_steps(math_result: dict) -> dict:
    """
    يأخذ نتيجة الرياضيات ويضيف steps إن أمكن.
    يحاول استنتاج نوع العملية ويولّد خطوات بسيطة.
    """
    res = dict(math_result or {})
    expr = str(res.get("expression", res.get("expr", "")))
    steps = res.get("steps", [])

    # تقييم قيمة
    if "value" in res and "at" in res and not steps:
        try:
            at = float(res["at"])
            val = float(res["value"])
            steps = _steps_for_polynomial_eval(expr or "f(x)", at, val)
        except Exception:
            pass

    # مشتقة
    if ("derivative" in res or "derivative_value" in res) and not steps:
        d = res.get("derivative", "")
        dv = res.get("derivative_value", None)
        steps = [
            {"id": "s1", "title": "اشتقاق", "text": f"نشتق التعبير: المشتقة هي: {d}."},
            {"id": "s2", "title": "تعويض (إن وُجد)", "text": f"قيمة المشتقة عند النقطة: {dv}." if dv is not None else "لا توجد نقطة تقييم."}
        ]

    # تكامل
    if ("integral" in res or "definite_integral" in res) and not steps:
        val = res.get("definite_integral", None)
        steps = [
            {"id": "s1", "title": "التكامل", "text": f"أوجدنا التكامل الرمزي/المحدد للتعبير {expr}."},
        ]
        if val is not None:
            steps.append({"id": "s2", "title": "قيمة محددة", "text": f"قيمة التكامل المحدد = {val}."})

    res["steps"] = steps
    return res


# ======================================================
# 8) دالة واجهة متوافقة مع الواجهة الأمامية: solve_math_problem
# ======================================================
def solve_math_problem(query: str) -> Dict[str, Any]:
    """
    واجهة موحّدة يستدعيها التطبيق (main.py).
    تعيد مفاتيح متوافقة مع HTML الحالي:
      - success: bool
      - operation: str
      - result / solutions / derivative / integral ...
      - steps: list[ {id,title,text} ]
      - image: (اختياري مستقبلاً Base64)
    """
    try:
        core = solve_math(query)  # ناتج أساسي
        core = wrap_result_with_steps(core)  # إضافة خطوات

        # صياغة مفاتيح ملائمة للواجهة
        payload: Dict[str, Any] = {"success": True}

        op = core.get("operation", "")
        payload["operation"] = {
            "evaluate": "تقييم دالة",
            "differentiate": "اشتقاق",
            "integrate": "تكامل غير محدد",
            "integrate_definite": "تكامل محدد",
            "solve": "حل معادلة",
            "simplify": "تبسيط",
            "factor": "تحليل",
            "matrix_det": "محدد مصفوفة",
            "matrix_inv": "معكوس مصفوفة",
            "matrix_rank": "رتبة مصفوفة",
            "simplify_try": "تبسيط (تجريبي)",
        }.get(op, "عملية رياضية")

        # نقل أهم الحقول إلى result/solutions حسب الحالة
        if "solutions" in core:
            payload["solutions"] = core["solutions"]
        if "value" in core:
            payload["result"] = core["value"]
        if "definite_integral" in core:
            payload["result"] = core["definite_integral"]
        if "integral" in core and "result" not in payload:
            payload["result"] = core["integral"]
        if "derivative" in core and "result" not in payload:
            payload["result"] = core["derivative"]
        if "derivative_value" in core:
            payload["derivative_value"] = core["derivative_value"]

        # أضف باقي الحقول المفيدة
        for k in ["expression", "variable", "equation", "order", "a", "b", "original", "simplified", "factored"]:
            if k in core:
                payload[k] = core[k]

        # خطوات الشرح
        if "steps" in core:
            payload["steps"] = core["steps"]

        return payload

    except MathError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"خطأ غير متوقع: {e}"}
