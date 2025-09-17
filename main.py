# main.py — بحث عربي مجاني + تلخيص ذكي + أسعار المتاجر + صور + تقييم + PDF + نسخ + وضع ليلي
from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from ddgs import DDGS
from readability import Document
from bs4 import BeautifulSoup
from diskcache import Cache
from urllib.parse import urlparse, urlencode
from fpdf import FPDF
import requests, re, html, time

app = FastAPI()
cache = Cache(".cache")

# ---------------- إعدادات ----------------
PREFERRED_AR_DOMAINS = {
    "ar.wikipedia.org", "ar.m.wikipedia.org",
    "mawdoo3.com", "almrsal.com", "sasapost.com",
    "arabic.cnn.com", "bbcarabic.com", "aljazeera.net",
    "ar.wikihow.com", "moe.gov.sa", "yemen.gov.ye", "moh.gov.sa"
}

MARKET_SITES = [
    "alibaba.com", "1688.com", "aliexpress.com",
    "amazon.com", "amazon.ae", "amazon.sa", "amazon.eg",
    "noon.com", "jumia.com", "jumia.com.eg",
    "ebay.com", "made-in-china.com", "temu.com", "souq.com"
]

HDRS = {"User-Agent": "Mozilla/5.0 (compatible; BassamBot/1.2)"}

# -------- أدوات اللغة والملخص --------
AR_RE = re.compile(r"[اأإآء-ي]")
def is_arabic(text: str, min_ar_chars: int = 30) -> bool:
    return len(AR_RE.findall(text or "")) >= min_ar_chars

