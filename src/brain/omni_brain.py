# src/brain/omni_brain.py
# Omni Brain v3 — أدوات محلية + RAG + ويب + Gemini(اختياري) + ذاكرة

import os, re
from typing import List, Dict, Optional
from dateutil import parser as dateparser

import httpx
from bs4 import BeautifulSoup
from readability import Document
from duckduckgo_search import DDGS
from diskcache import Cache
from wikipedia import summary as wiki_summary

from sympy import sympify, diff, integrate

# ✅ Sumy (الاستدعاء الصحيح)
from sumy.parsers.text import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

# ✅ ذاكرة المستخدم (بسيطة)
from src.memory.memory import remember, recall

# ✅ RAG (اختياري — يعمل لو الفهرس متوفر)
try:
    import faiss
    from sentence_transformers import SentenceTransformer
    from src.rag.indexer import is_ready as rag_cache_ready
    from src.rag.retriever import query_index as rag_file_query
    RAG_MODEL_NAME = os.getenv("RAG_EMB_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    RAG_EMB = SentenceTransformer(RAG_MODEL_NAME)
except Exception:
    faiss = None
    SentenceTransformer = None
    RAG_EMB = None
    def rag_cache_ready(): return False
    def rag_file_query(q, top_k=4): return []

# ===== إعدادات عامة =====
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
cache = Cache(".cache")

# Gemini (اختياري)
USE_GEMINI = bool(os.getenv("GEMINI_API_KEY"))
if USE_GEMINI:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    GEMINI = genai.GenerativeModel("gemini-1.5-flash")
else:
    GEMINI = None

# ===== أدوات مساعدة =====
def AR(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def summarize_text(text: str, max_sentences: int = 5) -> str:
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("arabic"))
        summ = TextRankSummarizer()
        sents = summ(parser.document, max_sentences)
        return " ".join(str(s) for s in sents)
    except Exception:
        return (text or "")[:700]

# ===== ويب =====
def ddg_text(q: str, n: int = 5) -> List[Dict]:
    with DDGS() as ddgs:
        return list(ddgs.text(q, region="xa-ar", safesearch="moderate", max_results=n) or [])

def fetch_clean(url: str, timeout: int = 12) -> str:
    try:
        r = httpx.get(url, headers=UA, timeout=timeout, follow_redirects=True)
        r.raise_for_status()
        doc = Document(r.text)
        html_clean = doc.summary()
        text = BeautifulSoup(html_clean, "lxml").get_text("\n", strip=True)
        return text[:8000]
    except Exception:
        return ""

# ===== أدوات محلية (رياضيات/وحدات/تواريخ) =====
MATH_PAT = re.compile(r"[=+\-*/^()]|sin|cos|tan|log|sqrt|∫|dx|dy|d/dx|مشتقة|تكامل", re.I)
CURRENCY = {"USD":1.0, "EUR":0.92, "SAR":3.75, "AED":3.67, "YER":250.0}

def answer_math(q: str) -> Optional[str]:
    if not MATH_PAT.search(q): return None
    try:
        expr = sympify(q.replace("^", "**"))
        return f"الناتج التقريبي: {expr.evalf()}"
    except Exception:
        if q.strip().startswith("مشتقة "):
            t = q.split("مشتقة ",1)[1]
            try: return f"مشتقة {t} = {diff(sympify(t))}"
            except: return "لم أفهم التعبير للمشتقة."
        if q.strip().startswith("تكامل "):
            t = q.split("تكامل ",1)[1]
            try: return f"تكامل {t} = {integrate(sympify(t))}"
            except: return "لم أفهم التعبير للتكامل."
        return None

def answer_units_dates(q: str) -> Optional[str]:
    m = re.search(r"(\d+[\.,]?\d*)\s*(USD|EUR|SAR|AED|YER)\s*(?:->|الى|إلى|to)\s*(USD|EUR|SAR|AED|YER)", q, re.I)
    if m:
        amount = float(m.group(1).replace(",", "."))
        src, dst = m.group(2).upper(), m.group(3).upper()
        usd = amount / CURRENCY[src]; out = usd * CURRENCY[dst]
        return f"تقريبًا: {amount} {src} ≈ {round(out,2)} {dst}"
    m2 = re.search(r"(\d+)\s*(يوم|أيام|day|days)\s*(?:بعد|later|from)\s*([0-9\-/: ]+)", q, re.I)
    if m2:
        n = int(m2.group(1)); base = dateparser.parse(m2.group(3))
        if base:
            from datetime import timedelta
            return (base + timedelta(days=n)).strftime("%Y-%m-%d %H:%M")
    return None

# ===== ويكيبيديا قصيرة =====
def answer_wikipedia(q: str) -> Optional[str]:
    m = re.search(r"^(من هو|من هي|ما هي|ماهو|ماهي)\s+(.+)$", q.strip(), re.I)
    topic = m.group(2) if m else (q if len(q.split())<=6 else None)
    if not topic: return None
    try:
        s = wiki_summary(topic, sentences=3, auto_suggest=False, redirect=True)
        return AR(s)
    except Exception:
        return None

# ===== مشاعر وتحيات =====
GREET = ["مرحبا","مرحباً","اهلاً","أهلاً","السلام عليكم","هلا","صباح الخير","مساء الخير","هاي","شلونك","كيفك"]
FARE = ["مع السلامة","إلى اللقاء","تصبح على خير","اشوفك لاحقاً","باي"]
TAGLINES = [
    "أنا بسّام الذكي — هنا عشان أساعدك بخطوات بسيطة وواضحة ✨",
    "بسّام معك! نحلها خطوة بخطوة وبهدوء 💪",
]
def answer_empathy(q: str) -> Optional[str]:
    for w in GREET:
        if w in q:
            return ("وعليكم السلام ورحمة الله — أهلاً وسهلاً! 😊\n"+TAGLINES[0]) if "السلام" in w else ("مرحبًا! سعيد بوجودك 🤝\n"+TAGLINES[1])
    for w in FARE:
        if w in q: return "في حفظ الله! إذا احتجت أي شيء أنا حاضر دائمًا 🌟"
    if re.search(r"(شكرا|ثنكيو|thank|ممتاز|جزاك الله خير)", q, re.I): return "شكرًا لذوقك! يسعدني أساعدك دائمًا 🙏"
    return None

# ===== Beauty Coach =====
BEAUTY_PAT = re.compile(r"(بشرة|تفتيح|بياض|غسول|رتينول|فيتامين|شعر|تساقط|قشره|حب شباب|حبوب|رؤوس سوداء|ترطيب|واقي|رشاقه|تخسيس|رجيم)", re.I)
def beauty_coach(q: str) -> Optional[str]:
    if not BEAUTY_PAT.search(q): return None
    ql = q.lower()
    tips = [
        "🧼 غسول لطيف صباحًا ومساءً.",
        "🧴 ترطيب يومي (حتى للبشرة الدهنية بجلّ خفيف).",
        "🛡️ واقي شمس SPF 30+ يوميًا.",
        "🛌 نوم كافٍ + ماء بانتظام.",
    ]
    if re.search(r"(تفتيح|بياض|اسمرار|غموق)", ql):
        tips += ["فيتامين C صباحًا 3–10% + SPF","نياسيناميد 4–10% مساءً","تجنب الخلطات المجهولة."]
    if re.search(r"(حب شباب|الحبوب|blackhead|whitehead|رؤوس)", ql):
        tips += ["بنزويل بيروكسيد 2.5–5%","ساليسيليك أسيد 0.5–2%","ريتينول تدريجيًا ليلًا 1–2×/أسبوع"]
    if re.search(r"(شعر|تساقط|قشره)", ql):
        tips += ["تدليك الفروة 5 دقائق يوميًا","زيوت خفيفة للأطراف","تأكد من الحديد/فيتامين D"]
    if re.search(r"(رشاقه|تخسيس|وزن|رجيم|دايت)", ql):
        tips += ["عجز حراري 300–500 سعرة","مشي 30 دقيقة 5 أيام/أسبوع","تجنّب الحميات القاسية"]
    return "أنا معك — خطوة بخطوة ✨\n" + "\n".join("• "+t for t in tips[:10])

# ===== RAG =====
def answer_rag(q: str, k: int = 4) -> Optional[str]:
    # (1) cache index من indexer.py
    if RAG_EMB and rag_cache_ready():
        try:
            index  = cache.get("rag:index")
            chunks = cache.get("rag:chunks")
            metas  = cache.get("rag:metas")
            if index and chunks and metas:
                qv = RAG_EMB.encode([q], convert_to_numpy=True, normalize_embeddings=True)
                D, I = index.search(qv, k)
                picks = [i for i in I[0] if 0 <= i < len(chunks)]
                if picks:
                    ctx  = "\n\n".join(chunks[i] for i in picks)
                    srcs = sorted(set(metas[i]["source"] for i in picks))
                    summ = summarize_text(ctx, max_sentences=6)
                    return f"{AR(summ)}\n\nالمصادر (RAG):\n" + "\n".join(f"- {s}" for s in srcs)
        except Exception:
            pass
    # (2) retriever من ملفات docs/
    try:
        hits = rag_file_query(q, top_k=k)
        if not hits: return None
        ctx  = "\n\n".join(snippet for _, snippet in hits)
        srcs = [fname for fname, _ in hits]
        if not ctx.strip(): return None
        summ = summarize_text(ctx, max_sentences=6)
        return f"{AR(summ)}\n\nالمصادر (RAG):\n" + "\n".join(f"- {s}" for s in sorted(set(srcs)))
    except Exception:
        return None

# ===== Gemini اختياري =====
def answer_gemini(q: str) -> Optional[str]:
    if not GEMINI: return None
    try:
        resp = GEMINI.generate_content("أجب بالعربية الواضحة باختصار ودقة وبنبرة ودودة:\n"+q)
        return (resp.text or "").strip()
    except Exception:
        return None

# ===== ويب + تلخيص محلي =====
def answer_from_web(q: str) -> str:
    key = f"w:{q}"
    c = cache.get(key)
    if c: return c
    hits = ddg_text(q, n=5)
    contexts, cites = [], []
    for h in hits:
        url = h.get("href") or h.get("url")
        if not url: continue
        txt = fetch_clean(url)
        if txt:
            contexts.append(txt)
            cites.append(url)
    if not contexts:
        return "لم أجد مصادر كافية الآن. جرّب/ي إعادة الصياغة."
    blob = "\n\n".join(contexts)[:16000]
    summ = summarize_text(blob, max_sentences=6)
    ans = AR(summ) + ("\n\nالمصادر:\n" + "\n".join(f"- {u}" for u in cites[:5]) if cites else "")
    cache.set(key, ans, expire=3600)
    return ans

# ===== الموجه الرئيسي (بدون ذاكرة) =====
def omni_answer(q: str) -> str:
    q = AR(q)
    if not q: return "اكتب/ي سؤالك أولًا."
    a = answer_empathy(q)
    if a: return a
    for tool in (answer_math, answer_units_dates, beauty_coach, answer_wikipedia):
        a = tool(q)
        if a: return a
    a = answer_rag(q)
    if a: return a
    a = answer_gemini(q)
    if a: return a
    return answer_from_web(q)

# ===== خط أنابيب مع ذاكرة =====
def _extract_name(text: str) -> Optional[str]:
    m = re.search(r"(?:اسمي|انا اسمي|أنا اسمي|my name is)\s+([^\.,\|\n\r]+)", text, re.I)
    if m:
        name = re.sub(r"[^\w\u0600-\u06FF\s\-']", "", m.group(1).strip())
        return name[:40]
    return None

def qa_pipeline(query: str, user_id: str = "guest") -> str:
    q = AR(query or "")
    if not q: return "اكتب/ي سؤالك أولاً."
    # حفظ الاسم إن ظهر
    nm = _extract_name(q)
    if nm:
        remember(user_id, "name", nm)
        return f"تشرفت بمعرفتك يا {nm} 🌟"
    name = recall(user_id, "name", None)
    if name and re.search(r"(شكرا|ثنكيو|thanks)", q, re.I):
        remember(user_id, "last_query", q); return f"العفو يا {name}! 🙏"
    if name and re.search(r"(كيفك|شلونك|اخبارك)", q):
        remember(user_id, "last_query", q); return f"تمام الحمدلله، وأنت يا {name}؟ 😊"
    ans = omni_answer(q)
    remember(user_id, "last_query", q)
    if name and isinstance(ans, str) and len(ans) < 400:
        ans = f"{ans}\n\n— معك بسّام، دايمًا حاضر يا {name} 🌟"
    return ans
