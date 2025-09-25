# core/local_brain.py
from __future__ import annotations
import os, glob
from typing import List, Tuple
from .arabic_text import normalize_ar, split_sentences
from .summarizer import summarize

DATA_DIRS = ["data", "data/notes"]

def _read_corpus() -> List[Tuple[str, str]]:
    docs = []
    for d in DATA_DIRS:
        for p in glob.glob(os.path.join(d, "**", "*.*"), recursive=True):
            if os.path.isdir(p): 
                continue
            if os.path.splitext(p)[1].lower() not in (".md", ".txt"):
                continue
            try:
                with open(p, "r", encoding="utf-8") as f:
                    docs.append((p, f.read()))
            except Exception:
                pass
    return docs

_CORPUS = _read_corpus()

def retrieve(query: str, top_k: int = 3) -> List[Tuple[str, str]]:
    """إرجاع أفضل نصوص محلية مطابقة للاستعلام (مطابقة كلمات بسيطة)."""
    if not _CORPUS:
        return []
    q = set(normalize_ar(query).split())
    scored = []
    for path, content in _CORPUS:
        text = normalize_ar(content)
        toks = set(text.split())
        score = len(q.intersection(toks))
        if score > 0:
            scored.append((score, path, content))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [(p, c) for _, p, c in scored[:top_k]]

def answer_local(query: str) -> dict:
    hits = retrieve(query, top_k=3)
    if not hits:
        return {"found": False}
    merged = "\n\n".join(c for _, c in hits)
    return {
        "found": True,
        "sources": [p for p, _ in hits],
        "summary": summarize(merged, max_sentences=4, query=query)
    }
