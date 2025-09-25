# core/math_engine.py
# محرك رياضيات محلي مجاني قائم على Sympy

from __future__ import annotations
from typing import Any, Dict, List, Optional, Union

from sympy import (
    symbols, sympify, S, Eq, solveset, diff, integrate, simplify, factor,
    Matrix, det, pi, E, oo, sin, cos, tan, asin, acos, atan, log, exp,
    sqrt, Abs, re, im, Rational
)
from sympy.core.symbol import Symbol
from sympy.parsing.sympy_parser import (
    standard_transformations,
    convert_xor,
    implicit_multiplication_application,
    rationalize,
)

# =========================
# إعدادات عامة وآمنة
# =========================

_ALLOWED_LOCALS: Dict[str, Any] = {
    # ثوابت/دوال
    "pi": pi, "E": E, "oo": oo,
    "sin": sin, "cos": cos, "tan": tan,
    "asin": asin, "acos": acos, "atan": atan,
    "log": log, "ln": log,  # ln==log في sympy
    "exp": exp, "sqrt": sqrt, "Abs": Abs, "re": re, "im": im,
    "Rational": Rational,
}

# رموز شائعة
x, y, z = symbols("x y z")
_ALLOWED_LOCALS.update({"x": x, "y": y, "z": z})

_TRANSFORMS = (
    standard_transformations + (convert_xor, implicit_multiplication_application, rationalize)
)


class MathError(Exception):
    """خطأ خاص بمحرك الرياضيات"""
    pass


def _detect_var(expr_text: str) -> Symbol:
    """اختيار المتغير المناسب من النص تلقائياً."""
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


# =========================
# دوال أساسية
# =========================

def evaluate_function(expr_str: str, at: Optional[Union[int, float]] = None, var: Optional[str] = None) -> Dict[str, Any]:
    v = symbols(var) if var else _detect_var(expr_str)
    expr = _sympify(expr_str)
    out: Dict[str, Any] = {"operation": "تقييم دالة", "expression": str(expr), "variable": str(v)}
    if at is not None:
        val = expr.subs(v, at)
        try:
            out.update({"at": at, "value": float(val)})
        except Exception:
            out.update({"at": at, "value": str(val)})
    return out


def differentiate(expr_str: str, order: int = 1, at: Optional[Union[int, float]] = None, var: Optional[str] = None) -> Dict[str, Any]:
    if order < 1:
        raise MathError("رتبة المشتقة يجب أن تكون 1 أو أكثر.")
    v = symbols(var) if var else _detect_var(expr_str)
    expr = _sympify(expr_str)
    deriv = diff(expr, v, order)
    out: Dict[str, Any] = {
        "operation": f"مشتقة رتبة {order}",
        "expression": str(expr),
        "variable": str(v),
        "order": order,
        "derivative": str(deriv)
    }
    if at is not None:
        val = deriv.subs(v, at)
        try:
            out["at"] = at
            out["derivative_value"] = float(val)
        except Exception:
            out["at"] = at
            out["derivative_value"] = str(val)
    return out


def integrate_expr(expr_str: str, a: Optional[Union[int, float]] = None, b: Optional[Union[int, float]] = None, var: Optional[str] = None) -> Dict[str, Any]:
    v = symbols(var) if var else _detect_var(expr_str)
    expr = _sympify(expr_str)
    if a is None and b is None:
        integ = integrate(expr, v)
        return {"operation": "تكامل غير محدد", "expression": str(expr), "variable": str(v), "integral": str(integ)}
    if (a is None) ^ (b is None):
        raise MathError("للتكامل المحدد يجب تحديد الحدين معاً a و b.")
    integ = integrate(expr, (v, a, b))
    try:
        val = float(integ)
    except Exception:
        val = str(integ)
    return {
        "operation": "تكامل محدد",
        "expression": str(expr),
        "variable": str(v),
        "a": a, "b": b,
        "definite_integral": val
    }


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
    # تحويل النتائج لأشكال قابلة للطباعة
    if hasattr(sol, "__iter__"):
        pretty = [str(s) for s in list(sol)]
    else:
        pretty = [str(sol)]
    return {
        "operation": "حل معادلة",
        "equation": str(equation),
        "variable": str(v),
        "solutions": pretty,
        "success": True,
    }


def simplify_expr(expr_str: str) -> Dict[str, Any]:
    expr = _sympify(expr_str)
    return {"operation": "تبسيط", "original": str(expr), "simplified": str(simplify(expr))}


def factor_expr(expr_str: str) -> Dict[str, Any]:
    expr = _sympify(expr_str)
    return {"operation": "تحليل", "original": str(expr), "factored": str(factor(expr))}


# =========================
# خطوات توضيحية بسيطة (اختياري)
# =========================

def _steps_for_polynomial_eval(expr_str: str, at: float, value: Union[float, str]) -> list:
    return [
        {"id": "s1", "title": "تعويض", "text": f"نعوّض x = {at} في {expr_str}."},
        {"id": "s2", "title": "حساب جزئي", "text": "نحسب الحدود خطوة خطوة ثم نجمعها."},
        {"id": "s3", "title": "النتيجة", "text": f"قيمة الدالة عند x={at} تساوي {value}."},
    ]


