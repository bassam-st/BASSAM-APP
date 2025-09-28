# src/rag/retriever.py — RAG خفيف (BM25 فقط) مع دعم نصوص و PDF
import os, glob, re
from typing import List, Tuple
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

from rank_bm25 import BM25Okapi

DOCS_DIR = os.getenv("DOCS_DIR", "docs")

def _read_text_file(fp: str) -> str:
    try:
        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""

def _read_pdf_file(fp: str) -> str:
    if not fitz:
        return ""
    try:
        doc = fitz.open(fp)
        chunks = []
        for page in doc:
            chunks.append(page.get_text("text"))
        return "\n".join(chunks)
    except Exception:
        return ""

def _load_corpus() -> Tuple[List[str], List[str]]:
    files, texts = [], []
    patterns = ("*.txt","*.md","*.rst","*.html","*.htm","*.log","*.csv","*.tsv","*.json","*.yml","*.yaml","*.ini","*.pdf")
    for pat in patterns:
        for fp in glob.glob(os.path.join(DOCS_DIR, "**", pat), recursive=True):
            txt = ""
            if fp.lower().endswith(".pdf"):
                txt = _read_pdf_file(fp)
            else:
                txt = _read_text_file(fp)
            if txt and txt.strip():
                files.append(fp)
                texts.append(txt)
    return files, texts

def _tokenize_ar(s: str):
    s = re.sub(r"[^\w\u0600-\u06FF]+", " ", s)
    return s.lower().split()

_FILES, _TEXTS = _load_corpus()
_TOKS = [_tokenize_ar(t) for t in _TEXTS] if _TEXTS else []
_BM25 = BM25Okapi(_TOKS) if _TOKS else None

def query_index(query: str, top_k: int = 4):
    if not _BM25:
        return [("لم يتم إنشاء الفهرس", "أضف ملفات نصية أو PDF داخل مجلد docs/ ثم أعد التشغيل.")]
    q_tokens = _tokenize_ar(query or "")
    scores = _BM25.get_scores(q_tokens)
    idxs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    out = []
    for i in idxs:
        snippet = _TEXTS[i][:1200]  # قصّة مقتطف خفيف
        out.append((_FILES[i], snippet))
    return out
