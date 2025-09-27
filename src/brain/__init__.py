# src/brain/__init__.py
import math
import re

__all__ = ["safe_run"]

_ALLOWED = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "sqrt": math.sqrt,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "log": math.log, "log10": math.log10, "exp": math.exp,
    "abs": abs, "round": round
}

_MATH_PATTERN = re.compile(r"[0-9pi e\taufx\+\-\*\/\^\(\)\.\,\s]|sqrt|sin|cos|tan|asin|acos|atan|log10|log|exp|abs|round", re.I)

def _try_math(expr: str):
    # تبسيطات سريعة
    clean = expr.replace("^", "**")
    # تأكد أنه لا يحوي سوى رموز مسموحة (لتقليل المخاطر)
    if not _MATH_PATTERN.fullmatch(clean.replace(" ", "")):
        raise ValueError("تعبير غير رياضي أو يحوي دوال غير مدعومة.")

    # eval بقيود شديدة
    return eval(clean, {"__builtins__": {}}, _ALLOWED)

def safe_run(query: str) -> str:
    q = (query or "").strip()

    # 1) حاول كرياضيات بسيطة
    try:
        val = _try_math(q)
        return f"النتيجة: {val}"
    except Exception:
        pass

    # 2) رد عام بسيط (يمكن تطويره لاحقًا)
    return (
        "تلقيت سؤالك:\n"
        f"«{q}»\n\n"
        "هذه نسخة تجريبية خفيفة (نمط واحد Smart). "
        "للمسائل العامة سأعطيك ردًا موجزًا. "
        "للحسابات الرياضية اكتب التعبير مباشرة مثل: sqrt(16)+2*pi"
    )
