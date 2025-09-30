# core/utils.py — أدوات مساعدة لتطبيق بسام الذكي

from typing import List, Dict, Tuple, Iterable, Union
import os, re, glob, json
from bs4 import BeautifulSoup

# ==== إنشاء مجلدات بأمان ====
def ensure_dirs(paths: Union[str, Iterable[str]]) -> None:
    """ينشئ مجلدات بأمان (حتى لو كانت موجودة)"""
    if isinstance(paths, (str, bytes, os.PathLike)):
        paths = [paths]
    for p in paths:
        if not p:
            continue
        try:
            os.makedirs(p, exist_ok=True)
        except Exception as e:
            print(f"[ensure_dirs] skip {p}: {e}")

# ==== إزالة التكرار من الروابط ====
def dedup_by_url(hits: List[Dict]) -> List[Dict]:
    seen, out = set(), []
    for h in hits:
        u = h.get("url")
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(h)
    return out

# ==== ضبط القيم بين حدين ====
def clamp(x, lo, hi): return max(lo, min(hi, x))

# ==== بحث بسيط في الملفات المحلية ====
def simple_md_search(folder: str, query: str, max_files: int = 40, max_chars: int = 6000):
    files = []
    for ext in ("*.md", "*.txt"):
        files += glob.glob(os.path.join(folder, ext))
    hits = []
    qs = query.lower()
    for p in files[:max_files]:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                t = f.read()
                if qs in t.lower():
                    hits.append((p, t[:max_chars]))
        except Exception:
            pass
    return hits

# ==== OCR: استخراج النص من الصور ====
try:
    from PIL import Image
    import pytesseract
except ImportError:
    Image = None
    pytesseract = None

def extract_image_text(path: str) -> str:
    """يستخرج النصوص من الصور (عربية + إنجليزية)"""
    if not Image or not pytesseract:
        return ""
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="eng+ara")
        return text.strip()
    except Exception as e:
        print(f"[OCR ERROR] {e}")
        return ""

# ==== تحويل الأرقام العربية إلى إنجليزية ====
_ARABIC_DIGITS = {
    "٠": "0","١": "1","٢": "2","٣": "3","٤": "4",
    "٥": "5","٦": "6","٧": "7","٨": "8","٩": "9",
    "۰": "0","۱": "1","۲": "2","۳": "3","۴": "4",
    "۵": "5","۶": "6","۷": "7","۸": "8","۹": "9",
}

def convert_arabic_numbers(text: str) -> str:
    """تحويل الأرقام العربية والفارسية إلى أرقام إنجليزية"""
    if not text:
        return ""
    return "".join(_ARABIC_DIGITS.get(ch, ch) for ch in text)

# ==== التحقق من أن النص عربي ====
def is_arabic(text: str) -> bool:
    """يتحقق إن كان النص يحتوي على أحرف عربية"""
    if not text:
        return False
    return bool(re.search(r"[\u0600-\u06FF]", text))

# ==== تنظيف HTML ====
def clean_html(html_text: str) -> str:
    """يحذف وسوم HTML ويحوّل <br> و </p> إلى أسطر جديدة"""
    if not html_text:
        return ""
    txt = re.sub(r"<\s*br\s*/?>", "\n", html_text, flags=re.I)
    txt = re.sub(r"</\s*p\s*>", "\n", txt, flags=re.I)
    txt = BeautifulSoup(txt, "html.parser").get_text("\n")
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()

# ==== تنميط النصوص ====
_ARABIC_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
_TATWEEL_RE = re.compile(r"\u0640")  # ـ

def normalize_spaces(s: str) -> str:
    """ضغط المسافات"""
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()

def normalize_text(s: str) -> str:
    """تنميط النص العربي"""
    if not s:
        return ""
    s = _ARABIC_DIACRITICS_RE.sub("", s)
    s = _TATWEEL_RE.sub("", s)
    s = convert_arabic_numbers(s)
    s = normalize_spaces(s)
    return s
