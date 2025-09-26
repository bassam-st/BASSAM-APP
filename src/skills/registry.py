# src/skills/registry.py — v7 Skills Router (compatible)
import re

# ---- optional imports (won't crash if file missing)
from . import math_v7  # هذه موجودة أكيد
try:
    from . import physics_v7
except Exception:
    physics_v7 = None
try:
    from . import electrical_v7
except Exception:
    electrical_v7 = None
try:
    from . import network_v7
except Exception:
    network_v7 = None
try:
    from . import chemistry_v7
except Exception:
    chemistry_v7 = None

# اجمع المهارات الموجودة فقط
SKILLS = [s for s in [math_v7, physics_v7, electrical_v7, chemistry_v7, network_v7] if s is not None]

MATH_HINTS = ("حل", "اشتق", "مشتقة", "تكامل", "بسّط", "بسط", "factor", "=", "sin", "cos", "sqrt", "pi", "**")

def is_mathy(q: str) -> bool:
    q = (q or "")
    qn = q.replace(" ", "")
    return any(k in q for k in MATH_HINTS) or any(ch in qn for ch in ["=", "^", "*", "/", "+", "-"])

def _call_skill(skill, q: str):
    """ينادي الدالة المتاحة داخل المهارة بالترتيب."""
    # math_v7 الجديد عنده run_math_query
    if hasattr(skill, "run_math_query"):
        return skill.run_math_query(q)
    # بعض المهارات القديمة تستخدم solve أو run
    if hasattr(skill, "solve"):
        return skill.solve(q)
    if hasattr(skill, "run"):
        return skill.run(q)
    return None

def route_to_skill(q: str, prefer: str = "") -> str | None:
    """يمرّر السؤال للمهارة المناسبة ويرجع HTML أو None."""
    q = (q or "").strip()
    ordered = list(SKills := SKILLS)  # نسخة

    # تفضيل مسار معيّن لو طالبته الواجهة
    pref_map = {
        "math": math_v7,
        "physics": physics_v7,
        "electrical": electrical_v7,
        "network": network_v7,
        "chemistry": chemistry_v7,
    }
    pref_skill = pref_map.get(prefer)
    if pref_skill and pref_skill in ordered:
        ordered = [pref_skill] + [s for s in ordered if s is not pref_skill]

    # إن كان السؤال رياضياً بوضوح قدّم الرياضيات أولًا
    if is_mathy(q) and math_v7 in ordered and ordered[0] is not math_v7:
        ordered = [math_v7] + [s for s in ordered if s is not math_v7]

    # جرّب المهارات بالترتيب
    for skill in ordered:
        try:
            # إن كانت المهارة توفر can_handle استخدمها، وإلا جرّب مباشرة
            if hasattr(skill, "can_handle"):
                if not skill.can_handle(q):
                    continue
            html = _call_skill(skill, q)
            if html:
                return html
        except Exception:
            continue

    # لا أحد التقطه: إن كان رياضي حاول math_v7 كـ fallback
    if is_mathy(q) and math_v7:
        try:
            return _call_skill(math_v7, q)
        except Exception:
            pass

    return None
