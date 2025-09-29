# main.py — بسّام v4.1 (عربي/فَزّي + بحث متقدّم + سوشال + رفع PDF + RAG + ويكي + رياضيات)
from fastapi import FastAPI, Request, Query, Body, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

import os, json, time, re, unicodedata, uuid
from typing import List, Dict, Any

# نص/ويب
from duckduckgo_search import DDGS
try:
    from sumy.parsers.text import PlaintextParser
except Exception:
    from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer
import wikipedia

# رياضيات
from sympy import symbols, sympify, diff, integrate, simplify

# RAG
from rank_bm25 import BM25Okapi

# فَزّي
from rapidfuzz.fuzz import partial_ratio

# PDF
from pdfminer.high_level import extract_text as pdf_extract_text

APP_VER = "4.1"

DATA_DIR     = "data"
NOTES_DIR    = os.path.join(DATA_DIR, "notes")
UPLOADS_DIR  = os.path.join(DATA_DIR, "uploads")
DERIVED_DIR  = os.path.join(DATA_DIR, "derived")
LEARN_PATH   = os.path.join(NOTES_DIR, "learned.jsonl")
USAGE_PATH   = os.path.join(DATA_DIR, "usage_stats.json")

# كلمة مرور "الوضع الموسّع" (بحث أعمق ضمن الويب العام فقط)
PROTECTED_PASS = "093589"

app = FastAPI(title="بسّام الذكي 🤖", version=APP_VER)

# Static/Templates
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
except Exception:
    templates = None

# مجلد data متاح للتنزيل/المعاينة
app.mount("/files", StaticFiles(directory=DATA_DIR), name="files")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ===== تجهيز المجلدات =====
def _ensure_dirs():
    for p in [DATA_DIR, NOTES_DIR, UPLOADS_DIR, DERIVED_DIR]:
        os.makedirs(p, exist_ok=True)
    if not os.path.exists(LEARN_PATH):
        open(LEARN_PATH, "a", encoding="utf-8").close()
    if not os.path.exists(USAGE_PATH):
        with open(USAGE_PATH, "w", encoding="utf-8") as f:
            json.dump({"requests": 0, "last_time": int(time.time())}, f)
_ensure_dirs()

# ===== تطبيع عربي + فَزّي =====
AR_DIAC = re.compile(r"[\u0610-\u061A\u064B-\u065F\u06D6-\u06ED]")
def normalize_ar(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFKC", s)
    s = AR_DIAC.sub("", s)
    s = s.replace("أ","ا").replace("إ","ا").replace("آ","ا")
    s = s.replace("ى","ي").replace("ة","ه").replace("ؤ","و").replace("ئ","ي")
    s = s.replace("٠","0").replace("١","1").replace("٢","2").replace("٣","3").replace("٤","4")
    s = s.replace("٥","5").replace("٦","6").replace("٧","7").replace("٨","8").replace("٩","9")
    s = re.sub(r"\s+"," ", s)
    return s.strip().lower()

def is_like(text: str, keywords: List[str], threshold: int = 80) -> bool:
    t = normalize_ar(text)
    return any(partial_ratio(t, normalize_ar(k)) >= threshold for k in keywords)

# ===== تلخيص =====
def summarize_text(text: str, max_sentences: int = 3) -> str:
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("arabic"))
        summ = TextRankSummarizer()
        sents = summ(parser.document, max_sentences)
        return " ".join(str(s) for s in sents) if sents else text[:400]
    except Exception:
        return text[:400]

# ===== بحث متقدّم (DuckDuckGo) + سوشال =====
SOCIAL_SITES = {
    "تويتر": ["x.com", "twitter.com"], "x": ["x.com","twitter.com"],
    "انستقرام": ["instagram.com"], "انستغرام": ["instagram.com"], "instagram": ["instagram.com"],
    "فيسبوك": ["facebook.com"], "facebook": ["facebook.com"],
    "يوتيوب": ["youtube.com"], "youtube": ["youtube.com"],
    "لينكدان": ["linkedin.com"], "لينكدإن": ["linkedin.com"], "linkedin": ["linkedin.com"],
    "تيك توك": ["tiktok.com"], "tiktok": ["tiktok.com"],
    "رديت": ["reddit.com"], "reddit": ["reddit.com"],
    "تلغرام": ["t.me","telegram.me","telegram.org"],
    "سناب": ["snapchat.com"], "snapchat": ["snapchat.com"],
    "تانجو": ["tango.me","tango.me/en"],  # تغطية تقريبية
}