# -------- النظام الذكي للإجابة على الأسئلة --------
class SmartAnswerEngine:
    def __init__(self):
        self.question_types = {
            'ما هو': 'definition',
            'ما هي': 'definition', 
            'كيف': 'how_to',
            'لماذا': 'why',
            'متى': 'when',
            'أين': 'where',
            'من': 'who',
            'كم': 'quantity',
            'هل': 'yes_no'
        }
        
    def analyze_question(self, question: str):
        """تحليل السؤال لفهم نوعه والمعلومات المطلوبة"""
        question_lower = question.strip().lower()
        
        # تحديد نوع السؤال
        question_type = 'general'
        for keyword, qtype in self.question_types.items():
            if question_lower.startswith(keyword):
                question_type = qtype
                break
        
        # استخراج الكلمات المفتاحية
        keywords = self.extract_keywords(question)
        
        # تحديد إذا كان السؤال يحتاج تفصيل
        needs_detail = any(word in question_lower for word in ['اشرح', 'فصل', 'وضح', 'بالتفصيل'])
        
        return {
            'type': question_type,
            'keywords': keywords,
            'needs_detail': needs_detail,
            'original': question
        }
    
    def extract_keywords(self, text: str):
        """استخراج الكلمات المفتاحية من النص"""
        # إزالة كلمات الاستفهام وحروف الجر
        stop_words = {'ما', 'هو', 'هي', 'كيف', 'لماذا', 'متى', 'أين', 'من', 'كم', 'هل', 
                     'في', 'على', 'إلى', 'من', 'عن', 'مع', 'ضد', 'تحت', 'فوق'}
        
        words = text.split()
        keywords = [word.strip('؟،.!') for word in words if word not in stop_words and len(word) > 2]
        return keywords[:5]  # أهم 5 كلمات
        
    def generate_smart_answer(self, question_analysis, search_results, detailed=False):
        """توليد إجابة ذكية مختصرة من نتائج البحث"""
        if not search_results:
            return "لم أتمكن من العثور على إجابة مناسبة لسؤالك. حاول إعادة صياغة السؤال."
            
        # جمع المعلومات من جميع المصادر
        all_content = []
        sources = []
        
        for result in search_results:
            if result.get('content'):
                all_content.append(result['content'])
                sources.append(result.get('title', 'مصدر'))
        
        if not all_content:
            return "لم أجد معلومات كافية للإجابة على سؤالك."
        
        # تحليل نوع السؤال وتوليد إجابة مناسبة
        answer = self.create_targeted_answer(question_analysis, all_content, detailed)
        
        # إضافة مصادر الإجابة
        if len(sources) > 0:
            source_list = ", ".join(sources[:3])  # أول 3 مصادر
            answer += f"\n\nالمصادر: {source_list}"
            
        return answer
    
    def create_targeted_answer(self, analysis, content_list, detailed):
        """إنشاء إجابة مستهدفة حسب نوع السؤال"""
        combined_content = " ".join(content_list)
        question_type = analysis['type']
        
        if question_type == 'definition':
            return self.answer_definition(combined_content, detailed)
        elif question_type == 'how_to':
            return self.answer_how_to(combined_content, detailed)
        elif question_type == 'why':
            return self.answer_why(combined_content, detailed)
        elif question_type == 'when':
            return self.answer_when(combined_content, detailed)
        elif question_type == 'where':
            return self.answer_where(combined_content, detailed)
        elif question_type == 'who':
            return self.answer_who(combined_content, detailed)
        else:
            return self.answer_general(combined_content, detailed)
    
    def answer_definition(self, content, detailed):
        """إجابة أسئلة التعريف (ما هو/ما هي)"""
        sentences = self.split_into_sentences(content)
        
        # البحث عن جمل التعريف
        definition_sentences = []
        for sentence in sentences:
            if any(word in sentence for word in ['هو', 'هي', 'يعرف', 'يُعرّف', 'مصطلح', 'مفهوم']):
                definition_sentences.append(sentence)
        
        if not definition_sentences:
            definition_sentences = sentences[:2]  # أول جملتين
        
        if detailed:
            return " ".join(definition_sentences[:4])  # 4 جمل للتفصيل
        else:
            return definition_sentences[0] if definition_sentences else sentences[0]
    
    def answer_how_to(self, content, detailed):
        """إجابة أسئلة الطريقة (كيف)"""
        sentences = self.split_into_sentences(content)
        
        # البحث عن جمل الخطوات والطرق
        how_sentences = []
        for sentence in sentences:
            if any(word in sentence for word in ['خطوة', 'طريقة', 'كيفية', 'يمكن', 'أولاً', 'ثانياً', 'عبر', 'من خلال']):
                how_sentences.append(sentence)
        
        if not how_sentences:
            how_sentences = sentences[:3]
        
        if detailed:
            return " ".join(how_sentences[:5])
        else:
            return " ".join(how_sentences[:2])
    
    def answer_why(self, content, detailed):
        """إجابة أسئلة السبب (لماذا)"""
        sentences = self.split_into_sentences(content)
        
        why_sentences = []
        for sentence in sentences:
            if any(word in sentence for word in ['سبب', 'لأن', 'نتيجة', 'بسبب', 'يؤدي', 'يسبب', 'السبب']):
                why_sentences.append(sentence)
        
        if not why_sentences:
            why_sentences = sentences[:2]
        
        if detailed:
            return " ".join(why_sentences[:4])
        else:
            return why_sentences[0] if why_sentences else sentences[0]
    
    def answer_when(self, content, detailed):
        """إجابة أسئلة الوقت (متى)"""
        sentences = self.split_into_sentences(content)
        
        when_sentences = []
        for sentence in sentences:
            if any(word in sentence for word in ['عام', 'تاريخ', 'يوم', 'شهر', 'قبل', 'بعد', 'في', 'منذ']):
                when_sentences.append(sentence)
        
        if not when_sentences:
            when_sentences = sentences[:2]
        
        return " ".join(when_sentences[:3 if detailed else 1])
    
    def answer_where(self, content, detailed):
        """إجابة أسئلة المكان (أين)"""
        sentences = self.split_into_sentences(content)
        
        where_sentences = []
        for sentence in sentences:
            if any(word in sentence for word in ['في', 'بـ', 'تقع', 'يقع', 'موقع', 'مكان', 'دولة', 'مدينة']):
                where_sentences.append(sentence)
        
        if not where_sentences:
            where_sentences = sentences[:2]
        
        return " ".join(where_sentences[:3 if detailed else 1])
    
    def answer_who(self, content, detailed):
        """إجابة أسئلة الهوية (من)"""
        sentences = self.split_into_sentences(content)
        
        who_sentences = []
        for sentence in sentences:
            if any(word in sentence for word in ['شخص', 'رجل', 'امرأة', 'عالم', 'مؤلف', 'رئيس', 'مدير']):
                who_sentences.append(sentence)
        
        if not who_sentences:
            who_sentences = sentences[:2]
        
        return " ".join(who_sentences[:3 if detailed else 1])
    
    def answer_general(self, content, detailed):
        """إجابة عامة للأسئلة الأخرى"""
        sentences = self.split_into_sentences(content)
        
        if detailed:
            return " ".join(sentences[:5])
        else:
            return " ".join(sentences[:2])
    
    def split_into_sentences(self, text):
        """تقسيم النص إلى جمل"""
        sentences = re.split(r'[.!؟\?\n]+', text)
        clean_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # جمل ذات معنى
                clean_sentences.append(sentence)
        return clean_sentences[:10]  # أول 10 جمل فقط

