# core/utils.py — أدوات مساعدة لـ OCR و PDF
from typing import List, Dict, Tuple
import os, re, glob, json

# ============ البحث البسيط في الملفات المحلية ============
def dedup_by_url(hits: List[Dict]) -> List[Dict]:
    seen, out = set(), []
    for h in hits:
        u = h.get("url")
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(h)
    return out


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def simple_md_search(folder: str, query: str, max_files: int = 40, max_chars: int = 6000) -> List[Tuple[str, str]]:
    files = []
    for ext in ("*.md", "*.txt"):
        files += glob.glob(os.path.join(folder, ext))

    hits = []
    q = query.lower()
    for p in files[:max_files]:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                t = f.read()
            if q in t.lower():
                hits.append((p, t[:max_chars]))
        except Exception:
            pass
    return hits


# ============ OCR من الصور ============
try:
    from PIL import Image
    import pytesseract
except ImportError:
    Image = None
    pytesseract = None


def extract_image_text(path: str) -> str:
    """استخراج النص من الصور"""
    if not Image or not pytesseract:
        return ""
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="eng+ara")
        return text.strip()
    except Exception as e:
        print(f"[OCR ERROR] {e}")
        return ""


# ============ استخراج النص من PDF ============
try:
    from pdfminer.high_level import extract_text
except ImportError:
    extract_text = None


def extract_pdf_text(path: str) -> str:
    """استخراج النص من ملفات PDF"""
    try:
        if extract_text:
            return extract_text(path) or ""
        return ""
    except Exception as e:
        print(f"[PDF ERROR] {e}")
        return ""


# ============ تحويل الأرقام العربية إلى إنجليزية ============
_ARABIC_DIGITS = {
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
}


def convert_arabic_numbers(text: str) -> str:
    if not text:
        return ""
    return "".join(_ARABIC_DIGITS.get(ch, ch) for ch in text)


# ============ كشف النص العربي ============
def is_arabic(text: str) -> bool:
    """يتحقق هل النص يحتوي على حروف عربية"""
    if not text:
        return False
    return bool(re.search(r"[\u0600-\u06FF]", text))
    def ensure_dirs(*dirs):
    for d in dirs:
        os.makedirs(d, exist_ok=True)