INTENT_SEARCH = ["ابحث", "بحث", "دور", "استعلم", "فتش", "search", "look up", "find", "google"]
GOV_HINTS = ["حكومي", "وزارة", "gov", "government"]
EDU_HINTS = ["تعليمي", "جامعة", "مدرسه", "edu", "education"]

def ddg_search(query: str, site_domains: List[str] = None, max_results: int = 8, exact_phrases: List[str] = None):
    q = query.strip()
    if exact_phrases:
        for ph in exact_phrases:
            ph = ph.strip()
            if ph:
                q += f' "{ph}"'
    if site_domains:
        site_filter = " OR ".join([f"site:{d}" for d in site_domains])
        q = f"({q}) ({site_filter})"
    try:
        with DDGS() as ddgs:
            res = ddgs.text(q, region="xa-ar", max_results=max_results)
            out = [{"title": r.get("title",""), "link": r.get("href",""), "snippet": r.get("body","")} for r in res]
            # إزالة التكرار
            seen, uniq = set(), []
            for it in out:
                if it["link"] in seen: continue
                seen.add(it["link"]); uniq.append(it)
            return uniq[:max_results]
    except Exception:
        return []

def smart_search_router(q: str, deep: bool = False):
    """
    deep=True عند تفعيل كلمة السر: يزيد النتائج + يضيف عبارات مقتبسة لرفع الدقة.
    (ما يزال ضمن الويب العام فقط.)
    """
    qn = normalize_ar(q)
    if qn.startswith("ابحث") or is_like(qn, INTENT_SEARCH, 82):
        chosen = []
        for key, domains in SOCIAL_SITES.items():
            if key in qn or key in q.lower():
                chosen += domains
        if any(h in qn for h in GOV_HINTS):
            chosen.append(".gov")
        if any(h in qn for h in EDU_HINTS):
            chosen.append(".edu")
        # وضع موسّع: نتائج أكثر + اقتباس الاسم بين ""
        maxr = 12 if deep else 8
        phrases = []
        # التقط الاسم بعد كلمة "عن"
        m = re.search(r"عن\s+(.+)", q)
        if m:
            phrases = [m.group(1).strip()]
        results = ddg_search(q, chosen or None, max_results=maxr, exact_phrases=phrases if deep else None)
        for item in results:
            item["summary"] = summarize_text(item.get("snippet",""), 2)
        return {"type": "search", "query": q, "domains": chosen, "results": results}
    return None

# بحث اسم عبر منصّات السوشال (تجميع سريع بالـ site:)
def social_name_search(name: str, deep: bool = False):
    domains = []
    for dlist in SOCIAL_SITES.values():
        domains += dlist
    maxr = 15 if deep else 8
    res = ddg_search(name, domains, max_results=maxr, exact_phrases=[name] if deep else None)
    for item in res:
        item["summary"] = summarize_text(item.get("snippet",""), 2)
    return {"type":"search","query":name,"domains":domains,"results":res}

# ===== ويكيبيديا: تعريفات + عواصم =====
def wiki_define(term: str):
    term = (term or "").strip()
    for lang in ["ar", "en"]:
        try:
            wikipedia.set_lang(lang)
            page = wikipedia.page(term, auto_suggest=True, redirect=True)
            return {"lang": lang, "term": term, "summary": page.summary[:800], "source": page.url}
        except Exception:
            continue
    return None

