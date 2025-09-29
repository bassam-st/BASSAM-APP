# main.py — Bassam الذكي v4.2
from fastapi import FastAPI, UploadFile
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os, re, json, difflib
from typing import List, Dict
from duckduckgo_search import DDGS
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer
from sympy import sympify, diff, integrate, simplify

app = FastAPI(title="بسام الذكي 🤖", version="4.2")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

os.makedirs("data/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# -------------------- أدوات مساعدة --------------------
def clean_text(t: str) -> str:
    t = re.sub(r"[^\w\u0600-\u06FF\s\-]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def summarize_text(text: str, max_sent: int = 3) -> str:
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("arabic"))
        summ = TextRankSummarizer()
        sents = summ(parser.document, max_sent)
        return " ".join(str(s) for s in sents) or text[:400]
    except:
        return text[:400]

def correct(word: str, vocab: List[str]) -> str:
    if word in vocab: return word
    m = difflib.get_close_matches(word, vocab, n=1, cutoff=0.6)
    return m[0] if m else word

def web_search(query: str, limit: int = 6):
    with DDGS() as ddgs:
        return list(ddgs.text(query, region="xa-ar", safesearch="off", max_results=limit))

# -------------------- نوايا/قواميس --------------------
COUNTRIES = {
    "اليمن": "صنعاء","السعودية":"الرياض","مصر":"القاهرة","الإمارات":"أبوظبي","قطر":"الدوحة",
    "عمان":"مسقط","الكويت":"الكويت","البحرين":"المنامة","ألمانيا":"برلين","فرنسا":"باريس",
    "تركيا":"أنقرة","اليابان":"طوكيو","الصين":"بكين","الهند":"نيودلهي","أمريكا":"واشنطن"
}
COUNTRY_WORDS = list(COUNTRIES.keys())

SOCIAL_MAP: Dict[str, List[str]] = {
    "تويتر": ["site:x.com","site:twitter.com"],
    "اكس": ["site:x.com","site:twitter.com"],
    "يوتيوب": ["site:youtube.com"],
    "فيسبوك": ["site:facebook.com"],
    "انستجرام": ["site:instagram.com"],
    "لينكدإن": ["site:linkedin.com","site:linkedin.cn"],
    "تيك توك": ["site:tiktok.com"],
    "سناب شات": ["site:snapchat.com"],
}

MARKET_MAP: Dict[str, List[str]] = {
    "علي بابا": ["site:alibaba.com","site:1688.com","site:aliexpress.com"],
    "أمازون": ["site:amazon.com","site:amazon.ae","site:amazon.sa","site:amazon.de"],
    "إيباي": ["site:ebay.com"],
    "نون": ["site:noon.com"],
    "علي اكسبريس": ["site:aliexpress.com"],
    "تمّ": ["site:temu.com"], "تمو": ["site:temu.com"], "temu": ["site:temu.com"],
    "سوق": ["site:souq.com","site:amazon.ae","site:amazon.sa"],
}

def detect_intent(q: str):
    lq = q.lower()
    if any(w in lq for w in ["عاصمة","عاصمه","capital","بلد","دولة"]): return "country"
    if any(w in lq for w in ["تكامل","مشتقة","تفاضل","معادلة","derivative","integral"]): return "math"
    if any(w in lq for w in ["ابحث في","بحث في","فتش في","دور في"]) and any(key in lq for key in (*SOCIAL_MAP.keys(), *MARKET_MAP.keys(), "الأسواق","الاسواق","سوق")):
        return "platform"
    if any(w in lq for w in ["فسّر","اشرح","وضح","ما هو","ماهي","ما معنى"]): return "explain"
    return "search"

# -------------------- رياضيات --------------------
def solve_math(expr: str):
    try:
        e = sympify(expr)
        return {
            "input": str(e),
            "simplify": str(simplify(e)),
            "diff": str(diff(e)),
            "integrate": str(integrate(e))
        }
    except Exception as ex:
        return {"error": f"تعذر تحليل المعادلة: {ex}"}

# -------------------- واجهات --------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!doctype html><meta charset="utf-8"><title>بسام الذكي v4.2</title>
    <style>body{background:#0b1020;color:#e7ecff;font-family:system-ui;max-width:900px;margin:40px auto}
    input,button{padding:12px;border-radius:10px;border:1px solid #223066;background:#0f1a38;color:#fff}</style>
    <h2>🤖 بسّام الذكي v4.2</h2>
    <p>اكتب مثلاً: <code>ابحث في علي بابا عن مضخة ماء ستانلس 2 بوصة</code> — أو — <code>ما عاصمة تركيا؟</code></p>
    <form action="/ask" method="get"><input name="q" style="width:70%"><button>إرسال</button></form>
    """

@app.get("/healthz")
def healthz():
    return {"status":"ok","version":"4.2"}

@app.post("/upload")
async def upload_file(file: UploadFile):
    path = f"data/uploads/{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())
    return {"ok": True, "path": path}

@app.get("/download")
def download_file(name: str):
    path = f"data/uploads/{name}"
    if not os.path.exists(path): return {"error":"الملف غير موجود"}
    return FileResponse(path)

@app.get("/platforms")
def platforms():
    return {"social": list(SOCIAL_MAP.keys()), "markets": list(MARKET_MAP.keys())}

@app.get("/ask")
def ask(q: str):
    q = clean_text(q)
    intent = detect_intent(q)

    # 1) دول/عواصم
    if intent == "country":
        for name, cap in COUNTRIES.items():
            if name in q or correct(name, COUNTRY_WORDS) in q:
                return {"type":"country","country":name,"capital":cap}
        return {"type":"country","message":"اذكر اسم الدولة بوضوح (مثال: ما عاصمة ألمانيا؟)"}

    # 2) رياضيات
    if intent == "math":
        return {"type":"math","result": solve_math(q)}

    # 3) بحث منصات (سوشيال + أسواق)
    if intent == "platform":
        domains: List[str] = []
        # منصات اجتماعية
        for key, doms in SOCIAL_MAP.items():
            if key.lower() in q.lower(): domains += doms
        # أسواق إلكترونية
        market_hit = False
        for key, doms in MARKET_MAP.items():
            if key.lower() in q.lower():
                domains += doms
                market_hit = True
        # كلمة عامة "الأسواق"
        if ("الأسواق" in q or "الاسواق" in q or "سوق" in q) and not market_hit:
            # ابحث في مجموعة أسواق واسعة
            for doms in MARKET_MAP.values(): domains += doms

        # اصنع عبارة بحث مدمجة
        # مثال: "مضخة ماء ستانلس 2 بوصة" + site:alibaba.com OR site:amazon.com ...
        base_query = re.sub(r"(ابحث|بحث|فتش|دور)\s+في\s+.*?\s+عن\s+", "", q, flags=re.IGNORECASE)
        base_query = re.sub(r"(ابحث|بحث|فتش|دور)\s+عن\s+", "", base_query, flags=re.IGNORECASE)
        site_filter = " OR ".join(domains) if domains else ""
        full_query = f"{base_query} {site_filter}".strip()

        hits = web_search(full_query, limit=10)
        results = []
        for r in hits:
            results.append({
                "title": r.get("title",""),
                "link": r.get("href",""),
                "snippet": r.get("body",""),
                "summary": summarize_text(r.get("body",""))
            })
        return {
            "type":"platform",
            "query": full_query,
            "platforms": [d.replace("site:","") for d in domains],
            "results": results
        }

    # 4) بحث ويب عام
    hits = web_search(q, limit=6)
    if hits:
        for h in hits:
            h["summary"] = summarize_text(h.get("body",""))
        return {"type":"web","results": hits}

    # 5) رد افتراضي لطيف
    return {
        "type":"none","emotion":"neutral",
        "message":"تمام! أنا بسّام 😊. لم أجد نتيجة واضحة الآن. جرّب إعادة الصياغة أو حدد المنصة (مثال: ابحث في علي بابا عن ...)."
    }

if __name__ == "__main__":
    import uvicorn, os
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
