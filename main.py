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

# -------- نظام الحماية الإسلامي المحسن --------
# كلمات مناسبة طبياً/تعليمياً/دينياً
EDUCATIONAL_CONTEXTS = {
    # سياق طبي
    'سرطان الثدي', 'سرطان القضيب', 'رضاعة طبيعية', 'فحص طبي', 'تثقيف جنسي', 'صحة المرأة',
    'أعراض', 'علاج', 'طب', 'صحة', 'تشريح', 'التهاب', 'مرض', 'دواء',
    'breast cancer', 'breastfeeding', 'medical exam', 'sex education', 'reproductive health',
    'symptoms', 'treatment', 'medicine', 'health', 'anatomy', 'inflammation', 'disease',
    
    # سياق ديني/تعليمي
    'حكم الزنا', 'حد الزنا', 'فقه', 'دين', 'شريعة', 'إسلام', 'أحكام', 'حدود',
    'تعليم', 'درس', 'شرح', 'بحث', 'دراسة', 'كتاب', 'مقال', 'موسوعة',
    'islamic ruling', 'religious education', 'study', 'research', 'lesson', 'encyclopedia'
}

# أنماط محظورة محسنة مع حدود الكلمات
PROHIBITED_PATTERNS = [
    # أنماط عربية (كلمات كاملة فقط)
    r'\b(إباحي|إباحية|عاهرة|عاهرات|دعارة|شذوذ|زنا|بغاء|فاحشة)\b',
    r'\b(نيك|نكح|لحس|قضيب|فرج|طيز|بزاز)\b',
    r'\b(بورن|سكس|عاري|عارية|فاضح|فاضحة)\b',
    
    # أنماط إنجليزية مع مقاومة التجاوز  
    r'\b(porn|xxx|fuck|nude|naked|sexy)\b',
    r'\b(prostitute|whore|penis|vagina|orgasm|erotic|fetish)\b',
    r'\b(masturbat\w*)\b',
    
    # أنماط مقاومة للتجاوز
    r's[\W_]*e[\W_]*x(?!tant|agesimal)',  # sex لكن ليس sextant
    r'p[\W_]*o[\W_]*r[\W_]*n',
    r'ج[\W_ـ]*ن[\W_ـ]*س',
    r'س[\W_ـ]*ك[\W_ـ]*س',
]

# تجميع الأنماط المحظورة مع تحسين الأداء
PROHIBITED_REGEX = re.compile('|'.join(PROHIBITED_PATTERNS), re.IGNORECASE | re.UNICODE)

def normalize_text(text: str) -> str:
    """تطبيع النص لإزالة محاولات التجاوز"""
    # إزالة التشكيل والطاولة العربية
    text = re.sub(r'[\u064B-\u065F\u0670\u0640]', '', text)
    # تحويل للأحرف الصغيرة وإزالة المسافات الزائدة
    text = re.sub(r'\s+', ' ', text.lower().strip())
    # إزالة علامات الترقيم والرموز
    text = re.sub(r'[^\w\s]', ' ', text)
    return text

def is_inappropriate_content(text: str) -> bool:
    """فحص متقدم للمحتوى غير المناسب مع تجنب الإيجابيات الخاطئة"""
    if not text or len(text.strip()) < 3:
        return False
    
    # فحص السياق التعليمي/الطبي أولاً
    text_lower = text.lower()
    for context in EDUCATIONAL_CONTEXTS:
        if context in text_lower:
            return False  # محتوى تعليمي/طبي مقبول
    
    # تطبيع النص لمقاومة التجاوز
    normalized_text = normalize_text(text)
    
    # فحص الأنماط المحظورة
    if PROHIBITED_REGEX.search(normalized_text):
        return True
    
    return False

def get_reminder_message() -> str:
    """رسالة تذكيرية مهذبة للمستخدم"""
    return '''
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0;">
        <h3>🕌 تذكير أخوي كريم</h3>
        <p style="font-size: 16px; line-height: 1.6;">
            أخي الكريم، بسام الذكي مخصص للأسئلة المفيدة والمعرفة النافعة.<br>
            تذكر أن الله يراك ويسمعك في كل وقت.<br>
            <strong>"وَاعْلَمُوا أَنَّ اللَّهَ يَعْلَمُ مَا فِي أَنفُسِكُمْ فَاحْذَرُوهُ"</strong>
        </p>
        <p style="margin-top: 15px;">
            🌟 اطرح أسئلة مفيدة عن العلوم، التقنية، الدين، التاريخ، أو أي موضوع يفيدك ويفيد الآخرين
        </p>
    </div>
    '''

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
    result = cache.get("domain_scores", {})
    return result if isinstance(result, dict) else {}

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