# إنشاء محرك الإجابة الذكية
smart_engine = SmartAnswerEngine()

STOP = set("""من في على إلى عن أن إن بأن كان تكون يكون التي الذي الذين هذا هذه ذلك هناك ثم حيث كما اذا إذا أو و يا ما مع قد لم لن بين لدى لدى، عند بعد قبل دون غير حتى كل أي كيف لماذا متى هل الى ال""".split())

def tokenize(s: str):
    s = re.sub(r"[^\w\s\u0600-\u06FF]+", " ", s.lower())
    toks = [t for t in s.split() if t and t not in STOP]
    return toks

def score_sentences(text: str, query: str):
    sentences = re.split(r'(?<=[\.\!\?\؟])\s+|\n+', text or "")
    q_terms = set(tokenize(query))
    scored = []
    for s in sentences:
        s2 = s.strip()
        if len(s2) < 25 or not is_arabic(s2, 8):
            continue
        terms = set(tokenize(s2))
        inter = q_terms & terms
        score = len(inter) + (len(s2) >= 80)
        if score > 0:
            scored.append((score, s2))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [s for _, s in scored[:8]]

def summarize_from_text(text: str, query: str, max_sentences=3):
    sents = score_sentences(text, query)
    return " ".join(sents[:max_sentences]) if sents else ""

def domain_of(url: str):
    try:
        return urlparse(url).netloc.lower()
    except:
        return url

# -------- نقاط النطاقات (تعلم ذاتي بسيط) --------
def get_scores():
    return cache.get("domain_scores", {}) or {}

def save_scores(scores):
    cache.set("domain_scores", scores, expire=0)

def bump_score(domain: str, delta: int):
    if not domain:
        return
    scores = get_scores()
    scores[domain] = scores.get(domain, 0) + delta
    save_scores(scores)

# -------- جلب الصفحات --------
def fetch(url: str, timeout=3):
    r = requests.get(url, headers=HDRS, timeout=timeout)
    r.raise_for_status()
    return r.text

def fetch_and_extract(url: str, timeout=3):
    try:
        html_text = fetch(url, timeout=timeout)
        if not html_text or len(html_text.strip()) < 100:
            return "", ""
        
        # تنظيف HTML من المحتوى الضار قبل المعالجة
        html_text = html_text.replace('\x00', '').replace('\x0b', '').replace('\x0c', '')
        html_text = ''.join(char for char in html_text if ord(char) >= 32 or char in '\n\r\t')
        
        try:
            doc = Document(html_text)
            content_html = doc.summary()
        except:
            # إذا فشل readability، استخدم BeautifulSoup مباشرة
            soup = BeautifulSoup(html_text, "html.parser")
            # أخذ النص من الفقرات الرئيسية
            content = soup.find_all(['p', 'article', 'div'], limit=10)
            content_html = ''.join(str(tag) for tag in content)
        
        soup = BeautifulSoup(content_html, "html.parser")
        text = soup.get_text(separator="\n")
        return html.unescape(text), html_text
    except Exception as e:
        print(f"error getting summary: {e}")
        return "", ""

