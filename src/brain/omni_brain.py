# src/brain/omni_brain.py — Omni Brain v3 (أدوات + RAG + ويب + ذاكرة)

import os, re
from typing import List, Dict, Optional
import httpx
from bs4 import BeautifulSoup
from readability import Document
from duckduckgo_search import DDGS
from diskcache import Cache
from wikipedia import summary as wiki_summary
from dateutil import parser as dateparser
from sympy import sympify, diff, integrate

# ✅ Sumy الصحيح
from sumy.parsers.plaintext import PlainTextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

# ذاكرة المستخدم
from src.memory.memory import remember, recall

# RAG (اختياري)
import faiss
from sentence_transformers import SentenceTransformer
from src.rag.indexer import is_ready as rag_cache_ready
from src.rag.retriever import query_index as rag_file_query

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

# Embeddings لـ RAG
try:
    RAG_EMB = SentenceTransformer(os.getenv(
        "RAG_EMB_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    ))
except Exception:
    RAG_EMB = None

AR = lambda s: re.sub(r"\s+", " ", (s or "").strip())

def summarize_text(text: str, max_sentences: int = 5) -> str:
    try:
        parser = PlainTextParser.from_string(text, Tokenizer("arabic"))
        s = TextRankSummarizer()(parser.document, max_sentences)
        return " ".join(str(x) for x in s)
    except Exception:
        return (text or "")[:700]

def ddg_text(q: str, n: int = 5) -> List[Dict]:
    with DDGS() as ddgs:
        return list(ddgs.text(q, region="xa-ar", safesearch="moderate", max_results=n) or [])

def fetch_clean(url: str, timeout: int = 12) -> str:
    try:
        r = httpx.get(url, headers=UA, timeout=timeout, follow_redirects=True)
        r.raise_for_status()
        html = Document(r.text).summary()
        return BeautifulSoup(html, "lxml").get_text("\n", strip=True)[:8000]
    except Exception:
        return ""

MATH_PAT = re.compile(r"[=+\-*/^()]|sin|cos|tan|log|sqrt|∫|dx|dy|d/dx|مشتقة|تكامل", re.I)
CURRENCY = {"USD":1.0, "EUR":0.92, "SAR":3.75, "AED":3.67, "YER":250.0}

def answer_math(q: str) -> Optional[str]:
    if not MATH_PAT.search(q): return None
    try:
        expr = sympify(q.replace("^","**"))
        return f"الناتج التقريبي: {expr.evalf()}"
    except Exception:
        if q.strip().startswith("مشتقة "):
            t=q.split("مشتقة ",1)[1]
            try: return f"مشتقة {t} = {diff(sympify(t))}"
            except: return "لم أفهم التعبير للمشتقة."
        if q.strip().startswith("تكامل "):
            t=q.split("تكامل ",1)[1]
            try: return f"تكامل {t} = {integrate(sympify(t))}"
            except: return "لم أفهم التعبير للتكامل."
        return None

def answer_units_dates(q: str) -> Optional[str]:
    m = re.search(r"(\d+[\.,]?\d*)\s*(USD|EUR|SAR|AED|YER)\s*(?:->|الى|إلى|to)\s*(USD|EUR|SAR|AED|YER)", q, re.I)
    if m:
        amount=float(m.group(1).replace(",",".")); src=m.group(2).upper(); dst=m.group(3).upper()
        usd=amount / CURRENCY[src]; out=usd*CURRENCY[dst]
        return f"تقريبًا: {amount} {src} ≈ {round(out,2)} {dst}"
    m2=re.search(r"(\d+)\s*(يوم|أيام|day|days)\s*(?:بعد|later|from)\s*([0-9\-/: ]+)", q, re.I)
    if m2:
        from datetime import timedelta
        n=int(m2.group(1)); base=dateparser.parse(m2.group(3))
        if base: return (base+timedelta(days=n)).strftime("%Y-%m-%d %H:%M")
    return None

def answer_wikipedia(q: str) -> Optional[str]:
    m=re.search(r"^(من هو|من هي|ما هي|ماهو|ماهي)\s+(.+)$", q.strip(), re.I)
    topic=m.group(2) if m else (q if len(q.split())<=6 else None)
    if not topic: return None
    try:
        return AR(wiki_summary(topic, sentences=3, auto_suggest=False, redirect=True))
    except Exception:
        return None

GREET = ["مرحبا","مرحباً","اهلاً","أهلاً","السلام عليكم","هلا","صباح الخير","مساء الخير","هاي","شلونك","كيفك"]
BYE = ["مع السلامة","إلى اللقاء","تصبح على خير","اشوفك لاحقاً","باي"]
def answer_empathy(q: str) -> Optional[str]:
    for w in GREET:
        if w in q: return "مرحبًا! أنا بسّام الذكي — هنا لخدمتك ✨"
    for w in BYE:
        if w in q: return "في أمان الله! إذا احتجتني أنا حاضر 🌟"
    if re.search(r"(حزين|متضايق|قلقان|زعلان)", q): return "أنا معك 💙 احكي لي بهدوء وسنجد حلًا."
    if re.search(r"(شكرا|ثنكيو|thank|جزاك)", q, re.I): return "العفو! يسعدني أساعدك دائمًا 🙏"
    return None

BEAUTY_PAT = re.compile(r"(بشرة|تفتيح|بياض|غسول|رتينول|فيتامين|شعر|تساقط|قشره|حب شباب|حبوب|رؤوس سوداء|ترطيب|واقي|رشاقه|تخسيس|رجيم)", re.I)
def beauty_coach(q: str) -> Optional[str]:
    if not BEAUTY_PAT.search(q): return None
    tips = [
        "🧼 غسول لطيف صباحًا ومساءً.",
        "🧴 ترطيب يومي حتى للبشرة الدهنية (جل خفيف).",
        "🛡️ واقي شمس 30+ SPF يوميًا.",
        "💤 نوم كافٍ وماء بانتظام.",
    ]
    if re.search(r"(تفتيح|اسمرار|غموق)", q): tips += ["فيتامين C صباحًا + SPF","نياسيناميد مساءً","تجنب الخلطات المجهولة"]
    if re.search(r"(حب شباب|رؤوس|blackhead|whitehead)", q): tips += ["بنزويل بيروكسيد 2.5–5%","ساليسيليك 0.5–2%","ريتينول تدريجيًا"]
    if re.search(r"(شعر|تساقط|قشره)", q): tips += ["تدليك الفروة 5 دقائق","زيوت خفيفة للأطراف","فحص الحديد/فيتامين D"]
    if re.search(r"(رشاقه|تخسيس|رجيم|دايت|وزن)", q): tips += ["عجز 300–500 سعرة","مشي 30 دقيقة 5×أسبوع","تجنب الحميات القاسية"]
    return "أنا معك خطوة بخطوة ✨\n" + "\n".join("• "+t for t in tips[:10])

def answer_rag(q: str, k: int = 4) -> Optional[str]:
    # عبر indexer (Cache) إن وُجد
    if RAG_EMB and rag_cache_ready():
        index  = cache.get("rag:index")
        chunks = cache.get("rag:chunks")
        metas  = cache.get("rag:metas")
        if index and chunks and metas:
            vec = RAG_EMB.encode([q], convert_to_numpy=True, normalize_embeddings=True)
            D, I = index.search(vec, k)
            picks = [i for i in I[0] if 0 <= i < len(chunks)]
            if picks:
                ctx  = "\n\n".join(chunks[i] for i in picks)
                srcs = sorted(set(metas[i]["source"] for i in picks))
                summ = summarize_text(ctx, 6)
                return f"{AR(summ)}\n\nالمصادر (RAG):\n" + "\n".join(f"- {s}" for s in srcs)
    # عبر ملفات القرص
    try:
        hits = rag_file_query(q, top_k=k)
        ctx = "\n\n".join(s for _, s in hits)
        if not ctx.strip(): return None
        srcs = [f for f, _ in hits]
        summ = summarize_text(ctx, 6)
        return f"{AR(summ)}\n\nالمصادر (RAG):\n" + "\n".join(f"- {s}" for s in sorted(set(srcs)))
    except Exception:
        return None

def answer_gemini(q: str) -> Optional[str]:
    if not GEMINI: return None
    try:
        r = GEMINI.generate_content("أجب بالعربية باختصار ودقة وود:\n"+q)
        return (r.text or "").strip()
    except Exception as e:
        return f"(تنبيه Gemini): {e}"

def answer_from_web(q: str) -> str:
    key=f"w:{q}"; c=cache.get(key)
    if c: return c
    hits=ddg_text(q, n=5)
    ctxs, cites=[],[]
    for h in hits:
        url=h.get("href") or h.get("url")
        if not url: continue
        t=fetch_clean(url)
        if t: ctxs.append(t); cites.append(url)
    if not ctxs: return "لم أجد مصادر كافية الآن."
    blob="\n\n".join(ctxs)[:16000]
    summ=summarize_text(blob, 6)
    ans=AR(summ)+("\n\nالمصادر:\n"+"\n".join(f"- {u}" for u in cites[:5]) if cites else "")
    cache.set(key, ans, expire=3600)
    return ans

def omni_answer(q: str) -> str:
    q=AR(q)
    if not q: return "اكتب/ي سؤالك أولًا."
    for tool in (answer_empathy, answer_math, answer_units_dates, beauty_coach, answer_wikipedia):
        a=tool(q)
        if a: return a
    a=answer_rag(q);     if a: return a
    a=answer_gemini(q);  if a: return a
    return answer_from_web(q)

# ===== خط الأنابيب مع الذاكرة =====
def _extract_name(text: str) -> Optional[str]:
    m=re.search(r"(?:اسمي|أنا اسمي|my name is)\s+([^\.,\|\n\r]+)", text, re.I)
    if not m: return None
    name=re.sub(r"[^\w\u0600-\u06FF\s\-']", "", m.group(1)).strip()
    return name[:40] if name else None

def qa_pipeline(query: str, user_id: str = "guest") -> str:
    q=AR(query)
    if not q: return "اكتب/ي سؤالك أولًا."
    name_candidate=_extract_name(q)
    if name_candidate:
        remember(user_id, "name", name_candidate)
        return f"تشرفت بمعرفتك يا {name_candidate} 🌟"
    name=recall(user_id, "name", None)
    if name and re.search(r"(شكرا|thanks|ثنكيو)", q, re.I): return f"العفو يا {name} 🙏"
    ans=omni_answer(q)
    remember(user_id, "last_query", q)
    if name and isinstance(ans,str) and len(ans)<400:
        ans += f"\n\n— معك بسّام، حاضر يا {name} 🌟"
    return ans
