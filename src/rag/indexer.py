# src/rag/indexer.py
import os, glob
import fitz  # PyMuPDF
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from diskcache import Cache

cache = Cache(".cache")

DOCS_DIR   = os.getenv("RAG_DOCS_DIR", "docs")
MODEL_NAME = os.getenv("RAG_EMB_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

def read_pdf(path: str) -> str:
    doc = fitz.open(path)
    texts = []
    for p in doc:
        texts.append(p.get_text())
    return "\n".join(texts)

def chunk_text(text: str, size: int = 700, overlap: int = 80):
    i = 0
    n = len(text)
    while i < n:
        yield text[i:i+size]
        i += max(1, size - overlap)

def build_index() -> dict:
    os.makedirs(DOCS_DIR, exist_ok=True)
    files = sorted(glob.glob(os.path.join(DOCS_DIR, "*.pdf")))
    if not files:
        raise RuntimeError(f"لا توجد ملفات PDF داخل {DOCS_DIR}")

    emb = SentenceTransformer(MODEL_NAME)

    chunks, metas = [], []
    for fp in files:
        base = os.path.basename(fp)
        txt = read_pdf(fp)
        for i, c in enumerate(chunk_text(txt)):
            chunks.append(c)
            metas.append({"source": base, "chunk": i})

    if not chunks:
        raise RuntimeError("لم يتم استخراج أي نصوص من ملفات PDF")

    X = emb.encode(chunks, convert_to_numpy=True, show_progress_bar=True, normalize_embeddings=True)
    dim = X.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(X)

    cache.set("rag:index", index)
    cache.set("rag:chunks", chunks)
    cache.set("rag:metas", metas)

    return {"files": [os.path.basename(f) for f in files], "chunks": len(chunks), "model": MODEL_NAME}

def is_ready() -> bool:
    return bool(cache.get("rag:index") and cache.get("rag:chunks") and cache.get("rag:metas"))