def fetch_and_extract(url: str, timeout=2):
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
            val = ""
            if hasattr(meta_price, 'get') and meta_price.get("content"):
                val = meta_price.get("content")
            elif hasattr(meta_price, 'text') and meta_price.text:
                val = meta_price.text
            if val and re.search(r"[\d\.,]", str(val)):
                return str(val).strip()
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
  <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no, viewport-fit=cover"/>
  <title>بسام الذكي - مجاني</title>
  
  <!-- PWA Meta Tags -->
  <meta name="application-name" content="بسام الذكي"/>
  <meta name="description" content="محرك بحث ذكي باللغة العربية مع إجابات مجانية وتلخيص فوري"/>
  <meta name="theme-color" content="#4a90e2"/>
  <meta name="background-color" content="#ffffff"/>
  <meta name="mobile-web-app-capable" content="yes"/>
  <meta name="apple-mobile-web-app-capable" content="yes"/>
  <meta name="apple-mobile-web-app-status-bar-style" content="default"/>
  <meta name="apple-mobile-web-app-title" content="بسام الذكي"/>
  <meta name="msapplication-TileColor" content="#4a90e2"/>
  <meta name="msapplication-tap-highlight" content="no"/>
  
  <!-- PWA Manifest -->
  <link rel="manifest" href="/manifest.json"/>
  
  <!-- Apple Touch Icons -->
  <link rel="apple-touch-icon" href="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTkyIiBoZWlnaHQ9IjE5MiIgdmlld0JveD0iMCAwIDE5MiAxOTIiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGNpcmNsZSBjeD0iOTYiIGN5PSI5NiIgcj0iOTYiIGZpbGw9IiM0YTkwZTIiLz48dGV4dCB4PSI5NiIgeT0iMTEwIiBmaWxsPSJ3aGl0ZSIgZm9udC1zaXplPSI2NCIgZm9udC1mYW1pbHk9IkFyaWFsIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj7YqDwvdGV4dD48L3N2Zz4="/>
  
  <!-- Favicon -->
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48Y2lyY2xlIGN4PSIxNiIgY3k9IjE2IiByPSIxNiIgZmlsbD0iIzRhOTBlMiIvPjx0ZXh0IHg9IjE2IiB5PSIyMCIgZmlsbD0id2hpdGUiIGZvbnQtc2l6ZT0iMTYiIGZvbnQtZmFtaWx5PSJBcmlhbCIgdGV4dC1hbmNob3I9Im1pZGRsZSI+2KI8L3RleHQ+PC9zdmc+"/>
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
    .smart-answer {{ background:linear-gradient(135deg, var(--summary), var(--card)); border-left:4px solid var(--accent); font-weight:500; }}
    .btn-detail {{ background:var(--accent); color:white; padding:8px 16px; border-radius:8px; border:none; margin-top:10px; cursor:pointer; }}
    .btn-detail:hover {{ opacity:0.8; }}
    
    /* PWA & Mobile Optimizations */
    @media (max-width: 768px) {{
      body {{ padding: 12px; }}
      .row {{ flex-direction: column; }}
      .col {{ min-width: auto; }}
      input[type=text], select {{ font-size: 16px; padding: 14px; }}
      button {{ padding: 12px 20px; font-size: 16px; }}
      h1 {{ font-size: 1.5rem; }}
      .toolbar {{ flex-direction: column; align-items: stretch; }}
      .imggrid {{ grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); }}
      .card {{ padding: 10px; }}
    }}
    
    @media (max-width: 480px) {{
      body {{ padding: 8px; }}
      .imggrid {{ grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); }}
      .imgcard img {{ height: 100px; }}
    }}
    
    /* PWA Install Button */
    .install-btn {{ 
      background: linear-gradient(135deg, #4a90e2, #637dfc); 
      color: white; 
      border: none; 
      padding: 12px 20px; 
      border-radius: 10px; 
      font-weight: bold;
      display: none;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(74, 144, 226, 0.3);
    }}
    .install-btn:hover {{ transform: translateY(-2px); }}
    
    /* Loading Spinner */
    .loading {{ 
      display: inline-block; 
      width: 20px; 
      height: 20px; 
      border: 3px solid #f3f3f3; 
      border-top: 3px solid var(--accent); 
      border-radius: 50%; 
      animation: spin 1s linear infinite; 
    }}
    @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    
    /* Offline Indicator */
    .offline-indicator {{ 
      position: fixed; 
      top: 10px; 
      right: 10px; 
      background: #ff4444; 
      color: white; 
      padding: 8px 12px; 
      border-radius: 8px; 
      font-size: 14px; 
      display: none; 
      z-index: 1000;
    }}
    
    /* Smooth Transitions */
    * {{ transition: background-color 0.3s ease, color 0.3s ease; }}
    
    /* Better Touch Targets */
    button, a, input, select {{ min-height: 44px; }}
  </style>
</head>
<body>
  <!-- Offline Indicator -->
  <div class="offline-indicator" id="offlineIndicator">🔄 وضع عدم الاتصال</div>
  
  <div class="toolbar">
    <h1 style="flex:1;">بسام الذكي — بحث / تلخيص / أسعار / صور (مجاني)</h1>
    <button class="install-btn" id="installBtn" onclick="installPWA()">📱 تثبيت التطبيق</button>
    <button onclick="toggleTheme()" title="الوضع الليلي/النهاري">🌓 تبديل الوضع</button>
  </div>

  <form method="post" class="row">
    <div class="col"><input type="text" name="question" placeholder="اكتب سؤالك أو اسم/طراز السلعة..." required /></div>
    <div class="col">
      <select name="mode">
        <option value="smart">🤖 بحث ذكي (بسام AI)</option>
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

// طلب تفاصيل أكثر (آمن)
function showMore(){{
  const form = document.querySelector('form');
  const button = event.target;
  
  // إضافة السؤال الأصلي من data-attribute الآمن
  const questionField = document.querySelector('input[name="question"]');
  const originalQuestion = button.dataset.question;
  if (questionField && originalQuestion) {{
    questionField.value = originalQuestion;
  }}
  
  // إضافة وضع التفصيل
  const detailedField = document.createElement('input');
  detailedField.type = 'hidden';
  detailedField.name = 'detailed';
  detailedField.value = 'true';
  form.appendChild(detailedField);
  
  // إضافة وضع ذكي
  const modeField = document.querySelector('select[name="mode"]');
  if (modeField) {{
    modeField.value = 'smart';
  }}
  
  form.submit();
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

// PWA Functionality
let deferredPrompt;
let isOnline = navigator.onLine;

// تسجيل Service Worker
if ('serviceWorker' in navigator) {{
  window.addEventListener('load', async () => {{
    try {{
      const registration = await navigator.serviceWorker.register('/service-worker.js');
      console.log('✅ Service Worker registered:', registration.scope);
      
      // التحقق من التحديثات
      registration.addEventListener('updatefound', () => {{
        const newWorker = registration.installing;
        newWorker.addEventListener('statechange', () => {{
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {{
            showUpdateNotification();
          }}
        }});
      }});
      
    }} catch (error) {{
      console.error('❌ Service Worker registration failed:', error);
    }}
  }});
}}

// معالجة تثبيت PWA
window.addEventListener('beforeinstallprompt', (e) => {{
  e.preventDefault();
  deferredPrompt = e;
  document.getElementById('installBtn').style.display = 'block';
}});

// تثبيت التطبيق
async function installPWA() {{
  if (!deferredPrompt) {{
    alert('التطبيق مثبت بالفعل أو غير قابل للتثبيت');
    return;
  }}
  
  const result = await deferredPrompt.prompt();
  console.log('PWA install result:', result);
  
  if (result.outcome === 'accepted') {{
    console.log('✅ PWA تم تثبيته');
    document.getElementById('installBtn').style.display = 'none';
  }}
  
  deferredPrompt = null;
}}

// مراقبة حالة الاتصال
function updateOnlineStatus() {{
  const indicator = document.getElementById('offlineIndicator');
  if (navigator.onLine) {{
    indicator.style.display = 'none';
    if (!isOnline) {{
      // عودة الاتصال
      console.log('🌐 الاتصال متوفر مرة أخرى');
    }}
    isOnline = true;
  }} else {{
    indicator.style.display = 'block';
    indicator.textContent = '📴 لا يوجد اتصال بالإنترنت';
    isOnline = false;
  }}
}}

window.addEventListener('online', updateOnlineStatus);
window.addEventListener('offline', updateOnlineStatus);

// إشعار التحديث
function showUpdateNotification() {{
  const updateBanner = document.createElement('div');
  updateBanner.innerHTML = `
    <div style="position:fixed; top:0; left:0; right:0; background:#4a90e2; color:white; padding:12px; text-align:center; z-index:9999;">
      🚀 يتوفر تحديث جديد لبسام الذكي
      <button onclick="location.reload()" style="margin-right:10px; padding:6px 12px; border:none; border-radius:4px; background:white; color:#4a90e2;">
        تحديث الآن
      </button>
      <button onclick="this.parentElement.remove()" style="margin-right:5px; padding:6px 12px; border:none; border-radius:4px; background:rgba(255,255,255,0.2); color:white;">
        لاحقاً
      </button>
    </div>
  `;
  document.body.appendChild(updateBanner);
}}

// تحسين الأداء - تأجيل تحميل الصور
if ('IntersectionObserver' in window) {{
  const imageObserver = new IntersectionObserver((entries) => {{
    entries.forEach(entry => {{
      if (entry.isIntersecting) {{
        const img = entry.target;
        if (img.dataset.src) {{
          img.src = img.dataset.src;
          img.removeAttribute('data-src');
          imageObserver.unobserve(img);
        }}
      }}
    }});
  }});
  
  // مراقبة الصور عند تحميل المحتوى
  setTimeout(() => {{
    document.querySelectorAll('img[data-src]').forEach(img => {{
      imageObserver.observe(img);
    }});
  }}, 100);
}}

// تحديث الحالة عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', () => {{
  updateOnlineStatus();
  
  // إخفاء زر التثبيت إذا كان التطبيق مثبتاً
  if (window.matchMedia('(display-mode: standalone)').matches) {{
    document.getElementById('installBtn').style.display = 'none';
  }}
}});

