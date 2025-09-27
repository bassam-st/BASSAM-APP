import os, re, httpx
from typing import List, Dict

import google.generativeai as genai
from duckduckgo_search import DDGS
from readability import Document
from bs4 import BeautifulSoup

# ===== إعداد Gemini =====
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    GEMINI_MODEL = genai.GenerativeModel("gemini-1.5-flash")
else:
    GEMINI_MODEL = None

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# ===== البحث المجاني (DuckDuckGo) =====
def web_search_duckduckgo(q: str, max_n: int = 5) -> List[Dict]:
    with DDGS() as ddgs:
        results = ddgs.text(q, region="xa-ar", safesearch="moderate", max_results=max_n)
        return list(results or [])

# ===== جلب وتنظيف الصفحات =====
def fetch_clean(url: str, timeout: int = 12) -> str:
    try:
        r = httpx.get(url, headers=UA, timeout=timeout, follow_redirects=True)
        r.raise_for_status()
        doc = Document(r.text)
        html_clean = doc.summary()
        txt = BeautifulSoup(html_clean, "lxml").get_text("\n", strip=True)
        # حد أعلى للنص لحماية النموذج
        return txt[:8000]
    except Exception:
        return ""

# ===== استدعاء Gemini =====
def answer_with_gemini(prompt: str) -> str:
    if not GEMINI_MODEL:
        # حالة عدم وجود مفتاح — نعطي رسالة واضحة
        return (
            "⚠️ لم يتم ضبط مفتاح GEMINI_API_KEY. أضفه في إعدادات Render ثم أعد النشر.\n"
            "جواب مبدئي: " + prompt[:120]
        )
    try:
        resp = GEMINI_MODEL.generate_content(prompt)
        return (resp.text or "").strip()
    except Exception as e:
        return f"⚠️ حدث خطأ عند الاتصال بـ Gemini: {e}"

# ===== خط أنابيب السؤال والإجابة =====
def qa_pipeline(question: str) -> str:
    question = (question or "").strip()
    if not question:
        return "اكتب سؤالك أولًا."

    # 1) محاولة إجابة مباشرة سريعة
    direct = answer_with_gemini(
        (
            "أجب بالعربية الفصحى، بإيجاز ودقة، وبدون زخرفة.\n"
            "إذا كان السؤال عامًا فأعطِ خلاصة واضحة.\n\n"
            f"السؤال: {question}\n"
        )
    )

    # إذا كان الجواب قصيرًا جدًا أو عامًا، نعزز بسياقات من الويب
    if len(direct) < 40 or re.search(r"غير واضح|لا أستطيع|معذرة|لا أملك", direct):
        hits = web_search_duckduckgo(question, max_n=5)
        contexts = []
        cites = []
        for h in hits:
            url = h.get("href") or h.get("url")
            if not url:
                continue
            text = fetch_clean(url)
            if text:
                contexts.append(f"[المصدر] {url}\n{text}")
                cites.append(url)
        context_blob = "\n\n".join(contexts)[:15000] or "لا توجد سياقات كافية."

        prompt = (
            "أنت مساعد عربي مختصر ودقيق.\n"
            "استخدم المعلومات التالية للإجابة عن السؤال، ثم اعرض في النهاية قائمة نقاط للمصادر المستخدمة.\n\n"
            f"السؤال: {question}\n\n"
            f"السياقات:\n{context_blob}\n\n"
            "التنسيق المطلوب:\n"
            "- الإجابة بالعربية الواضحة.\n"
            "- في النهاية ضع عنوان: المصادر: ثم نقاط لكل رابط.\n"
        )
        answer = answer_with_gemini(prompt)
        # إن لم يذكر المصادر، نضيفها يدويًا كملحق
        if cites and "المصادر" not in answer:
            answer += "\n\nالمصادر:\n" + "\n".join(f"- {u}" for u in cites[:5])
        return answer

    return direct
