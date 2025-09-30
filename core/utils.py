# core/utils.py — helpers
from typing import List, Dict, Tuple
import os, re, glob, json

def dedup_by_url(hits: List[Dict]) -> List[Dict]:
    seen, out = set(), []
    for h in hits:
        u = h.get("url")
        if not u or u in seen: continue
        seen.add(u); out.append(h)
    return out

def clamp(x, lo, hi): return max(lo, min(hi, x))

def simple_md_search(folder: str, query: str, max_files: int = 40, max_chars: int = 6000) -> List[Tuple[str,str]]:
    files = []
    for ext in ("*.md","*.txt"):
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
