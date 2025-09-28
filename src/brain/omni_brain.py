import os, re, math, json, time
from datetime import datetime
from dateutil import parser as dateparser
from typing import List, Dict, Optional

import httpx
from bs4 import BeautifulSoup
from readability import Document
from duckduckgo_search import DDGS
from diskcache import Cache
from wikipedia import summary as wiki_summary

from sympy import sympify, diff, integrate
from sumy.parsers.plaintext import PlainTextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

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

# ===== مساعدات نصية =====
AR = lambda s: re.sub(r"\s+", " ", (s or "").strip())

# ===== تلخيص محلي =====
def summarize_text(text: str, max_sentences: int = 5) -> str:
    try:
        parser = PlainTextParser.from_string(text, Tokenizer("arabic"))
        summ = TextRankSummarizer()
        sents = summ(parser.document, max_sentences)
        return " ".join(str(s) for s in sents)
    except Exception:
        return text[:700]

# ===== بحث الويب =====
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
    if not MATH_PAT.search(q):
        return None
    try:
        s = q.replace("^", "**")
        expr = sympify(s)
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
    # عملة بسيطة: "100 USD إلى YER"
    m = re.search(r"(\d+[\.,]?\d*)\s*(USD|EUR|SAR|AED|YER)\s*(?:->|الى|إلى|to)\s*(USD|EUR|SAR|AED|YER)", q, re.I)
    if m:
        amount = float(m.group(1).replace(",", "."))
        src, dst = m.group(2).upper(), m.group(3).upper()
        usd = amount / CURRENCY[src]
        out = usd * CURRENCY[dst]
        return f"تقريبًا: {amount} {src} ≈ {round(out,2)} {dst}"
    # تاريخ/وقت بسيط: "ما تاريخ 3 أيام بعد 2025-09-27"
    m2 = re.search(r"(\d+)\s*(يوم|أيام|day|days)\s*(?:بعد|later|from)\s*([0-9\-/: ]+)", q, re.I)
    if m2:
        n = int(m2.group(1)); base = dateparser.parse(m2.group(3))
        if base:
            return (base + __import__('datetime').timedelta(days=n)).strftime("%Y-%m-%d %H:%M")
    return None

# ===== ويكيبيديا قصيرة =====
def answer_wikipedia(q: str) -> Optional[str]:
    m = re.search(r"^(من هو|من هي|ما هي|ماهو|ماهي)\s+(.+)$", q.strip(), re.I)
    topic = m.group(2) if m else None
    topic = topic or (q if len(q.split())<=6 else None)
    if not topic:
        return None
    try:
        s = wiki_summary(topic, sentences=3, auto_suggest=False, redirect=True)
        return AR(s)
    except Exception:
        return None

# ===== مشاعر وتحيات (شخصية ودودة) =====
GREET_WORDS = [
    "مرحبا", "مرحباً", "اهلاً", "أهلاً", "السلام عليكم", "هلا", "صباح الخير", "مساء الخير",
    "هاي", "هَاي", "ازيك", "شلونك", "كيفك"
]
FAREWELL_WORDS = ["مع السلامة", "إلى اللقاء", "تصبح على خير", "اشوفك لاحقاً", "باي"]

PERSONA_TAGLINES = [
    "أنا بسّام الذكي — هنا عشان أساعدك بخطوات بسيطة وواضحة ✨",
    "بسّام معك! نحلها خطوة بخطوة وبهدوء 💪",
]

def answer_empathy(q: str) -> Optional[str]:
    for w in GREET_WORDS:
        if w in q:
            return (
                "وعليكم السلام ورحمة الله — أهلاً وسهلاً! 😊\n"
                + PERSONA_TAGLINES[0]
            ) if "السلام" in w else (
                "مرحبًا! سعيد بوجودك 🤝\n" + PERSONA_TAGLINES[1]
            )
    for w in FAREWELL_WORDS:
        if w in q:
            return "في حفظ الله! إذا احتجت أي شيء أنا حاضر دائمًا 🌟"
    if re.search(r"(أنا حزين|حزينه|متضايق|متضايقة|قلقان|قلقانه|زعلان)", q):
        return (
            "أنا هنا معك 💙 — خذ نفسًا عميقًا، وقل لي ما الذي يزعجك خطوة خطوة."
            " أعدك أنني سأكون لطيفًا وواضحًا ونفكر سويًا بحلول عملية."
        )
    if re.search(r"(شكرا|ثنكيو|thank|ممتاز|جزاك الله خير)", q, re.I):
        return "شكرًا لذوقك! يسعدني أساعدك دائمًا 🙏"
    return None

# ===== Beauty Coach (العناية والجمال) =====
BEAUTY_PAT = re.compile(
    r"(بشره|بشرة|تفتيح|بياض|غسول|رتينول|فيتامين|شعر|طول شعر|تساقط|قشره|حب شباب|حبوب|رؤوس سوداء|ترطيب|واقي|رشاقه|تخسيس|رجيم)",
    re.I
)

