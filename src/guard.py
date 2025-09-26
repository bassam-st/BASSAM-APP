# src/guard.py
import time, traceback, logging
from typing import Optional, Callable
from src.autoheal import MATH_HEALER, normalize_math_text

logging.basicConfig(level=logging.INFO)

# نحن لا نوقف المهارة نهائياً؛ فقط نهدّئها لحظات إذا تكررت الأخطاء
MAX_FAILS  = 2
COOLDOWN_S = 60

_STATE: dict[str, dict] = {}  # {"skill": {"fails": int, "until": epoch}}

def _state(skill: str) -> dict:
    if skill not in _STATE:
        _STATE[skill] = {"fails": 0, "until": 0}
    return _STATE[skill]

def circuit_allows(skill: str) -> bool:
    return time.time() >= _state(skill)["until"]

def record_success(skill: str) -> None:
    st = _state(skill)
    st["fails"] = 0
    st["until"] = 0

def record_failure(skill: str) -> None:
    st = _state(skill)
    st["fails"] += 1
    if st["fails"] >= MAX_FAILS:
        st["until"] = time.time() + COOLDOWN_S
        logging.warning(f"[Guard] تهدئة مؤقتة للمهارة {skill} لمدة {COOLDOWN_S}s")

def _pick_healer(skill: str):
    # حالياً مهيّأ للرياضيات؛ لاحقاً أضف Healers لمهارات أخرى
    return MATH_HEALER if skill == "math" else None

def safe_call(skill: str, func: Callable[[str], str], q: str) -> Optional[str]:
    """
    Self-Improve:
      1) جرّب الدالة كما هي
      2) طبّق إصلاحات ذكية (autoheal) حتى ينجح
      3) في حال تكرار الفشل، نهدّئ المحاولات قليلًا لكن نظل نحاول بإصلاح خفيف
    """
    # لو في فترة تهدئة: جرب إصلاح خفيف سريع بدل الرفض
    if not circuit_allows(skill):
        q2 = normalize_math_text(q) if skill == "math" else q
        try:
            out = func(q2)
            if out:
                record_success(skill)
                return out
        except Exception:
            return None

    # 1) محاولة مباشرة
    try:
        out = func(q)
        if out:
            record_success(skill)
            return out
    except Exception as e:
        logging.debug(f"[{skill}] raw fail: {e}")

    # 2) خطط الإصلاح
    healer = _pick_healer(skill)
    if healer:
        try:
            out, tag = healer.try_run(func, q)
            if out:
                logging.info(f"[{skill}] healed via {tag}")
                record_success(skill)
                return out
        except Exception:
            pass

    # 3) فشل أخير
    record_failure(skill)
    return None
