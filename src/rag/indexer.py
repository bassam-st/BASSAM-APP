# src/rag/indexer.py — يبني فهرس من ملفات docs/ (اختياري)

import os, glob
from diskcache import Cache
import faiss
from sentence_transformers import SentenceTransformer

cache = Cache(".cache")

def chunk_text(txt, n=700, overlap=80):
    out=[]; i=0
    while i < len(txt):
        out.append(txt[i:i+n])
        i += n - overlap
    return out

def is_ready() -> bool:
    return all(cache.get(k) is not None for k in ["rag:index","rag:chunks","rag:metas"])

def build_index(docs_dir="docs", model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
    files = []
    for ext in ("*.txt","*.md"):
        files += glob.glob(os.path.join(docs_dir, ext))
    try:
        import fitz  # PyMuPDF
        files += glob.glob(os.path.join(docs_dir, "*.pdf"))
    except Exception:
        pass

    if not files:
        return "لا توجد ملفات داخل docs/"

    model = SentenceTransformer(model_name)
    chunks, metas = [], []

    for path in files:
        text=""
        if path.lower().endswith(".pdf"):
            try:
                import fitz
                with fitz.open(path) as doc:
                    for page in doc:
                        text += page.get_text()
            except Exception:
                continue
        else:
            try:
                text = open(path, "r", encoding="utf-8", errors="ignore").read()
            except Exception:
                continue

        for ch in chunk_text(text):
            chunks.append(ch)
            metas.append({"source": os.path.basename(path)})

    if not chunks:
        return "لم يتم استخراج نصوص صالحة."

    X = model.encode(chunks, convert_to_numpy=True, normalize_embeddings=True)
    index = faiss.IndexFlatIP(X.shape[1])
    index.add(X)

    cache.set("rag:index", index)
    cache.set("rag:chunks", chunks)
    cache.set("rag:metas", metas)
    return f"تم بناء فهرس RAG لعدد {len(chunks)} مقطع من {len(files)} ملف."