CAPITAL_PATTERNS = [
    r"^ما ?هي?\s+عاصمة\s+(.+)$",
    r"^عاصمة\s+(.+)$",
    r"^what\s+is\s+the\s+capital\s+of\s+(.+)\??$",
]
def detect_capital_query(q: str):
    qq = q.strip().lower()
    for pat in CAPITAL_PATTERNS:
        m = re.match(pat, qq, flags=re.IGNORECASE)
        if m: return m.group(1).strip(" ؟؟!.:،")
    return None

def wiki_capital(country: str):
    for lang in ["ar", "en"]:
        try:
            wikipedia.set_lang(lang)
            page = wikipedia.page(country, auto_suggest=True, redirect=True)
            summary = page.summary[:1200]
            src = page.url
            if lang == "ar":
                m = re.search(r"(?:عاصمتها|العاصمة(?:\s*هي)?)\s+([^\.\،\n]+)", summary)
                if m: return {"country": country, "capital": m.group(1).strip(), "source": src, "summary": summary}
            else:
                m = re.search(r"capital(?:\s+is|:)?\s+([^\.\,\n]+)", summary, flags=re.I)
                if m: return {"country": country, "capital": m.group(1).strip(), "source": src, "summary": summary}
        except Exception:
            continue
    return None

# ===== RAG (BM25) + قراءة ملفاتك (PDF استخراج) =====
def _tokenize_ar(s: str) -> List[str]:
    return re.findall(r"[\w\u0600-\u06FF]+", s.lower())

def _read_documents() -> List[Dict[str, str]]:
    docs = []
    for root, _, files in os.walk(DATA_DIR):
        for fn in files:
            path = os.path.join(root, fn)
            try:
                if fn.endswith(".txt") or fn.endswith(".md"):
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        docs.append({"file": path, "text": f.read()})
                elif fn.endswith(".pdf"):
                    derived_txt = os.path.join(DERIVED_DIR, fn + ".txt")
                    if not os.path.exists(derived_txt) or os.path.getmtime(derived_txt) < os.path.getmtime(path):
                        try:
                            txt = pdf_extract_text(path) or ""
                            with open(derived_txt, "w", encoding="utf-8") as out:
                                out.write(txt)
                        except Exception:
                            pass
                    if os.path.exists(derived_txt):
                        with open(derived_txt, "r", encoding="utf-8", errors="ignore") as f:
                            docs.append({"file": derived_txt, "text": f.read()})
            except:
                pass
    # بنك التعلم الذاتي
    try:
        with open(LEARN_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                obj = json.loads(line)
                text = f"س: {obj.get('question','')}\nج: {obj.get('answer','')}\nوسوم:{','.join(obj.get('tags',[]))}"
                docs.append({"file": "learned", "text": text})
    except:
        pass
    return docs

BM25_INDEX = None
BM25_CORPUS = []
BM25_DOCS: List[Dict[str, str]] = []
def build_index():
    global BM25_INDEX, BM25_CORPUS, BM25_DOCS
    BM25_DOCS = _read_documents()
    BM25_CORPUS = [_tokenize_ar(d["text"]) for d in BM25_DOCS]
    BM25_INDEX = BM25Okapi(BM25_CORPUS) if BM25_CORPUS else None
    return len(BM25_DOCS)
build_index()

def rag_bm25(query: str, k: int = 3):
    if not BM25_INDEX: return []
    toks = _tokenize_ar(query)
    scores = BM25_INDEX.get_scores(toks)
    pairs = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:k]
    results = []
    for idx, sc in pairs:
        if sc < 1.0: continue
        doc = BM25_DOCS[idx]
        results.append({"file": doc["file"], "score": float(sc), "snippet": doc["text"][:800]})
    return results

# ===== رياضيات =====
def solve_math(expr: str):
    try:
        x = symbols('x')
        parsed = sympify(expr)
        return {
            "input": str(parsed),
            "simplified": str(simplify(parsed)),
            "derivative": str(diff(parsed, x)),
            "integral": str(integrate(parsed, x)),
        }
    except Exception as e:
        return {"error": f"تعذر تحليل المعادلة: {e}"}

