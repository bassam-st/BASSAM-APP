# src/skills/registry.py — v7 Skills Router
import re
from . import math_v7, physics_v7, electrical_v7, network_v7, chemistry_v7

# ترتيب التجربة (من الأكثر احتمالًا)
SKILLS = [
    math_v7,
    physics_v7,
    electrical_v7,
    chemistry_v7,
    network_v7,
]

MATH_HINTS = ("حل", "اشتق", "مشتقة", "تكامل", "بسّط", "بسط", "factor", "=", "sin", "cos", "sqrt", "pi", "**")

def is_mathy(q: str) -> bool:
    qn = (q or "").replace(" ", "")
    return any(k in q for k in MATH_HINTS) or any(ch in qn for ch in ["=", "^", "*", "/", "+", "-"])

def route_to_skill(q: str, prefer: str = "") -> str | None:
    """يمرّر السؤال للمهارة المناسبة ويرجع HTML أو None."""
    q = (q or "").strip()
    ordered = SKILLS

    # تفضيل مسار معيّن لو طالبته الواجهة
    if prefer == "math":
        ordered = [math_v7] + [s for s in SKILLS if s is not math_v7]
    elif prefer == "physics":
        ordered = [physics_v7] + [s for s in SKILLS if s is not physics_v7]
    elif prefer == "electrical":
        ordered = [electrical_v7] + [s for s in SKILLS if s is not electrical_v7]
    elif prefer == "network":
        ordered = [network_v7] + [s for s in SKILLS if s is not network_v7]
    elif prefer == "chemistry":
        ordered = [chemistry_v7] + [s for s in SKILLS if s is not chemistry_v7]

    # إن كان السؤال رياضياً بوضوح قدّم الرياضيات أولًا
    if is_mathy(q) and math_v7 not in ordered[:1]:
        ordered = [math_v7] + [s for s in ordered if s is not math_v7]

    for skill in ordered:
        try:
            if hasattr(skill, "can_handle") and skill.can_handle(q):
                html = skill.solve(q)
                if html:
                    return html
        except Exception:
            continue
    return None
