# src/autoheal.py
import re
from typing import Callable, List, Tuple, Optional

AR_NUM = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
SYM_FIXES = {
    "÷": "/", "×": "*", "^": "**", "،": ",",
    "٫": ".", "∗": "*", "−": "-", "–": "-", "—": "-",
}

MATH_WORDS = {
    "جذر": "sqrt", "جذر(": "sqrt(", "لوغاريتم": "log",
    "جيب تمام": "cos", "جيب": "sin", "ظل": "tan",
}

def normalize_math_text(q: str) -> str:
    s = (q or "").strip()
    s = s.translate(AR_NUM)               # أرقام عربية → لاتينية
    for k, v in SYM_FIXES.items():        # رموز شائعة
        s = s.replace(k, v)
    # كلمات عربية → دوال
    for k, v in MATH_WORDS.items():
        s = s.replace(k, v)
    # 2x → 2*x  ، (x)(x+1) → (x)*(x+1)
    s = re.sub(r"(\d)([a-zA-Z\(])", r"\1*\2", s)
    s = re.sub(r"(\))(\()", r"\1*\2", s)
    # توحيد أوامر عربية
    s = s.replace("بسط", "بسّط").replace("حلل", "حلّل")
    return s

class AutoHealer:
    """يشغّل دالة (مثل solve_query) عبر خطط تصحيح متتالية حتى النجاح."""
    def __init__(self, plans: Optional[List[Callable[[str], str]]] = None):
        self.plans = plans or []

    def try_run(self, fn: Callable[[str], str], q: str) -> Tuple[Optional[str], str]:
        # 0) المحاولة الأولى كما هي
        try:
            out = fn(q)
            if out and len(out) > 0:
                return out, "success:raw"
        except Exception:
            pass

        # 1..N) طبّق خطط الإصلاح بالترتيب
        current = q
        for i, plan in enumerate(self.plans, start=1):
            try:
                current = plan(current)
                out = fn(current)
                if out and len(out) > 0:
                    return out, f"success:plan{i}"
            except Exception:
                continue
        return None, "failed"

# خطط جاهزة للرياضيات
def plan_normalize_math(q: str) -> str:
    return normalize_math_text(q)

def plan_force_equation(q: str) -> str:
    # إن لم يوجد = وحُدّد "حل ..." جرّب تحويله لمعادلة = 0
    m = re.search(r"حل\s+(.+)", q)
    if m and "=" not in q:
        expr = m.group(1)
        return f"حل {expr} = 0"
    return q

MATH_HEALER = AutoHealer(plans=[plan_normalize_math, plan_force_equation])
