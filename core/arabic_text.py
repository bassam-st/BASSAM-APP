import re
from deep_translator import LibreTranslator
from googletrans import Translator as GoogleTranslator

_AR_RE = re.compile(r"[\u0600-\u06FF]")

def is_arabic(s: str) -> bool:
    return bool(_AR_RE.search(s or ""))

def normalize_spaces(s: str) -> str:
    import re as _r
    return _r.sub(r"\s+", " ", (s or "").strip())

def strip_html_preserve_lines(html: str) -> str:
    import re as _r
    txt = _r.sub(r"<\s*br\s*/?>", "\n", html, flags=_r.I)
    txt = _r.sub(r"</p\s*>", "\n", txt, flags=_r.I)
    txt = _r.sub(r"<[^>]+>", "", txt)
    return _r.sub(r"\n{3,}", "\n\n", txt)

def to_arabic(text: str) -> str:
    if not text: return ""
    try:
        lt = LibreTranslator(source="auto", target="ar", api_url="https://libretranslate.de")
        return lt.translate(text)[:4000]
    except Exception:
        try:
            gt = import re
from deep_translator import LibreTranslator

_AR_RE = re.compile(r"[\u0600-\u06FF]")

def is_arabic(s: str) -> bool:
    return bool(_AR_RE.search(s or ""))

def normalize_spaces(s: str) -> str:
    import re as _r
    return _r.sub(r"\s+", " ", (s or "").strip())

def to_arabic(text: str) -> str:
    if not text:
        return ""
    try:
        lt = LibreTranslator(source="auto", target="ar", api_url="https://libretranslate.de")
        return lt.translate(text)[:4000]
    except Exception:
        # لو الخدمة المجانية تعطّلت، رجّع النص كما هو بدل ما تفشل الإجابة
        return text
