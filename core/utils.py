# core/utils.py — أدوات مساعدة خفيفة

from typing import List, Dict
import os, glob

def ensure_dirs(*paths: str) -> None:
    """ينشئ المجلدات لو غير موجودة (لا يُرمي خطأ)."""
    for p in paths:
        try:
            os.makedirs(p, exist_ok=True)
        except Exception as e:
            print(f"[ensure_dirs] {p}: {e}")

def dedup_by_url(hits: List[Dict]) -> List[Dict]:
    """حذف التكرار حسب الرابط"""
    seen, out = set(), []
    for h in hits:
        u = h.get("url")
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(h)
    return out

def simple_md_search(folder: str, query: str, max_files: int = 40, max_chars: int = 6000):
    """بحث بسيط داخل ملفات .md / .txt (اختياري للاستخدام المحلي)"""
    files = []
    for ext in ("*.md", "*.txt"):
        files += glob.glob(os.path.join(folder, ext))
    hits, qs = [], query.lower()
    for p in files[:max_files]:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                t = f.read()
            if qs in t.lower():
                hits.append({"path": p, "snippet": t[:max_chars]})
        except Exception:
            pass
    return hits