# ===== سجلات/تعلم + أسلوب مرح =====
FUN_LINES = [
    "على راسي يا فهيم! 🤓",
    "أها! الدماغ بدأ يسخّن 🔥",
    "خلّني ألبس نظارة العبقرية 🤓✨",
    "يا سلام على السؤال! 🚀",
]
def fun_wrap(text: str, mood: str) -> str:
    if mood == "plain":  # بدون مزاح
        return text
    add = FUN_LINES[int(time.time()) % len(FUN_LINES)]
    return f"{add}\n\n{text}"

def log_usage():
    try:
        with open(USAGE_PATH, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["requests"] = int(data.get("requests", 0)) + 1
            data["last_time"] = int(time.time())
            f.seek(0); json.dump(data, f); f.truncate()
    except Exception:
        pass

def save_feedback(question: str, answer: str, tags: List[str]):
    record = {"time": int(time.time()), "question": question.strip(), "answer": answer.strip(), "tags": tags or []}
    with open(LEARN_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

# ===== صفحات =====
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if templates and os.path.exists("templates/index.html"):
        return templates.TemplateResponse("index.html", {"request": request, "version": APP_VER})
    html = """<!doctype html><meta charset='utf-8'><title>Bassam</title>
    <h3>بسّام v4.1</h3><p>الواجهة غير موجودة. ارفع templates/index.html</p>"""
    return HTMLResponse(html)

@app.get("/chatui")
def chat_alias():
    return RedirectResponse("/")

@app.get("/healthz")
def healthz():
    return {"status":"ok","version":APP_VER,"docs_indexed":len(BM25_DOCS)}

# ===== رفع ملفات + فهرسة =====
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    fn = file.filename or f"file-{uuid.uuid4().hex}"
    safe = re.sub(r"[^A-Za-z0-9_.\\-]+","_", fn)
    path = os.path.join(UPLOADS_DIR, safe)
    with open(path, "wb") as f:
        f.write(await file.read())

    if safe.lower().endswith(".pdf"):
        try:
            txt = pdf_extract_text(path) or ""
            out = os.path.join(DERIVED_DIR, safe + ".txt")
            with open(out, "w", encoding="utf-8") as o:
                o.write(txt)
        except Exception:
            pass

    n = build_index()
    return {"ok": True, "saved": f"/files/uploads/{safe}", "indexed_docs": n}

@app.get("/list-files")
def list_files():
    out = []
    for root, _, files in os.walk(DATA_DIR):
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), DATA_DIR)
            out.append(f"/files/{rel.replace('\\', '/')}")
    return {"files": sorted(out)}

# ===== منطق الإجابة =====
GREET = ["مرحبا","السلام عليكم","اهلا","كيف الحال","هاي","hello","hi"]

