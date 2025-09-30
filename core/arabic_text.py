# -*- coding: utf-8 -*-
# أدوات النص العربي: كشف العربية، تنظيف HTML، و ترجمة إلى العربية

import re
from bs4 import BeautifulSoup
from deep_translator import LibreTranslator

from .utils import (
    convert_arabic_numbers,
    normalize_spaces,
    is_arabic as _is_arabic,
    clean_html as _clean_html,  # نستخدمه أحيانًا
)

# ===== واجهات جاهزة للاستخدام من باقي المشروع =====

def is_arabic(text: str) -> bool:
    """يعيد True إذا كان النص يحتوي على أحرف عربية."""
    return _is_arabic(text)

def strip_html_preserve_lines(html_text: str) -> str:
    """
    يحذف وسوم HTML مع الحفاظ على فواصل الأسطر (يدعم <br> و </p>)
    ويضغط الأسطر الفارغة.
    """
    if not html_text:
        return ""
    txt = re.sub(r"<\s*br\s*/?>", "\n", html_text, flags=re.I)
    txt = re.sub(r"</\s*p\s*>", "\n", txt, flags=re.I)
    txt = BeautifulSoup(txt, "html.parser").get_text("\n")
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()

def normalize_text(text: str) -> str:
    """
    تنميط نص عربي/مختلط:
    - إزالة التشكيل/المدّة (من utils)
    - توحيد الأرقام العربية/الفارسية
    - ضغط المسافات
    """
    from .utils import normalize_text as _normalize_text  # تجنب الدورات
    return _normalize_text(text)

def to_arabic(text: str) -> str:
    """
    ترجمة أي نص إلى العربية باستخدام LibreTranslate (مجاني).
    عند فشل الخدمة نرجع النص كما هو (حتى لا تفشل الاستجابة).
    """
    if not text:
        return ""
    try:
        lt = LibreTranslator(
            source="auto",
            target="ar",
            api_url="https://libretranslate.de",  # خدمة عامة مجانية
        )
        out = lt.translate(text)
        return normalize_spaces(convert_arabic_numbers(out))
    except Exception:
        return text
