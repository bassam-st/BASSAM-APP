# ============ إضافة البحث المتقدّم + تنزيل الروابط (جاهزة للصق) ============
# ملاحظة: الصق هذا القسم بعد تعريف app = FastAPI(...)

# --- وارد أن تكون بعض هذه المستوردات موجودة مسبقًا؛ إعادة الاستيراد آمنة ---
import os, time, re
from urllib.parse import urlparse
import httpx
from fastapi import Query, Body, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

# DuckDuckGo + قراءة الصفحات
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
try:
    from readability import Document
except Exception:
    Document = None

# بدائل آمنة إن لم تكن متوفرة في ملفك:
try:
    summarize_text
except NameError:
    # تلخيص مبسّط احتياطي (يفضَّل دالتك الأصلية إن كانت موجودة)
    def summarize_text(txt: str, max_sentences: int = 3) -> str:
        txt = (txt or "").strip()
        if not txt:
            return ""
        # جَمِّع أول جُمَلٍ قصيرة كنّسخة احتياطية
        parts = re.split(r"[\.!\؟\!]\s+", txt)
        return " ".join(parts[:max_sentences])[:600]

try:
    ensure_safe_filename
except NameError:
    def ensure_safe_filename(name: str) -> str:
        name = re.sub(r"[^\w\-.]+", "_", name or "")
        return name[:120] or f"file_{int(time.time())}"

# تأكّد من المسارات إن لم تكن معرفة
DATA_DIR     = globals().get("DATA_DIR", "data")
FILES_DIR    = globals().get("FILES_DIR", "files")
UPLOADS_DIR  = globals().get("UPLOADS_DIR", os.path.join(FILES_DIR, "uploads"))
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# استخراج نص PDF احتياطي إن لم توجد دالتك
try:
    extract_pdf_text
except NameError:
    try:
        from pypdf import PdfReader
    except Exception:
        PdfReader = None
    def extract_pdf_text(path: str) -> str:
        if not PdfReader:
            return ""
        try:
            reader = PdfReader(path)
            return "\n".join((p.extract_text() or "") for p in reader.pages)
        except Exception:
            return ""

# إعادة بناء الفهرس لو كانت موجودة (لا بأس إن لم توجد)
def _rebuild_index_if_exists():
    try:
        build_index()
    except Exception:
        pass

# ------------------ خرائط المنصات ونصائح توسيع الاستعلام ------------------
PLATFORM_FILTERS = {
    "social": [
        "site:x.com", "site:twitter.com", "site:facebook.com",
        "site:instagram.com", "site:linkedin.com", "site:tiktok.com",
        "site:reddit.com", "site:snapchat.com"
    ],
    "video": [
        "site:youtube.com", "site:vimeo.com", "site:tiktok.com", "site:dailymotion.com"
    ],
    "markets": [
        "site:alibaba.com", "site:amazon.com", "site:aliexpress.com",
        "site:etsy.com", "site:ebay.com", "site:noon.com"
    ],
    "gov": [
        "site:gov", "site:gov.sa", "site:gov.ae", "site:gov.eg",
        "site:edu", "site:edu.sa", "site:edu.eg"
    ],
    "all": []  # بدون فلتر
}

QUERY_EXPANSIONS = {
    "ابحث": ["ابحث عن", "تقصّى", "استخرج معلومات عن"],
    "منصات": ["سوشال ميديا", "تواصل اجتماعي"],
    "سعر": ["ثمن", "تكلفة"],
}

def _expand_query_text(q: str):
    vars_ = {q}
    for k, alts in QUERY_EXPANSIONS.items():
        if k in q:
            for a in alts:
                vars_.add(q.replace(k, a))
    return list(vars_)

