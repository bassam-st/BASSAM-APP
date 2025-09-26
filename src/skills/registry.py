# src/skills/registry.py — v7 Skills Router
import re
from . import math_v7, physics_v7, chemistry_v7, electrical_v7, network_v7

SKILLS = [
    math_v7,
    physics_v7,
    chemistry_v7,
    electrical_v7,
    network_v7,
]

MATH_HINTS = ("حل","مشتقة","اشتق","تكامل","بسّط","بسط","factor","=","sin","cos","tan","sqrt","**","log","pi")

def is_mathy(q: str) -> bool:
    qn = (q or "").replace(" ", "")
    return any(k in q for k in MATH_HINTS) or any(ch in qn for ch in ["=","∫","^","**"])

def route_to_skill(q: str, prefer: str = "") -> str | None:
    q = (q or "").strip()
    ordered = SKILLS

    # تفضيل مهارة معينة إن طلب
    if prefer == "math":
        ordered = [math_v7] + [s for s in SKILLS if s is not math_v7]

    for skill in ordered:
        try:
            if skill.can_handle(q):
                html = skill.solve(q)
                if html and len(html) > 0:
                    return html
        except Exception:
            continue
    return None
