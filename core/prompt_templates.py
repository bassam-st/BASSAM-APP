# core/prompt_templates.py
from __future__ import annotations

TEMPLATES = {
    "answer": (
        "أنت مساعد عربي واضح ومختصر.\n"
        "السؤال: {question}\n"
        "المعطيات/السياق:\n{context}\n"
        "أجب بدقة وبنقاطٍ مرتبة."
    ),
    "math_explain": (
        "اشرح الحل خطوة بخطوة وبالعربية المبسطة:\nالمسألة: {problem}\n"
        "إن وُجدت خطوات وسيطة فاذكرها."
    ),
    "summarize": (
        "لخّص النص التالي في {sentences} جمل عربية واضحة:\n{content}"
    ),
}

def render(name: str, **kwargs) -> str:
    tpl = TEMPLATES.get(name, "{x}")
    return tpl.format(**kwargs)
