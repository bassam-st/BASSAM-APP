# ====== RAG Retriever بسيط لتطبيق بسّام الذكي ======
# الهدف: استرجاع المقاطع الأقرب من ملفات PDF المخزنة في مجلد docs/
# يعتمد على FAISS + sentence-transformers

import os
import faiss
import pickle
from typing import List, Tuple
from sentence_transformers import SentenceTransformer, util
import fitz  # من مكتبة pymupdf لاستخراج النصوص من ملفات PDF

# المجلد الأساسي للملفات
DOCS_DIR = "docs"
INDEX_PATH = "docs/index.faiss"
META_PATH = "docs/meta.pkl"

# النموذج المستخدم لاستخراج التضمينات (embedding)
MODEL = SentenceTransformer("all-MiniLM-L6-v2")

# =======================================================
# دالة لاستخراج النصوص من ملفات PDF
# =======================================================
def extract_text_from_pdf(path: str) -> str:
    text = ""
    with fitz.open(path) as pdf:
        for page in pdf:
            text += page.get_text()
    return text

# =======================================================
# بناء الفهرس من جميع ملفات PDF الموجودة في docs/
# =======================================================
def build_index() -> None:
    docs, metas = [], []
    print("🔍 جاري قراءة ملفات PDF من:", DOCS_DIR)

    for file in os.listdir(DOCS_DIR):
        if not file.lower().endswith(".pdf"):
            continue
        path = os.path.join(DOCS_DIR, file)
        txt = extract_text_from_pdf(path)
        parts = [p.strip() for p in txt.split("\n") if len(p.strip()) > 100]
        docs.extend(parts)
        metas.extend([(file, i) for i in range(len(parts))])

    if not docs:
        print("⚠️ لا توجد ملفات PDF في المجلد:", DOCS_DIR)
        return

    print(f"📚 عدد المقاطع: {len(docs)} — جاري إنشاء الفهرس...")
    embeddings = MODEL.encode(docs, convert_to_tensor=False)
    dim = embeddings[0].shape[0]

    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss.write_index(index, INDEX_PATH)
    with open(META_PATH, "wb") as f:
        pickle.dump({"docs": docs, "metas": metas}, f)

    print("✅ تم إنشاء الفهرس بنجاح!")

# =======================================================
# دالة البحث داخل الفهرس
# =======================================================
def query_index(q: str, top_k: int = 3) -> List[Tuple[str, str]]:
    if not os.path.exists(INDEX_PATH) or not os.path.exists(META_PATH):
        return [("⚠️ لم يتم إنشاء الفهرس بعد.", "")]

    index = faiss.read_index(INDEX_PATH)
    with open(META_PATH, "rb") as f:
        meta = pickle.load(f)

    docs = meta["docs"]
    metas = meta["metas"]

    q_emb = MODEL.encode([q], convert_to_tensor=False)
    D, I = index.search(q_emb, top_k)

    results = []
    for idx in I[0]:
        if 0 <= idx < len(docs):
            file, part = metas[idx]
            results.append((file, docs[idx][:400] + "..."))

    return results

# =======================================================
# مثال عند التشغيل اليدوي
# =======================================================
if __name__ == "__main__":
    if not os.path.exists(INDEX_PATH):
        build_index()
    else:
        print("🔎 اختبار البحث:")
        q = input("اكتب سؤالك: ")
        for file, text in query_index(q):
            print(f"\n📘 {file}\n{text}\n")