def beauty_coach(q: str) -> Optional[str]:
    if not BEAUTY_PAT.search(q):
        return None
    ql = q.lower()
    tips = []

    # أساسيات عامة
    base = [
        "🧼 غسول لطيف صباحًا ومساءً (بدون سلفات/كحول قوي).",
        "🧴 ترطيب يومي — البشرة الدهنية تحتاج ترطيب أيضًا (جل/لوشن خفيف).",
        "🛡️ واقي شمس SPF 30+ يوميًا — أهم خطوة لتفتيح وتقليل الحبوب والآثار.",
        "🛌 نوم كافٍ وشرب ماء بانتظام — يؤثران مباشرة على المظهر.",
    ]

    if re.search(r"(تفتيح|بياض|اسمرار|غُمُوق|غموق)", ql):
        tips += [
            "فيتامين C صباحًا (3–10%) + واقي شمس — يساعد على توحيد اللون.",
            "نياسيناميد 4–10% مساءً لتقليل التصبغ واللمعان.",
            "تجنب خلطات مجهولة/مواد مبيضة قاسية. إن وُجد تصبغ شديد → راجِع/ي مختص جلدية.",
        ]
    if re.search(r"(حب شباب|الحبوب|رؤوس سوداء|whitehead|blackhead)", ql):
        tips += [
            "بنزويل بيروكسيد 2.5–5% للحبوب الملتهبة (موضعيًا وبكمية صغيرة).",
            "ساليسيليك أسيد 0.5–2% للرؤوس السوداء وتنظيف المسام.",
            "الريتينول تدريجيًا ليلًا 1–2× بالأسبوع (ثم زيادة حسب التحمل).",
            "غيّر/ي غطاء الوسادة بانتظام وقلّل/ي اللمس باليدين.",
            "لو حب شديد/ندبات/حمل — الأفضل مراجعة جلدية لخيارات مثل أدابالين/إيزوتريتينوين بإشراف طبي.",
        ]
    if re.search(r"(شعر|طول شعر|تساقط|قشره)", ql):
        tips += [
            "تدليك فروة الرأس 5 دقائق يوميًا لتحفيز الدورة الدموية.",
            "زيوت خفيفة على الأطراف (أرجان/جوجوبا) وليس على الفروة إذا كانت دهنية.",
            "تغذية: بروتين كافٍ وحديد وفيتامين D — نقصهم يسبب تساقطًا.",
            "قشرة؟ جرّب/ي شامبو كيتوكونازول 2% مرتين أسبوعيًا.",
            "تساقط ملحوظ/فراغات؟ تحاليل (حديد، فيتامين D، غدة) ثم مختص جلدية.",
        ]
    if re.search(r"(رشاقه|تخسيس|وزن|سمنه|سمنة|دايت|رجيم)", ql):
        tips += [
            "ابدأ/ئي بخطوات ثابتة: عجز حراري معتدل (300–500 سعر/يوم).",
            "لوحة وجبة: نصفها خضار، ربع بروتين، ربع نشويات كاملة.",
            "مشي سريع 30 دقيقة — 5 أيام/أسبوع + مقاومة خفيفة مرتين/أسبوع.",
            "تجنّب/ي الحميات القاسية/المدرّات/المكمّلات المجهولة — السلامة أولًا.",
        ]

    if not tips:
        tips = base
    else:
        tips = base + tips

    closing = (
        "\n\n💬 تذكير لطيف: الاستمرارية أهم من الكمال."
        " للحالات الشديدة/الحمل/الأدوية المزمنة — استشر/ي مختصًا."
    )

    return (
        "أنا معك — خطوة بخطوة نوصّل لأجمل نتيجة تناسبك ✨\n"
        + "\n".join(f"• {t}" for t in tips[:10]) + closing
    )

# ===== Gemini اختياري =====
def answer_gemini(q: str) -> Optional[str]:
    if not GEMINI:
        return None
    try:
        resp = GEMINI.generate_content("أجب بالعربية الواضحة باختصار ودقة وبنبرة ودودة:\n"+q)
        return (resp.text or "").strip()
    except Exception as e:
        return f"(تنبيه Gemini): {e}"

# ===== ويب + تلخيص محلي مع مصادر =====
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

# ===== الموجّه الرئيسي =====
def omni_answer(q: str) -> str:
    q = AR(q)
    if not q: return "اكتب/ي سؤالك أولًا."

    # 0) تحيات/مشاعر أولًا
    a = answer_empathy(q)
    if a: return a

    # 1) أدوات محلية + Beauty + ويكيبيديا
    for tool in (answer_math, answer_units_dates, beauty_coach, answer_wikipedia):
        a = tool(q)
        if a: return a

    # 2) Gemini (اختياري)
    a = answer_gemini(q)
    if a: return a

    # 3) ويب + تلخيص محلي
    return answer_from_web(q)
