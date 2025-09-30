from typing import List
import os, json

def dedup_by_url(hits):
    seen, out = set(), []
    for h in hits:
        u = h.get("url");
        if not u or u in seen: continue
        seen.add(u); out.append(h)
    return out

def ensure_dirs(paths: List[str]):
    for p in paths:
        os.makedirs(p, exist_ok=True)
from pdfminer.high_level import extract_text

def extract_pdf_text(path: str) -> str:
    try:
        return extract_text(path) or ""
    except Exception:
        return ""
        # ====== OCR: استخراج النص من الصور ======
try:
    from PIL import Image
    import pytesseract
except ImportError:
    Image = None
    pytesseract = None

def extract_image_text(path: str) -> str:
    """قراءة النص من الصورة (OCR)"""
    if not Image or not pytesseract:
        return ""
    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang="eng+ara")  # يدعم العربية والإنجليزية
        return text.strip()
    except Exception as e:
        print(f"[OCR ERROR] {e}")
        return ""
