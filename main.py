# === إضــــافات أعلى الملف ===
import httpx
from urllib.parse import urlparse

# خرائط المنصّات (تستعمل site: لتوجيه محرك البحث)
PLATFORM_FILTERS = {
    "social": [
        "site:x.com", "site:twitter.com", "site:facebook.com", "site:instagram.com",
        "site:linkedin.com", "site:tiktok.com", "site:reddit.com", "site:snapchat.com"
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
    "all": []  # بدون فلاتر خاصة
}

# توسيع السؤال بمرادفات بسيطة (تقدر توسّعها لاحقًا)
QUERY_EXPANSIONS = {
    "ابحث": ["ابحث عن", "تقصّى", "استخرج معلومات عن"],
    "منصات": ["سوشال ميديا", "تواصل اجتماعي"],
    "سعر": ["ثمن", "تكلفة"]
}

def expand_query_text(q: str) -> list[str]:
    vars = {q}
    for k, alts in QUERY_EXPANSIONS.items():
        if k in q:
            for a in alts:
                vars.add(q.replace(k, a))
    return list(vars)

def web_search_basic(q: str, limit: int = 8):
    """بحث عام عبر DuckDuckGo (نظيف ومباشر)."""
    try:
        with DDGS() as ddgs:
            out = []
            for r in ddgs.text(q, region="xa-ar", safesearch="off", max_results=limit):
                out.append({
                    "title": r.get("title", ""),
                    "link":  r.get("href",  ""),
                    "snippet": r.get("body", "")
                })
            return out
    except Exception:
        return []

def deep_search(q: str, mode: str = "all", per_site: int = 4, max_total: int = 30):
    """
    بحث متقدّم: يلف على مجموعة مواقع محددة (بواسطة site:) ويجمع نتائج كثيرة.
    mode ∈ {'all','social','video','markets','gov'}
    """
    domains = PLATFORM_FILTERS.get(mode, [])
    # لو ما في فلاتر، نعمل بحث عام قوي
    if not domains:
        hits = []
        for v in expand_query_text(q):
            hits += web_search_basic(v, limit=10)
        # أزل التكرارات
        seen, out = set(), []
        for h in hits:
            link = h.get("link")
            if not link or link in seen: 
                continue
            seen.add(link)
            out.append(h)
        # القصّ ولخّص
        for h in out:
            h["summary"] = summarize_text(h.get("snippet", ""), 2)
        return out[:max_total]

    # مع فلاتر منصّات
    results, seen = [], set()
    try:
        with DDGS() as ddgs:
            for dom in domains:
                query = f'{q} {dom}'
                for r in ddgs.text(query, region="xa-ar", safesearch="off", max_results=per_site):
                    link = r.get("href", "")
                    if not link or link in seen:
                        continue
                    seen.add(link)
                    results.append({
                        "title": r.get("title", ""),
                        "link":  link,
                        "snippet": r.get("body", ""),
                        "domain": dom.replace("site:", "")
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

async def fetch_and_digest(url: str) -> dict:
    """
    تنزيل URL بأمان:
      - لو PDF: نحفظه في /files/uploads وندخّله فهرس RAG
      - لو HTML: نلخّص المحتوى المقروء
    """
    headers = {"User-Agent": "Mozilla/5.0 (BassamBot; +https://render.com)"}
    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(url)
        ct = (resp.headers.get("content-type") or "").lower()

        # PDF؟
        if "application/pdf" in ct or url.lower().endswith(".pdf"):
            safe = ensure_safe_filename(os.path.basename(urlparse(url).path) or f"doc_{int(time.time())}.pdf")
            dest = os.path.join(UPLOADS_DIR, safe)
            with open(dest, "wb") as f:
                f.write(resp.content)
            txt = extract_pdf_text(dest)
            if txt.strip():
                txt_name = safe.rsplit(".", 1)[0] + ".txt"
                with open(os.path.join(DATA_DIR, txt_name), "w", encoding="utf-8") as f:
                    f.write(txt)
                build_index()
            return {"kind": "pdf", "file_url": f"/files/uploads/{safe}", "indexed": bool(txt.strip())}

        # HTML؟
        if "text/html" in ct or "<html" in resp.text.lower():
            html = resp.text
            # readability → نص قابل للتلخيص
            try:
                doc = Document(html)
                txt = BeautifulSoup(doc.summary(), "html.parser").get_text(" ", strip=True)
            except Exception:
                txt = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
            return {"kind": "html", "summary": summarize_text(txt, 4)}

        # نوع آخر (ننزّله كما هو فقط)
        safe = ensure_safe_filename(os.path.basename(urlparse(url).path) or f"file_{int(time.time())}")
        dest = os.path.join(UPLOADS_DIR, safe)
        with open(dest, "wb") as f:
            f.write(resp.content)
        return {"kind": "file", "file_url": f"/files/uploads/{safe}"}

# ====== مسارات (Endpoints) ======

@app.get("/search")
def search_endpoint(q: str = Query(..., description="نص البحث"), mode: str = "all",
                    per_site: int = 4, max_total: int = 30):
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
    results = deep_search(q, mode=mode, per_site=per_site, max_total=max_total)
    # رد موحّد (نفس شكل فقاعة بسّام)
    if results:
        return {"type": "chat", "answer": "أفضل النتائج 👇", "sources": results}
    return {"type": "chat", "answer": "لم أجد نتائج واضحة، جرّب وصفًا أدق."}

@app.post("/fetch_url")
async def fetch_url(payload: Dict[str, Any] = Body(...)):
    """
    تنزيل رابط (HTML/PDF/ملف) وتلخيصه أو فهرسته.
    JSON: {"url": "https://..."}
    """
    url = (payload.get("url") or "").strip()
    if not url:
        raise HTTPException(400, "الرجاء تمرير url")
    try:
        info = await fetch_and_digest(url)
        return {"ok": True, **info}
    except Exception as e:
        return {"ok": False, "error": str(e)}