console.log('🎉 بسام الذكي PWA جاهز للاستخدام!');
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
async def form_post(question: str = Form(...), mode: str = Form("summary"), detailed: bool = Form(False)):
    q = (question or "").strip()
    if not q:
        return HTML_TEMPLATE.format(result_panel="")

    # فحص المحتوى غير المناسب
    if is_inappropriate_content(q):
        reminder_panel = get_reminder_message()
        return HTML_TEMPLATE.format(result_panel=reminder_panel)

    if mode == "prices":
        panel, answer_text = await handle_prices(q, return_plain=True)
    elif mode == "images":
        panel, answer_text = await handle_images(q)
    elif mode == "smart":
        panel, answer_text = await handle_summary(q, return_plain=True, smart_mode=True, detailed=detailed)
    else:
        panel, answer_text = await handle_summary(q, return_plain=True, smart_mode=False, detailed=detailed)

    # شريط أدوات نسخ + PDF
    tools = make_toolbar_copy_pdf(q, mode, answer_text or "")
    return HTML_TEMPLATE.format(result_panel=tools + panel)

@app.post("/feedback")
async def feedback(domain: str = Form(...), delta: int = Form(...)):
    bump_score(domain, int(delta))
    return JSONResponse({"ok": True, "domain": domain, "score": get_scores().get(domain, 0)})