@app.get("/ask")
def ask(
    q: str = Query(..., description="سؤالك"),
    mood: str = Query("fun", description="fun|plain"),
    pwd: str = Query("", description="كلمة سر الوضع الموسّع (اختياري)")
):
    """
    pwd == PROTECTED_PASS => يفعّل وضع موسّع (نتائج/فلاتر أكثر) لكن ضمن الويب العام فقط.
    لن نصل لمحتوى محظور أو غير قانوني.
    """
    log_usage()
    q = (q or "").strip()
    if not q:
        return {"type":"none","answer":"اكتب سؤالك لو سمحت 😊"}

    deep = (pwd == PROTECTED_PASS)
    qn = normalize_ar(q)

    # 0) تحية
    if is_like(qn, GREET, 80):
        msg = fun_wrap("أهلًا بصاحبي! أنا بسّام 😊 اسألني عن رياضيات، تعريفات، البحث في الويب، أو من ملفاتك…", mood)
        return {"type":"greet","answer":msg}

    # 1) بحث متقدّم (منصّات/حكومي/تعليمي)
    smart = smart_search_router(q, deep=deep)
    if smart:
        tops = "\n\n".join([f"• {w['title']}\n{w['link']}\n{w.get('summary','')}" for w in smart.get("results",[])])
        ans = f"نتائج بحث{(' (مفلتر: ' + ', '.join(smart['domains']) + ')' ) if smart.get('domains') else ''}:\n{tops or '—'}"
        smart["answer"] = fun_wrap(ans, mood)
        return smart

    # 2) بحث أسماء داخل السوشال (لو السؤال كلمة اسم فقط)
    if len(q.split()) <= 3 and any(s in qn for s in ["حساب","اسم","يوزر","username","profile"]):
        soc = social_name_search(q.replace("حساب","").replace("اسم","").replace("يوزر","").strip(), deep=deep)
        tops = "\n\n".join([f"• {w['title']}\n{w['link']}\n{w.get('summary','')}" for w in soc.get("results",[])])
        soc["answer"] = fun_wrap("ترشيحات ملفات/نتائج عامة (روابط علنية فقط):\n"+(tops or "—"), mood)
        return soc

    # 3) رياضيات
    if any(tok in q for tok in ["sin","cos","tan","log","exp","^","+","-","*","/"]) or is_like(qn, ["مشتقه","تكامل","حل معادله"], 70):
        res = solve_math(q)
        ans = "حدث خطأ في تحليل المعادلة." if "error" in res else (
            f"المعادلة: {res['input']}\nتبسيط: {res['simplified']}\nالمشتقة: {res['derivative']}\nالتكامل: {res['integral']}"
        )
        return {"type":"math","result":res,"answer": fun_wrap(ans, mood)}

    # 4) عواصم
    country = detect_capital_query(q)
    if country:
        cap = wiki_capital(country)
        if cap:
            ans = f"عاصمة {country}: {cap['capital']}"
            return {"type":"fact","kind":"capital","query_country":country,"answer": fun_wrap(ans, mood),"source":cap["source"],"summary":cap["summary"][:400]}

    # 5) تعريفات (ويكي)
    if len(q.split()) == 1 or is_like(qn, ["عرف","تعريف","ماهو","ما هي","explain","definition","what is"], 75):
        d = wiki_define(q)
        if d:
            ans = d["summary"]
            return {"type":"definition","term":q,"answer": fun_wrap(ans, mood),"source":d["source"]}

    # 6) RAG من ملفاتك
    rag = rag_bm25(q, k=3)
    if rag:
        s = summarize_text(rag[0]["snippet"], 3)
        srcs = "\n".join([f"- {os.path.basename(h['file'])} (score={h['score']:.2f})" for h in rag])
        ans = f"ملخص من ملفاتك:\n{s}\n\nمصادر:\n{srcs}"
        return {"type":"rag","hits":rag,"summary":s,"answer": fun_wrap(ans, mood)}

    # 7) بحث ويب عام
    web = ddg_search(q, None, max_results=(12 if deep else 8))
    if web:
        for item in web:
            item["summary"] = summarize_text(item.get("snippet",""), 2)
        tops = "\n\n".join([f"• {w['title']}\n{w['link']}\n{w.get('summary','')}" for w in web])
        return {"type":"web","results":web,"answer": fun_wrap("نتيجة بحث سريعة:\n"+tops, mood)}

    # 8) غموض
    return {"type":"none","answer": fun_wrap("تمام يا بطل! ما لقيت إجابة دقيقة الآن. أعطني كلمة مفتاحية أكثر أو مثال، وأنا حاضر 👀", mood)}

# تعلم ذاتي
@app.post("/feedback")
def feedback(payload: Dict[str, Any] = Body(...)):
    q = (payload.get("question") or "").strip()
    a = (payload.get("answer") or "").strip()
    tags = payload.get("tags") or []
    if not q or not a:
        return {"ok": False, "error": "question و answer مطلوبة"}
    save_feedback(q, a, tags)
    n = build_index()
    return {"ok": True, "indexed_docs": n}

# إعادة فهرسة
@app.post("/train")
def train():
    n = build_index()
    return {"ok": True, "indexed_docs": n}

# إحصاءات
@app.get("/stats")
def stats():
    try:
        with open(USAGE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"requests": 0}

# تشغيل محلي
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
