# core/arabic_text.py — Arabic helpers + translation
import re
from typing import Optional
from deep_translator import LibreTranslator
from googletrans import Translator as GoogleTranslator

_AR_RE = re.compile(r"[\u0600-\u06FF]")

def is_arabic(s: str) -> bool:
    return bool(_AR_RE.search(s or ""))

def normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def strip_html_preserve_lines(html: str) -> str:
    # نحافظ على فواصل الأسطر
    txt = re.sub(r"<\s*br\s*/?>", "\n", html, flags=re.I)
    txt = re.sub(r"</p\s*>", "\n", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", "", txt)
    return re.sub(r"\n{3,}", "\n\n", txt)

def to_arabic(text: str) -> str:
    """ترجمة آمنة للعربية مع مسارين: LibreTranslate ثم جوجل مجاناً."""
    if not text: return ""
    try:
        # يوجد سيرفرات عامة لـ LibreTranslate — قد تُقيَّد أحياناً
        lt = LibreTranslator(source="auto", target="ar", api_url="https://libretranslate.de")
        return lt.translate(text)[:4000]
    except Exception:
        try:
            gt = GoogleTranslator()
            return gt.translate(text, dest="ar").text[:4000]
        except Exception:
            return text  # نُعيد النص كما هو إذا فشلت الترجمة