# ------------------ بحث عام عبر DuckDuckGo ------------------
def _web_search_basic(q: str, limit: int = 8):
    try:
        with DDGS() as ddgs:
            out = []
            for r in ddgs.text(q, region="xa-ar", safesearch="off", max_results=limit):
                out.append({
                    "title":   r.get("title", ""),
                    "link":    r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
            return out
    except Exception:
        return []

# ------------------ بحث متقدّم (فلترة منصات) ------------------
def _deep_search(q: str, mode: str = "all", per_site: int = 4, max_total: int = 30):
    domains = PLATFORM_FILTERS.get(mode, [])
    # لا فلاتر → بحث عام قوي + إزالة تكرارات + تلخيص
    if not domains:
        hits = []
        for v in _expand_query_text(q):
            hits += _web_search_basic(v, limit=10)
        seen, out = set(), []
        for h in hits:
            link = h.get("link")
            if not link or link in seen:
                continue
            seen.add(link)
            out.append(h)
        for h in out:
            h["summary"] = summarize_text(h.get("snippet", ""), 2)
        return out[:max_total]

    results, seen = [], set()
    try:
        with DDGS() as ddgs:
            for dom in domains:
                query = f"{q} {dom}"
                for r in ddgs.text(query, region="xa-ar", safesearch="off", max_results=per_site):
                    link = r.get("href", "")
                    if not link or link in seen:
                        continue
                    seen.add(link)
                    results.append({
                        "title":   r.get("title", ""),
                        "link":    link,
                        "snippet": r.get("body", ""),
                        "domain":  dom.replace("site:", ""),
                    })
                    if len(results) >= max_total:
                        break
                if len(results) >= max_total:
                    break
    except Exception:
        pass
    for r in results:
        r["summary"] = summarize_text(r.get("snippet", ""), 2)
    return results

# ------------------ تنزيل/تلخيص رابط واحد ------------------
async def _fetch_and_digest(url: str) -> dict:
    """
    - PDF: يُحفَظ في /files/uploads ويُفهرس نصّه (RAG) إن أمكن.
    - HTML: استخراج نص مقروء وتلخيصه.
    - غير ذلك: تنزيل الملف كما هو في /files/uploads.
    """
    headers = {"User-Agent": "Mozilla/5.0 (BassamBot; +https://render.com)"}
    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        content_type = (resp.headers.get("content-type") or "").lower()

        # PDF
        if "application/pdf" in content_type or url.lower().endswith(".pdf"):
            safe = ensure_safe_filename(os.path.basename(urlparse(url).path) or f"doc_{int(time.time())}.pdf")
            dest = os.path.join(UPLOADS_DIR, safe)
            with open(dest, "wb") as f:
                f.write(resp.content)
            txt = extract_pdf_text(dest)
            indexed = False
            if txt.strip():
                txt_name = safe.rsplit(".", 1)[0] + ".txt"
                with open(os.path.join(DATA_DIR, txt_name), "w", encoding="utf-8") as f:
                    f.write(txt)
                _rebuild_index_if_exists()
                indexed = True
            return {"kind": "pdf", "file_url": f"/files/uploads/{safe}", "indexed": indexed}

        # HTML
        text = resp.text or ""
        if "text/html" in content_type or "<html" in text.lower():
            try:
                if Document:
                    doc = Document(text)
                    txt = BeautifulSoup(doc.summary(), "html.parser").get_text(" ", strip=True)
                else:
                    txt = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
            except Exception:
                txt = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
            return {"kind": "html", "summary": summarize_text(txt, 4)}

        # ملف آخر
        safe = ensure_safe_filename(os.path.basename(urlparse(url).path) or f"file_{int(time.time())}")
        dest = os.path.join(UPLOADS_DIR, safe)
        with open(dest, "wb") as f:
            f.write(resp.content)
        return {"kind": "file", "file_url": f"/files/uploads/{safe}"}

# ------------------ المسارات الجديدة ------------------

@app.get("/search")
def search_endpoint(
    q: str = Query(..., description="نص البحث"),
    mode: str = "all",
    per_site: int = 4,
    max_total: int = 30
):
    """
    أمثلة:
      /search?q=اسم+الشخص&mode=social
      /search?q=كاميرا+سوني&mode=markets
      /search?q=قانون+مرور&mode=gov
      /search?q=شرح+مشكلة+جوال&mode=video
    """
    q = (q or "").strip()
    if not q:
        return {"type": "search", "results": []}
    results = _deep_search(q, mode=mode, per_site=per_site, max_total=max_total)
    if results:
        return {"type": "chat", "answer": "أفضل النتائج 👇", "sources": results}
    return {"type": "chat", "answer": "لم أجد نتائج واضحة، جرّب وصفًا أدق."}

@app.post("/fetch_url")
async def fetch_url(payload: dict = Body(...)):
    """
    تنزيل رابط (HTML/PDF/ملف) ثم تلخيصه/فهرسته.
    JSON: {"url": "https://..."}
    """
    url = (payload.get("url") or "").strip()
    if not url:
        raise HTTPException(400, "الرجاء تمرير url")
    try:
        info = await _fetch_and_digest(url)
        return {"ok": True, **info}
    except Exception as e:
        return {"ok": False, "error": str(e)}
# ======================= نهاية القسم الإضافي =======================
