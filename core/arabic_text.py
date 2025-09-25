# core/arabic_text.py
from __future__ import annotations
import re

_AR_DIAC = re.compile(r"[\u0617-\u061A\u064B-\u0652\u0670\u06D6-\u06ED]")
_PUNCT = re.compile(r"[^\w\s\u0600-\u06FF]+")

def normalize_ar(text: str) -> str:
    text = _AR_DIAC.sub("", text)             # إزالة التشكيل
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي").replace("ة", "ه")
    text = _PUNCT.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()

def is_arabic(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", text))

def split_sentences(text: str) -> list[str]:
    # فصل جُمَل بسيط
    parts = re.split(r"(?<=[\.!\؟\!])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]
