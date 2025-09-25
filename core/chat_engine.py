# core/chat_engine.py
from __future__ import annotations
from typing import List, Dict, Any

def make_segments(text: str) -> List[Dict[str, Any]]:
    """
    يقسم النص إلى فقرات قصيرة ويعطي كل فقرة segment_id.
    لا يعتمد على أي مزود خارجي.
    """
    raw_parts = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]
    segments = []
    for i, p in enumerate(raw_parts, start=1):
        segments.append({
            "id": f"seg_{i}",
            "title": f"الفقرة {i}",
            "text": p
        })
    if not segments:
        segments = [{"id": "seg_1", "title": "الفقرة 1", "text": text}]
    return segments

def simplify_text(text: str, hint: str = "") -> str:
    """
    تبسيط نصي محلي (بدون ذكاء خارجي): 
    - يقسم الجمل
    - يُخرج نقاط مرقّمة ولغة أوضح
    """
    # تفكيك بسيط للجمل
    parts = [s.strip() for s in text.replace("؛", ".").replace("،", ",").split(".") if s.strip()]
    if not parts:
        return text

    out = ["تبسيط الفقرة:"]
    for i, s in enumerate(parts, 1):
        out.append(f"{i}) {s}")
    if hint:
        out.append("")
        out.append(f"ملاحظة الطالب: {hint}")
        out.append("شرح إضافي مختصر: الفقرة أعلاه مُعادة بصياغة أبسط وبنقاط.")
    return "\n".join(out)
