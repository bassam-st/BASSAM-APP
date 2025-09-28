# src/rag/retriever.py — استرجاع مباشر من ملفات docs/ بدون Cache (بديل)

import os, glob
from sentence_transformers import SentenceTransformer, util

_model = None
def _model_load():
    global _model
    if _model is None:
        _model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    return _model

def _read_all(docs_dir="docs"):
    files=[]
    for ext in ("*.txt","*.md"): files += glob.glob(os.path.join(docs_dir, ext))
    files += glob.glob(os.path.join(docs_dir, "*.pdf"))
    items=[]
    for p in files:
        text=""
        if p.lower().endswith(".pdf"):
            try:
                import fitz
                with fitz.open(p) as doc:
                    for page in doc:
                        text += page.get_text()
            except Exception:
                continue
        else:
            try:
                text=open(p,"r",encoding="utf-8",errors="ignore").read()
            except Exception:
                continue
        if text.strip():
            items.append((os.path.basename(p), text))
    return items

def query_index(q: str, top_k: int = 4, docs_dir="docs"):
    items=_read_all(docs_dir)
    if not items: return [("لم يتم إنشاء الفهرس أو لا توجد ملفات في docs/", "")]
    model=_model_load()
    texts=[t for _,t in items]
    vq=model.encode([q], normalize_embeddings=True)
    vs=model.encode(texts, normalize_embeddings=True)
    sims = (vq @ vs.T)[0]
    order = sims.argsort()[::-1][:top_k]
    results=[]
    for i in order:
        fname, full = items[i]
        snippet = full[:1200]
        results.append((fname, snippet))
    return results