def wrap_result_with_steps(math_result: dict) -> dict:
    """يضيف steps آليًا عندما يمكن استنتاجها."""
    res = dict(math_result or {})
    expr = str(res.get("expression", res.get("expr", "")))
    steps = res.get("steps", [])

    if "value" in res and "at" in res and not steps:
        steps = _steps_for_polynomial_eval(expr or "f(x)", res["at"], res["value"])

    if ("derivative" in res or "derivative_value" in res) and not steps:
        d = res.get("derivative", "")
        dv = res.get("derivative_value", None)
        steps = [
            {"id": "s1", "title": "اشتقاق", "text": f"المشتقة: {d}."},
            {"id": "s2", "title": "تعويض", "text": f"قيمة المشتقة عند النقطة: {dv}." if dv is not None else "لا توجد نقطة تقييم."},
        ]

    if ("integral" in res or "definite_integral" in res) and not steps:
        val = res.get("definite_integral", None)
        steps = [{"id": "s1", "title": "التكامل", "text": f"أوجدنا التكامل للتعبير {expr}."}]
        if val is not None:
            steps.append({"id": "s2", "title": "قيمة محددة", "text": f"قيمة التكامل المحدد = {val}."})

    res["steps"] = steps
    return res


# =========================
# موجه نصي بسيط (المطلوب)
# =========================

def solve_math_problem(query: str):
    """
    موجه نصي ذكي مبسّط: يطبّع الإدخال ويميز (حل/مشتق/تكامل/تقييم).
    """
    q = (query or "").strip()
    # تطبيع شائع
    q = (
        q.replace("^", "**")
         .replace("×", "*")
         .replace("−", "-")
         .replace("= 0", "=0")
         .replace("أوجد الجذور", "حل")
         .replace("احسب الجذور", "حل")
    )

    # معادلة؟
    if ("حل" in q) or ("=" in q):
        try:
            if "=" in q:
                left, right = q.split("=", 1)
                expr = left.split("حل")[-1].strip() + " = " + right.strip()
            else:
                # صيغة مثل: "حل 2*x**2 + 3*x - 2"
                core = q.split("حل")[-1].strip()
                expr = f"{core} = 0"
            return solve_equation(expr)
        except Exception as e:
            return {"success": False, "error": f"تعذّر تفسير المعادلة: {e}"}

    # مشتقة؟
    if any(k in q for k in ["مشتق", "اشتق", "deriv", "diff"]):
        expr = q
        for k in ["مشتق", "اشتق", "deriv", "diff", ":", "of"]:
            expr = expr.replace(k, "")
        res = differentiate(expr.strip())
        return wrap_result_with_steps(res)

    # تكامل؟
    if any(k in q for k in ["تكامل", "integral"]):
        txt = q.replace("integral", "تكامل")
        if "من" in txt and "إلى" in txt:
            # مثال: تكامل sin(x) من 0 إلى pi
            try:
                head, tail = txt.split("من", 1)
                expr = head.replace("تكامل", "").strip()
                a_txt, b_txt = tail.split("إلى", 1)
                a = _sympify(a_txt.strip())
                b = _sympify(b_txt.strip())
                res = integrate_expr(expr, a=float(a), b=float(b))
                return wrap_result_with_steps(res)
            except Exception:
                # محاولة تكامل غير محدد إن فشلت صيغة المحدد
                res = integrate_expr(txt.replace("تكامل", "").strip())
                return wrap_result_with_steps(res)
        else:
            res = integrate_expr(txt.replace("تكامل", "").strip())
            return wrap_result_with_steps(res)

    # تبسيط وتحليل (اختياري)
    if any(k in q for k in ["بسّط", "بسط", "simplify"]):
        return simplify_expr(q.replace("بسّط", "").replace("بسط", "").replace("simplify", "").strip())

    if any(k in q for k in ["حلّل", "حلل", "factor"]):
        return factor_expr(q.replace("حلّل", "").replace("حلل", "").replace("factor", "").strip())

    # افتراضي: تقييم/عرض
    res = evaluate_function(q)
    return wrap_result_with_steps(res)


# =========================
# كائن يصدّر باسم math_engine
# =========================

class MathEngine:
    def solve_math_problem(self, query: str):
        return solve_math_problem(query)

    # لمن يحتاج النداء المباشر للدوال:
    def evaluate(self, expr: str, at: Optional[float] = None, var: Optional[str] = None):
        return evaluate_function(expr, at=at, var=var)

    def differentiate(self, expr: str, order: int = 1, at: Optional[float] = None, var: Optional[str] = None):
        return differentiate(expr, order=order, at=at, var=var)

    def integrate(self, expr: str, a: Optional[float] = None, b: Optional[float] = None, var: Optional[str] = None):
        return integrate_expr(expr, a=a, b=b, var=var)

    def solve(self, eq: str, var: Optional[str] = None):
        return solve_equation(eq, var=var)

    def simplify(self, expr: str):
        return simplify_expr(expr)

    def factor(self, expr: str):
        return factor_expr(expr)


# هذا ما يقوم core/__init__.py باستيراده: from .math_engine import math_engine
math_engine = MathEngine()