# -------- استخراج الأسعار --------
PRICE_RE = re.compile(r"(?i)(US?\s*\$|USD|EUR|GBP|AED|SAR|EGP|QAR|KWD|OMR|د\.إ|ر\.س|ج\.م|د\.ك|ر\.ق|ر\.ع)\s*[\d\.,]+")
AR_NUM = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def extract_price_from_html(html_text: str):
    if not html_text:
        return ""
    text = BeautifulSoup(html_text, "html.parser").get_text(separator=" ")
    text = text.translate(AR_NUM)
    m = PRICE_RE.search(text)
    return m.group(0).strip() if m else ""

def try_get_price(url: str):
    try:
        h = fetch(url, timeout=3)
        price = extract_price_from_html(h)
        if price:
            return price
        soup = BeautifulSoup(h, "html.parser")
        meta_price = soup.find(attrs={"itemprop": "price"}) or soup.find("meta", {"property":"product:price:amount"})
        if meta_price:
            val = meta_price.get("content") or meta_price.text
            if val and re.search(r"[\d\.,]", val):
                return val.strip()
        time.sleep(0.3)
        h2 = fetch(url, timeout=3)
        return extract_price_from_html(h2)
    except Exception:
        return ""

# ---------------- واجهة HTML ----------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl" data-theme="light">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>بسام الذكي - مجاني</title>
  <style>
    :root {{
      --bg:#ffffff; --fg:#111; --muted:#666; --card:#f7f7f7; --accent:#0b63c6; --summary:#eef6ff;
    }}
    [data-theme="dark"] {{
      --bg:#0f172a; --fg:#e5e7eb; --muted:#9ca3af; --card:#111827; --accent:#60a5fa; --summary:#0b2942;
    }}
    body {{ background:var(--bg); color:var(--fg); font-family: Tahoma, Arial; padding:18px; max-width:960px; margin:auto; }}
    input[type=text], select {{ width:100%; padding:12px; font-size:16px; background:var(--card); color:var(--fg); border:1px solid #334155; border-radius:10px; }}
    button {{ padding:10px 18px; font-size:16px; margin-top:8px; border-radius:10px; border:1px solid #334155; background:var(--card); color:var(--fg); cursor:pointer; }}
    .row {{ display:flex; gap:10px; flex-wrap:wrap; }}
    .col {{ flex:1 1 200px; min-width:220px; }}
    .card {{ background:var(--card); padding:12px; border-radius:10px; }}
    .summary {{ background:var(--summary); padding:12px; border-radius:10px; margin-top:10px; }}
    a {{ color:var(--accent); text-decoration:none; }}
    h1 {{ margin-top:0; }}
    .note {{ color:var(--muted); font-size:13px; }}
    .fb {{ display:inline-flex; gap:8px; margin-top:8px; }}
    .btn-mini {{ padding:6px 10px; font-size:13px; border:1px solid #334155; border-radius:8px; background:var(--bg); color:var(--fg); cursor:pointer; }}
    .toolbar {{ display:flex; gap:10px; align-items:center; flex-wrap:wrap; }}
    .imggrid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap:10px; }}
    .imgcard {{ overflow:hidden; border-radius:10px; border:1px solid #334155; }}
    .imgcard img {{ width:100%; height:140px; object-fit:cover; display:block; }}
  </style>
</head>
<body>
  <div class="toolbar">
    <h1 style="flex:1;">بسام الذكي — بحث / تلخيص / أسعار / صور (مجاني)</h1>
    <button onclick="toggleTheme()" title="الوضع الليلي/النهاري">🌓 تبديل الوضع</button>
  </div>

  <form method="post" class="row">
    <div class="col"><input type="text" name="question" placeholder="اكتب سؤالك أو اسم/طراز السلعة..." required /></div>
    <div class="col">
      <select name="mode">
        <option value="summary">بحث & تلخيص</option>
        <option value="prices">بحث أسعار (متاجر)</option>
        <option value="images">بحث صور</option>
      </select>
    </div>
    <div class="col" style="max-width:140px;"><button type="submit">تنفيذ</button></div>
  </form>

  {result_panel}

  <p class="note" style="margin-top:18px;">
    التقييم 👍/👎 يحسّن ترتيب المصادر تلقائيًا. زر «نسخ الإجابة» ينسخ الملخّص. زر «تصدير PDF» ينزّل نسخة مرتبة من النتيجة.
  </p>

<script>
// وضع ليلي/نهاري
(function(){{
  const saved = localStorage.getItem("theme");
  if(saved){{ document.documentElement.setAttribute("data-theme", saved); }}
}})();
function toggleTheme(){{
  const cur = document.documentElement.getAttribute("data-theme") || "light";
  const next = cur === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
}}

// نسخ الإجابة
async function copyAnswer(text){{
  try{{
    await navigator.clipboard.writeText(text || "");
    alert("تم نسخ الإجابة!");
  }}catch(e){{ alert("تعذّر النسخ. ربما المتصفح يمنعه."); }}
}}

// إرسال تقييم
async function sendFeedback(domain, delta){{
  try{{
    const fd = new FormData();
    fd.append("domain", domain);
    fd.append("delta", delta.toString());
    const r = await fetch("/feedback", {{method:"POST", body: fd}});
    if(r.ok){{ /* اختياري: رسالة */ }}
  }}catch(e){{ console.log(e); }}
}}
</script>
</body>
</html>
"""

def feedback_buttons(domain: str):
    d = html.escape(domain or "")
    return f'''
      <div class="fb">
        <button class="btn-mini" onclick="sendFeedback('{d}', 1)">👍 مفيد</button>
        <button class="btn-mini" onclick="sendFeedback('{d}', -1)">👎 غير دقيق</button>
      </div>
    '''

def make_summary_card(title, url, summ, domain):
    return (
        f'<div class="card" style="margin-top:10px;"><strong>{html.escape(title)}</strong>'
        f'<div class="summary" style="margin-top:8px;">{html.escape(summ)}</div>'
        f'<div style="margin-top:8px;"><a target="_blank" href="{html.escape(url)}">فتح المصدر</a></div>'
        f'{feedback_buttons(domain)}'
        f'</div>'
    )

def make_price_card(title, url, price, snippet, domain):
    price_html = f"<div><strong>السعر:</strong> {html.escape(price)}</div>" if price else "<div>السعر غير واضح – افتح المصدر للتحقق.</div>"
    sn = f'<div class="note" style="margin-top:6px;">{html.escape((snippet or "")[:180])}</div>' if snippet else ""
    return (
        f'<div class="card" style="margin-top:10px;"><strong>{html.escape(title)}</strong>'
        f'{price_html}'
        f'<div style="margin-top:8px;"><a target="_blank" href="{html.escape(url)}">فتح المصدر</a></div>'
        f'{sn}'
        f'{feedback_buttons(domain)}'
        f'</div>'
    )

def make_toolbar_copy_pdf(q: str, mode: str, answer_text: str):
    pdf_url = "/export_pdf?" + urlencode({"q": q, "mode": mode})
    safe_answer_js = (answer_text or "").replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    return (
        f'<div class="row" style="margin-top:10px;">'
        f'  <div class="col" style="max-width:220px;"><button onclick="copyAnswer(\'{safe_answer_js}\'); return false;">📋 نسخ الإجابة</button></div>'
        f'  <div class="col" style="max-width:220px;"><a href="{pdf_url}" target="_blank"><button type="button">🖨️ تصدير PDF</button></a></div>'
        f'</div>'
    )

# ---------------- أولوية ذكية ----------------
def priority_key(item, mode="summary"):
    scores = get_scores()
    d = domain_of(item.get("href") or item.get("link") or item.get("url") or "")
    base = 2
    if d in PREFERRED_AR_DOMAINS: base -= 1
    if mode == "prices" and any(d.endswith(ms) or d==ms for ms in MARKET_SITES): base -= 0.5
    base -= 0.05 * scores.get(d, 0)
    return base

# ---------------- المسارات ----------------
@app.get("/", response_class=HTMLResponse)
async def form_get():
    return HTML_TEMPLATE.format(result_panel="")

@app.post("/", response_class=HTMLResponse)
async def form_post(question: str = Form(...), mode: str = Form("summary")):
    q = (question or "").strip()
    if not q:
        return HTML_TEMPLATE.format(result_panel="")

    if mode == "prices":
        panel, answer_text = await handle_prices(q, return_plain=True)
    elif mode == "images":
        panel, answer_text = await handle_images(q)
    else:
        panel, answer_text = await handle_summary(q, return_plain=True)

    # شريط أدوات نسخ + PDF
    tools = make_toolbar_copy_pdf(q, mode, answer_text or "")
    return HTML_TEMPLATE.format(result_panel=tools + panel)

@app.post("/feedback")
async def feedback(domain: str = Form(...), delta: int = Form(...)):
    bump_score(domain, int(delta))
    return JSONResponse({"ok": True, "domain": domain, "score": get_scores().get(domain, 0)})

# -------- وضع: بحث & تلخيص عربي --------
async def handle_summary(q: str, return_plain=False):
    cache_key = "sum:" + q
    cached = cache.get(cache_key)
    if cached and not return_plain:
        return cached, ""

    query_ar = q if "بالعربية" in q else (q + " بالعربية")
    with DDGS() as ddgs:
        results = list(ddgs.text(query_ar, region="xa-ar", safesearch="Moderate", max_results=25)) or []
    if not results:
        with DDGS() as ddgs:
            results = list(ddgs.text(query_ar, region="sa-ar", safesearch="Moderate", max_results=25)) or []
    if not results:
        with DDGS() as ddgs:
            results = list(ddgs.text(q, region="xa-ar", safesearch="Moderate", max_results=25)) or []

    source_cards, combined_chunks = [], []
    for r in sorted(results, key=lambda it: priority_key(it, "summary")):
        href = r.get("href") or r.get("link") or r.get("url")
        title = r.get("title") or ""
        if not href:
            continue
        d = domain_of(href)

        ckey = "url:" + href
        val = cache.get(ckey)
        if val is None:
            txt, raw = fetch_and_extract(href)
            if txt and len(txt) > 200:
                cache.set(ckey, (txt, raw), expire=60*60*24)
            val = (txt, raw)
        page_text, raw_html = val

        if not page_text or not is_arabic(page_text):
            continue

        summ = summarize_from_text(page_text, q, max_sentences=3)
        if not summ:
            continue

        combined_chunks.append(summ)
        source_cards.append(make_summary_card(title, href, summ, d))
        if len(source_cards) >= 4:
            break

    if not combined_chunks:
        panel = '<div class="card" style="margin-top:12px;">لم أعثر على محتوى عربي كافٍ. غيّر صياغة السؤال أو أضف كلمة "بالعربية".</div>'
        cache.set(cache_key, panel, expire=60*5)
        return (panel, "") if return_plain else (panel, None)

    final_answer = " ".join(combined_chunks)
    panel = (
        f'<div style="margin-top:18px;">'
        f'<h3>سؤالك:</h3><div class="card">{html.escape(q)}</div>'
        f'<h3 style="margin-top:12px;">الملخّص (من المصادر):</h3><div class="summary">{html.escape(final_answer)}</div>'
        f'<h3 style="margin-top:12px;">المصادر:</h3>'
        f'{"".join(source_cards)}'
        f'</div>'
    )
    cache.set(cache_key, panel, expire=60*60)
    return (panel, final_answer) if return_plain else (panel, None)

# -------- وضع: بحث أسعار المتاجر --------
async def handle_prices(q: str, return_plain=False):
    cache_key = "price:" + q
    cached = cache.get(cache_key)
    if cached and not return_plain:
        return cached, ""

    sites_filter = " OR ".join([f"site:{s}" for s in MARKET_SITES])
    query = f'{q} {sites_filter}'
    with DDGS() as ddgs:
        results = list(ddgs.text(query, region="xa-ar", safesearch="Off", max_results=30)) or []
    if not results:
        with DDGS() as ddgs:
            results = list(ddgs.text(q + " " + sites_filter, region="wt-wt", safesearch="Off", max_results=30)) or []

    cards, seen = [], set()
    lines_for_pdf = []
    for r in sorted(results, key=lambda it: priority_key(it, "prices")):
        url = r.get("href") or r.get("link") or r.get("url")
        title = r.get("title") or ""
        snippet = r.get("body") or ""
        if not url or url in seen:
            continue
        seen.add(url)
        d = domain_of(url)

        price = ""
        try:
            ckey = "purl:" + url
            html_page = cache.get(ckey)
            if html_page is None:
                html_page = fetch(url, timeout=3)
                if html_page and len(html_page) < 1_500_000:
                    cache.set(ckey, html_page, expire=60*60*6)
            price = extract_price_from_html(html_page or "")
            if not price and d.endswith("aliexpress.com"):
                soup = BeautifulSoup(html_page or "", "html.parser")
                meta_price = soup.find(attrs={"itemprop": "price"})
                if meta_price:
                    price = (meta_price.get("content") or meta_price.text or "").strip()
        except Exception:
            price = ""

        cards.append(make_price_card(title, url, price, snippet, d))
        lines_for_pdf.append(f"- {title} | {price or '—'} | {url}")
        if len(cards) >= 10:
            break

    if not cards:
        panel = '<div class="card" style="margin-top:12px;">لم أجد نتائج مناسبة في المتاجر. جرّب اسمًا أدق للمنتج (الموديل/الطراز) أو أضف site:aliexpress.com.</div>'
        cache.set(cache_key, panel, expire=60*5)
        return (panel, "") if return_plain else (panel, None)

    # نص بسيط للتصدير/النسخ
    answer_text = "نتائج أسعار:\n" + "\n".join(lines_for_pdf)
    panel = f'<div style="margin-top:18px;"><h3>بحث أسعار عن: {html.escape(q)}</h3>{"".join(cards)}</div>'
    cache.set(cache_key, panel, expire=60*30)
    return (panel, answer_text) if return_plain else (panel, None)

# -------- وضع: بحث الصور --------
async def handle_images(q: str):
    key = "img:" + q
    cached = cache.get(key)
    if cached:
        return cached, ""

    items = []
    try:
        if DDGS:
            with DDGS() as dd:
                for it in dd.images(keywords=q, region="xa-ar", safesearch="Off", max_results=20):
                    items.append({"title": it.get("title") or "", "image": it.get("image"), "source": it.get("url")})
        else:
            # احتياط: استخدم بحث ويب عادي مع "صور"
            with DDGS() as ddgs:
                results = list(ddgs.text(q + " صور", region="xa-ar", safesearch="Off", max_results=20)) or []
            for r in results:
                items.append({"title": r.get("title") or "", "image": None, "source": r.get("href") or r.get("url")})
    except Exception:
        items = []

    if not items:
        panel = '<div class="card" style="margin-top:12px;">لم أجد صورًا مناسبة. حاول تفاصيل أكثر أو كلمة "صور".</div>'
        cache.set(key, (panel, ""), expire=60*10)
        return panel, ""

    cards = []
    for it in items[:16]:
        img = it.get("image")
        src = it.get("source")
        title = it.get("title") or ""
        if img:
            cards.append(f'<div class="imgcard"><a href="{html.escape(src or img)}" target="_blank"><img src="{html.escape(img)}" alt=""/></a></div>')
        else:
            # لا يوجد صورة مباشرة—نعرض رابط المصدر
            cards.append(f'<div class="card"><a href="{html.escape(src)}" target="_blank">{html.escape(title or "فتح المصدر")}</a></div>')

    panel = f'<div style="margin-top:18px;"><h3>نتائج صور عن: {html.escape(q)}</h3><div class="imggrid">{"".join(cards)}</div></div>'
    cache.set(key, (panel, ""), expire=60*20)
    return panel, ""

# -------- تصدير PDF --------
@app.get("/export_pdf")
def export_pdf(q: str, mode: str = "summary"):
    """
    يبني PDF بسيط من آخر نتيجة في الكاش (حسب q + mode).
    - للملخص: يستخرج نص الملخص والمصادر من الـ panel المخزن.
    - للأسعار: يسرد العناوين/الأسعار/الروابط.
    """
    if mode == "prices":
        panel, ans = handle_prices_sync(q)
        text_for_pdf = ans or "لا توجد بيانات."
        title = f"بحث أسعار: {q}"
    elif mode == "images":
        panel = cache.get("img:" + q)
        title = f"نتائج صور: {q}"
        text_for_pdf = f"عدد العناصر: {len(panel[0]) if panel else 0}\n(يُنصح بفتح الروابط من المتصفح لمعاينة الصور)"
    else:
        panel_html = cache.get("sum:" + q)
        if not panel_html:
            # حاول توليد سريع ثم استخدمه
            p, ans = app.run_sync(handle_summary(q, return_plain=True))  # قد لا يعمل في بعض بيئات ASGI، لذا نعتمد على الكاش في العادة
            panel_html = p
        # محاولة بسيطة لاستخراج الملخص كنص من الـ HTML
        soup = BeautifulSoup(panel_html or "", "html.parser")
        summary_div = soup.find("div", {"class": "summary"})
        text_for_pdf = summary_div.get_text(" ", strip=True) if summary_div else "لا توجد بيانات."
        title = f"ملخص البحث: {q}"

    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('Arial', '', fname='')
    pdf.set_font("Arial", size=14)
    pdf.multi_cell(0, 10, title)
    pdf.ln(4)
    pdf.set_font("Arial", size=12)
    for line in (text_for_pdf or "").split("\n"):
        pdf.multi_cell(0, 8, line)

    pdf_bytes = pdf.output(dest="S").encode("latin1", "ignore")
    headers = {
        "Content-Disposition": f'attachment; filename="bassam_ai_{mode}.pdf"',
        "Content-Type": "application/pdf",
    }
    return Response(content=pdf_bytes, headers=headers)

# نسخة متزامنة مبسطة للوضع السعري لاستخدامها في PDF لو احتجنا
def handle_prices_sync(q: str):
    sites_filter = " OR ".join([f"site:{s}" for s in MARKET_SITES])
    query = f'{q} {sites_filter}'
    with DDGS() as ddgs:
        results = list(ddgs.text(query, region="xa-ar", safesearch="Off", max_results=15)) or []
    if not results:
        with DDGS() as ddgs:
            results = list(ddgs.text(q + " " + sites_filter, region="wt-wt", safesearch="Off", max_results=15)) or []
    lines = []
    for r in results[:10]:
        url = r.get("href") or r.get("link") or r.get("url")
        title = r.get("title") or ""
        price = ""
        try:
            h = fetch(url, timeout=3)
            price = extract_price_from_html(h)
        except Exception:
            pass
        lines.append(f"- {title} | {price or '—'} | {url}")
    panel = ""  # غير مستخدم هنا
    return panel, "نتائج أسعار:\n" + "\n".join(lines)

@app.get("/health")
def health():
    return {"ok": True}