# PWA Routes
@app.get("/manifest.json")
async def get_manifest():
    """خدمة ملف manifest.json للـ PWA"""
    try:
        with open("manifest.json", "r", encoding="utf-8") as f:
            manifest_content = f.read()
        return Response(content=manifest_content, media_type="application/json")
    except FileNotFoundError:
        return JSONResponse({"error": "Manifest not found"}, status_code=404)

@app.get("/service-worker.js")
async def get_service_worker():
    """خدمة ملف service worker للـ PWA"""
    try:
        with open("service-worker.js", "r", encoding="utf-8") as f:
            sw_content = f.read()
        return Response(content=sw_content, media_type="application/javascript")
    except FileNotFoundError:
        return Response(content="console.log('Service Worker not found');", media_type="application/javascript")

# -------- وضع: بحث & تلخيص عربي --------
async def handle_summary(q: str, return_plain=False, smart_mode=False, detailed=False):
    cache_key = "sum:" + q
    cached = cache.get(cache_key)
    if cached and not return_plain:
        return cached, ""

    query_ar = q if "بالعربية" in q else (q + " بالعربية")
    
    # Reduce search results to speed up response
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query_ar, region="xa-ar", safesearch="Strict", max_results=10)) or []
        if not results:
            with DDGS() as ddgs:
                results = list(ddgs.text(q, region="xa-ar", safesearch="Strict", max_results=10)) or []
    except Exception:
        results = []

    source_cards, combined_chunks = [], []
    successful_sources = 0
    
    for r in sorted(results, key=lambda it: priority_key(it, "summary")):
        if successful_sources >= 3:  # Limit to 3 sources for faster response
            break
            
        href = r.get("href") or r.get("link") or r.get("url")
        title = r.get("title") or ""
        snippet = r.get("body", "")[:200]  # Use snippet from search results
        
        if not href:
            continue
        d = domain_of(href)

        # Try cache first
        ckey = "url:" + href
        val = cache.get(ckey)
        page_text = ""
        
        if val and isinstance(val, (tuple, list)) and len(val) >= 2:
            page_text = val[0] if isinstance(val[0], str) else ""
        
        # If no cached content and not a problematic domain, try to fetch
        if not page_text and not any(domain in href for domain in ["16personalities", "reverso", "britannica"]):
            try:
                txt, raw = fetch_and_extract(href, timeout=2)  # Reduced timeout
                if txt and len(txt) > 100:
                    cache.set(ckey, (txt, raw), expire=60*60*24)
                    page_text = txt
            except Exception:
                pass  # Skip this source if fetch fails
        
        # If we have content, process it
        if page_text and isinstance(page_text, str) and len(page_text) > 50:
            if is_arabic(page_text, min_ar_chars=10):  # Reduced Arabic requirement
                summ = summarize_from_text(page_text, q, max_sentences=2)
                if summ:
                    combined_chunks.append(summ)
                    source_cards.append(make_summary_card(title, href, summ, d))
                    successful_sources += 1
        elif snippet:  # Use search snippet as fallback
            combined_chunks.append(snippet)
            source_cards.append(make_summary_card(title, href, snippet, d))
            successful_sources += 1

    if not combined_chunks:
        panel = '<div class="card" style="margin-top:12px;">لم أعثر على محتوى عربي كافٍ. غيّر صياغة السؤال أو أضف كلمة "بالعربية".</div>'
        cache.set(cache_key, panel, expire=60*5)
        return (panel, "") if return_plain else (panel, None)

    # استخدام المحرك الذكي في الوضع الذكي
    if smart_mode and combined_chunks:
        # إعداد البيانات للمحرك الذكي
        search_results = []
        for r, chunk in zip(results[:len(combined_chunks)], combined_chunks):
            search_results.append({
                'title': r.get("title", ""),
                'content': chunk,
                'url': r.get("href", "")
            })
        
        # تحليل السؤال وتوليد الإجابة الذكية
        question_analysis = smart_engine.analyze_question(q)
        smart_answer = smart_engine.generate_smart_answer(
            question_analysis, 
            search_results, 
            detailed or question_analysis.get('needs_detail', False)
        )
        
        # عرض الإجابة الذكية مع أمان كامل
        panel = (
            f'<div style="margin-top:18px;">'
            f'<h3>🤖 إجابة بسام الذكي:</h3><div class="card smart-answer">{html.escape(smart_answer)}</div>'
            f'<h3 style="margin-top:12px;">المصادر:</h3>'
            f'{"".join(source_cards)}'
            f'<div style="margin-top:12px;">'
            f'<button onclick="showMore()" data-question="{html.escape(q, quote=True)}" class="btn-detail">📖 أريد تفاصيل أكثر</button>'
            f'</div>'
            f'</div>'
        )
        cache.set(cache_key + "_smart", panel, expire=60*60)
        return (panel, smart_answer) if return_plain else (panel, None)
    
    # الوضع العادي
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

# إضافة endpoint للتعامل مع طلبات /api المستمرة
@app.head("/api")
@app.get("/api") 
async def api_endpoint():
    return {"status": "active", "message": "بسام الذكي API جاهز"}