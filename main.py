# main.py — بسام الذكي: بحث عربي مجاني + تلخيص ذكي + أسعار + صور + ذكاء اصطناعي + ذاكرة ذكية
import os
from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from ddgs import DDGS
from readability import Document
from bs4 import BeautifulSoup
from diskcache import Cache
from urllib.parse import urlparse, urlencode

# PDF functionality - optional
try:
    from fpdf import FPDF
    PDF_AVAILABLE = True
except ImportError:
    try:
        from fpdf2 import FPDF
        PDF_AVAILABLE = True
    except ImportError:
        PDF_AVAILABLE = False
        print("تحذير: مكتبة PDF غير متوفرة - سيتم تعطيل ميزة تصدير PDF")

import requests, re, html, time, ast, operator, datetime
from typing import Dict, Any, Optional, Union, List
import hashlib
import json

# استيراد psycopg2 بشكل اختياري
try:
    import psycopg2
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("تحذير: مكتبة psycopg2 غير متوفرة - سيتم تعطيل ميزة قاعدة البيانات")

try:
    from gemini_ai import hybrid_ai
except ImportError:
    print("تحذير: مكتبة Gemini غير متوفرة")
    hybrid_ai = None

app = FastAPI()
cache = Cache(".cache")

# -------- نظام الذاكرة الذكية والتعلم --------
class SmartMemory:
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        
    def get_connection(self):
        """الحصول على اتصال قاعدة البيانات"""
        if not PSYCOPG2_AVAILABLE:
            return None
        return psycopg2.connect(self.db_url)
    
    def hash_question(self, question: str) -> str:
        """إنشاء هاش فريد للسؤال"""
        # تطبيع السؤال قبل الهاش
        normalized = re.sub(r'\s+', ' ', question.lower().strip())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def search_memory(self, question: str) -> Optional[Dict]:
        """البحث في الذاكرة عن سؤال مشابه"""
        if not PSYCOPG2_AVAILABLE:
            return None
            
        question_hash = self.hash_question(question)
        
        try:
            conn = self.get_connection()
            if not conn:
                return None
                
            with conn:
                with conn.cursor() as cur:
                    # البحث بالهاش أولاً
                    cur.execute("""
                        SELECT question, answer, confidence_score, usage_count
                        FROM smart_memory 
                        WHERE question_hash = %s
                        ORDER BY usage_count DESC, last_used DESC
                        LIMIT 1
                    """, (question_hash,))
                    
                    result = cur.fetchone()
                    if result:
                        # تحديث عداد الاستخدام
                        cur.execute("""
                            UPDATE smart_memory 
                            SET usage_count = usage_count + 1, last_used = NOW()
                            WHERE question_hash = %s
                        """, (question_hash,))
                        
                        return {
                            'question': result[0],
                            'answer': result[1],
                            'confidence': result[2],
                            'usage_count': result[3] + 1
                        }
                    
                    # البحث التشابهي إذا لم نجد تطابق دقيق
                    words = question.lower().split()
                    if len(words) >= 2:
                        search_pattern = '%' + '%'.join(words[:3]) + '%'
                        cur.execute("""
                            SELECT question, answer, confidence_score, usage_count
                            FROM smart_memory 
                            WHERE LOWER(question) LIKE %s
                            AND confidence_score > 0.6
                            ORDER BY usage_count DESC, confidence_score DESC
                            LIMIT 1
                        """, (search_pattern,))
                        
                        result = cur.fetchone()
                        if result:
                            return {
                                'question': result[0],
                                'answer': result[1],
                                'confidence': result[2] * 0.8,  # تقليل الثقة للبحث التشابهي
                                'usage_count': result[3]
                            }
                            
        except Exception as e:
            print(f"خطأ في البحث بالذاكرة: {e}")
        
        return None
    
    def save_to_memory(self, question: str, answer: str, category: str = None, confidence: float = 0.9, source: str = 'auto'):
        """حفظ سؤال وإجابة في الذاكرة"""
        if not PSYCOPG2_AVAILABLE:
            return False
            
        question_hash = self.hash_question(question)
        
        try:
            conn = self.get_connection()
            if not conn:
                return False
                
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO smart_memory (question_hash, question, answer, category, confidence_score, source)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (question_hash) 
                        DO UPDATE SET 
                            answer = EXCLUDED.answer,
                            confidence_score = GREATEST(smart_memory.confidence_score, EXCLUDED.confidence_score),
                            usage_count = smart_memory.usage_count + 1,
                            last_used = NOW()
                    """, (question_hash, question, answer, category, confidence, source))
                    
            return True
            
        except Exception as e:
            print(f"خطأ في الحفظ بالذاكرة: {e}")
            return False

# إنشاء مثيل الذاكرة الذكية
smart_memory = SmartMemory()

# -------- HTML التطبيق الكامل --------
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 بسام الذكي - البحث العربي المتقدم</title>
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#667eea">
    <style>
        :root {{
            --primary: #667eea;
            --secondary: #764ba2;
            --accent: #f093fb;
            --text: #2d3748;
            --bg: #f7fafc;
            --card-bg: white;
            --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            --radius: 12px;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            min-height: 100vh;
            direction: rtl;
            color: var(--text);
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
            color: white;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        
        .header p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .search-card {{
            background: var(--card-bg);
            border-radius: var(--radius);
            padding: 30px;
            box-shadow: var(--shadow);
            margin-bottom: 20px;
        }}
        
        .form-group {{
            margin-bottom: 20px;
        }}
        
        label {{
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: var(--text);
        }}
        
        .search-input {{
            width: 100%;
            padding: 15px 20px;
            border: 2px solid #e2e8f0;
            border-radius: var(--radius);
            font-size: 16px;
            transition: all 0.3s ease;
            background: #f8f9fa;
        }}
        
        .search-input:focus {{
            outline: none;
            border-color: var(--primary);
            background: white;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        
        .mode-selector {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin-bottom: 20px;
        }}
        
        .mode-option {{
            position: relative;
        }}
        
        .mode-option input {{
            position: absolute;
            opacity: 0;
        }}
        
        .mode-label {{
            display: block;
            padding: 12px 16px;
            background: #f1f5f9;
            border: 2px solid #e2e8f0;
            border-radius: var(--radius);
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 500;
        }}
        
        .mode-option input:checked + .mode-label {{
            background: var(--primary);
            color: white;
            border-color: var(--primary);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }}
        
        .search-btn {{
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            border: none;
            border-radius: var(--radius);
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .search-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }}
        
        .result-card {{
            background: var(--card-bg);
            border-radius: var(--radius);
            padding: 25px;
            box-shadow: var(--shadow);
            margin-top: 20px;
        }}
        
        .result-header {{
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        
        .result-header h3 {{
            color: var(--primary);
            margin-bottom: 5px;
        }}
        
        .toolbar {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        
        .toolbar-btn {{
            padding: 8px 16px;
            background: #f1f5f9;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 14px;
        }}
        
        .toolbar-btn:hover {{
            background: var(--primary);
            color: white;
        }}
        
        .card {{
            background: #f8f9fa;
            border: 1px solid #e2e8f0;
            border-radius: var(--radius);
            padding: 20px;
            margin: 15px 0;
        }}
        
        .card h4 {{
            color: var(--primary);
            margin-bottom: 10px;
        }}
        
        .source-link {{
            color: var(--primary);
            text-decoration: none;
            font-weight: 500;
        }}
        
        .source-link:hover {{
            text-decoration: underline;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            color: white;
            opacity: 0.8;
        }}
        
        @media (max-width: 768px) {{
            .container {{ padding: 15px; }}
            .header h1 {{ font-size: 2rem; }}
            .search-card {{ padding: 20px; }}
            .mode-selector {{ grid-template-columns: 1fr 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 بسام الذكي</h1>
            <p>البحث العربي المتقدم مع الذكاء الاصطناعي والذاكرة الذكية</p>
        </div>
        
        <div class="search-card">
            <form method="post" action="/">
                <div class="form-group">
                    <label for="question">اسأل بسام أي شيء:</label>
                    <input type="text" 
                           id="question" 
                           name="question" 
                           class="search-input"
                           placeholder="مثال: ما هو الذكاء الاصطناعي؟ أو سعر iPhone 15 أو كم يساوي كيلو بالرطل؟"
                           required
                           autocomplete="off">
                </div>
                
                <div class="mode-selector">
                    <div class="mode-option">
                        <input type="radio" id="summary" name="mode" value="summary" checked>
                        <label for="summary" class="mode-label">📄 ملخص ذكي</label>
                    </div>
                    <div class="mode-option">
                        <input type="radio" id="smart" name="mode" value="smart">
                        <label for="smart" class="mode-label">🧠 وضع ذكي</label>
                    </div>
                    <div class="mode-option">
                        <input type="radio" id="prices" name="mode" value="prices">
                        <label for="prices" class="mode-label">💰 أسعار</label>
                    </div>
                    <div class="mode-option">
                        <input type="radio" id="images" name="mode" value="images">
                        <label for="images" class="mode-label">🖼️ صور</label>
                    </div>
                </div>
                
                <button type="submit" class="search-btn">
                    🔍 ابحث مع بسام
                </button>
            </form>
        </div>
        
        {result_panel}
        
        <div class="footer">
            <p>بسام الذكي v3.0 - مدعوم بالذكاء الاصطناعي والذاكرة الذكية</p>
            <small>يتعلم من كل سؤال ليقدم إجابات أفضل</small>
        </div>
    </div>
    
    <script>
        // تسجيل Service Worker للـ PWA
        if ('serviceWorker' in navigator) {{
            navigator.serviceWorker.register('/service-worker.js')
                .then(function(registration) {{
                    console.log('✅ Service Worker registered:', registration.scope);
                }})
                .catch(function(error) {{
                    console.log('❌ Service Worker registration failed:', error);
                }});
        }}
        
        // تركيز تلقائي على حقل البحث
        document.getElementById('question').focus();
        
        // نسخ النص
        function copyText(text) {{
            navigator.clipboard.writeText(text).then(() => {{
                alert('تم نسخ النص بنجاح! ✅');
            }});
        }}
        
        console.log('🎉 بسام الذكي PWA جاهز للاستخدام!');
    </script>
</body>
</html>"""

# إنشاء جدول قاعدة البيانات إذا لم يكن موجوداً
def init_database():
    """إنشاء جدول الذاكرة الذكية"""
    if not PSYCOPG2_AVAILABLE:
        return
        
    try:
        conn = smart_memory.get_connection()
        if not conn:
            return
            
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS smart_memory (
                        id SERIAL PRIMARY KEY,
                        question_hash VARCHAR(32) UNIQUE NOT NULL,
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        category VARCHAR(50),
                        confidence_score FLOAT DEFAULT 0.9,
                        source VARCHAR(50) DEFAULT 'auto',
                        usage_count INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT NOW(),
                        last_used TIMESTAMP DEFAULT NOW()
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_question_hash ON smart_memory(question_hash);
                    CREATE INDEX IF NOT EXISTS idx_usage_count ON smart_memory(usage_count DESC);
                    CREATE INDEX IF NOT EXISTS idx_confidence ON smart_memory(confidence_score DESC);
                """)
                print("✅ تم إنشاء جدول الذاكرة الذكية بنجاح")
                
    except Exception as e:
        print(f"خطأ في إنشاء قاعدة البيانات: {e}")

# تشغيل إنشاء قاعدة البيانات عند بدء التطبيق
init_database()

# ---------------- المسارات ----------------
@app.get("/", response_class=HTMLResponse)
async def form_get():
    return HTML_TEMPLATE.format(result_panel="")

@app.post("/", response_class=HTMLResponse)
async def form_post(question: str = Form(...), mode: str = Form("summary")):
    q = (question or "").strip()
    if not q:
        return HTML_TEMPLATE.format(result_panel="")

    # 🧠 البحث في الذاكرة الذكية أولاً
    memory_result = smart_memory.search_memory(q)
    if memory_result and memory_result.get('confidence', 0) > 0.7:
        # وجدنا إجابة موثوقة في الذاكرة
        memory_panel = f"""
        <div class="result-card">
            <div class="result-header">
                <h3>🧠 من ذاكرة بسام الذكية</h3>
                <small>تم استخدام هذه الإجابة {memory_result['usage_count']} مرة | الثقة: {memory_result['confidence']*100:.0f}%</small>
            </div>
            <div class="card">
                <p>{memory_result['answer']}</p>
            </div>
            <div class="toolbar">
                <button class="toolbar-btn" onclick="copyText('{memory_result['answer']}')">📋 نسخ</button>
            </div>
        </div>
        """
        return HTML_TEMPLATE.format(result_panel=memory_panel)

    # 🤖 محاولة الذكاء الاصطناعي للأسئلة البرمجية والشبكات
    if hybrid_ai and hybrid_ai.is_available():
        if any(word in q.lower() for word in ['python', 'javascript', 'html', 'css', 'برمجة', 'كود', 'شبكة', 'network']):
            ai_answer = hybrid_ai.answer_question(q)
            if ai_answer:
                ai_panel = f"""
                <div class="result-card">
                    <div class="result-header">
                        <h3>🤖 إجابة من الذكاء الاصطناعي</h3>
                        <small>تم توليد هذه الإجابة خصيصاً لسؤالك | Powered by Gemini AI</small>
                    </div>
                    <div class="card">
                        <p>{ai_answer}</p>
                    </div>
                    <div class="toolbar">
                        <button class="toolbar-btn" onclick="copyText('{ai_answer}')">📋 نسخ</button>
                    </div>
                </div>
                """
                # حفظ في الذاكرة
                smart_memory.save_to_memory(q, ai_answer, 'ai_generated', 0.85, 'gemini_ai')
                return HTML_TEMPLATE.format(result_panel=ai_panel)

    # البحث الحقيقي باستخدام DuckDuckGo
    try:
        if mode == "summary" or mode == "smart":
            # بحث فعلي عن المعلومات
            search_results = []
            answer_text = ""
            
            try:
                with DDGS() as ddgs:
                    # البحث عن النتائج
                    results = list(ddgs.text(q, max_results=5))
                    search_results = results
                    
                    if results:
                        # تجميع أفضل النتائج
                        combined_info = ""
                        sources = []
                        
                        for i, result in enumerate(results[:3]):
                            snippet = result.get('body', '').strip()
                            title = result.get('title', '').strip()
                            url = result.get('href', '')
                            
                            if snippet:
                                combined_info += f"{title}: {snippet}\n\n"
                                sources.append(f"<a href='{url}' target='_blank'>{title}</a>")
                        
                        # إنشاء إجابة ذكية
                        if combined_info:
                            # تلخيص ذكي للمعلومات
                            sentences = combined_info.split('.')
                            key_info = []
                            
                            for sentence in sentences[:8]:
                                if len(sentence.strip()) > 20 and any(word in sentence.lower() for word in q.lower().split()):
                                    key_info.append(sentence.strip())
                            
                            if key_info:
                                answer_text = '. '.join(key_info[:3]) + '.'
                            else:
                                answer_text = sentences[0].strip() + '.' if sentences else "معلومات متوفرة في المصادر أدناه."
                            
                            # إضافة إجابات محددة للمواضيع الشائعة
                            if "ذكاء اصطناعي" in q or "AI" in q.upper():
                                answer_text = "الذكاء الاصطناعي هو تقنية حديثة تمكن الآلات من محاكاة الذكاء البشري في المهام مثل التعلم والتفكير واتخاذ القرارات. " + answer_text
                            elif "python" in q.lower() or "بايثون" in q:
                                answer_text = "Python لغة برمجة قوية ومرنة تستخدم في تطوير المواقع والذكاء الاصطناعي وتحليل البيانات. " + answer_text
                        else:
                            answer_text = "تم العثور على معلومات ذات صلة في المصادر أدناه."
                        
                        # بناء لوحة النتائج
                        sources_html = "<br>".join([f"📎 {source}" for source in sources[:3]])
                        
                        result_panel = f"""
                        <div class="result-card">
                            <div class="result-header">
                                <h3>📄 نتائج البحث المباشر</h3>
                                <small>وضع: {mode} | مصادر موثوقة</small>
                            </div>
                            <div class="card">
                                <h4>الإجابة:</h4>
                                <p>{answer_text}</p>
                                <br>
                                <h4>المصادر:</h4>
                                <div style="font-size: 0.9em; line-height: 1.6;">
                                    {sources_html}
                                </div>
                            </div>
                            <div class="toolbar">
                                <button class="toolbar-btn" onclick="copyText('{answer_text}')">📋 نسخ الإجابة</button>
                            </div>
                        </div>
                        """
                        
                        # حفظ في الذاكرة الذكية
                        smart_memory.save_to_memory(q, answer_text, 'web_search', 0.8, 'duckduckgo')
                        
                    else:
                        # لا توجد نتائج
                        result_panel = f"""
                        <div class="result-card">
                            <div class="result-header">
                                <h3>⚠️ لم يتم العثور على نتائج</h3>
                            </div>
                            <div class="card">
                                <p>عذراً، لم أتمكن من العثور على معلومات كافية حول: {q}</p>
                                <p>جرب إعادة صياغة السؤال أو استخدم كلمات مفتاحية مختلفة.</p>
                            </div>
                        </div>
                        """
                        
            except Exception as search_error:
                print(f"خطأ في البحث: {search_error}")
                # إجابة احتياطية عند فشل البحث
                basic_answer = f"أعتذر، واجهت مشكلة في البحث عن: {q}. سأحاول تقديم إجابة عامة."
                
                if "ذكاء اصطناعي" in q or "AI" in q.upper():
                    basic_answer = "الذكاء الاصطناعي هو مجال في علوم الحاسوب يهدف إلى إنشاء أنظمة قادرة على أداء مهام تتطلب ذكاءً بشرياً."
                elif "python" in q.lower() or "بايثون" in q:
                    basic_answer = "Python لغة برمجة عالية المستوى، سهلة التعلم ومتعددة الاستخدامات في التطوير والذكاء الاصطناعي."
                
                result_panel = f"""
                <div class="result-card">
                    <div class="result-header">
                        <h3>📄 إجابة احتياطية</h3>
                        <small>وضع: {mode} | مؤقت</small>
                    </div>
                    <div class="card">
                        <p>{basic_answer}</p>
                    </div>
                    <div class="toolbar">
                        <button class="toolbar-btn" onclick="copyText('{basic_answer}')">📋 نسخ</button>
                    </div>
                </div>
                """
                
                smart_memory.save_to_memory(q, basic_answer, 'fallback', 0.6)
            
        elif mode == "prices":
            # بحث الأسعار الحقيقي
            try:
                with DDGS() as ddgs:
                    price_query = f"{q} price سعر ثمن"
                    results = list(ddgs.text(price_query, max_results=8))
                    
                    price_info = []
                    for result in results:
                        snippet = result.get('body', '')
                        title = result.get('title', '')
                        url = result.get('href', '')
                        
                        # البحث عن أرقام الأسعار
                        if any(currency in snippet.lower() for currency in ['$', 'usd', 'sar', 'ر.س', 'aed', 'د.إ', 'egp', 'ج.م', 'price', 'سعر', 'ثمن']):
                            price_info.append({
                                'title': title,
                                'snippet': snippet[:200] + '...',
                                'url': url
                            })
                        
                        if len(price_info) >= 5:
                            break
                    
                    if price_info:
                        prices_html = ""
                        for item in price_info:
                            prices_html += f"""
                            <div style="border: 1px solid #e2e8f0; padding: 15px; margin: 10px 0; border-radius: 8px;">
                                <h4 style="color: #667eea; margin-bottom: 8px;">{item['title']}</h4>
                                <p style="margin-bottom: 8px;">{item['snippet']}</p>
                                <a href="{item['url']}" target="_blank" class="source-link">🔗 فتح المصدر</a>
                            </div>
                            """
                        
                        result_panel = f"""
                        <div class="result-card">
                            <div class="result-header">
                                <h3>💰 نتائج البحث عن الأسعار</h3>
                                <small>تم العثور على {len(price_info)} نتيجة</small>
                            </div>
                            <div class="card">
                                {prices_html}
                            </div>
                        </div>
                        """
                    else:
                        result_panel = f"""
                        <div class="result-card">
                            <div class="result-header">
                                <h3>💰 بحث أسعار</h3>
                            </div>
                            <div class="card">
                                <p>لم أتمكن من العثور على معلومات واضحة عن أسعار: {q}</p>
                                <p>جرب البحث في:</p>
                                <ul>
                                    <li><a href="https://www.amazon.ae/s?k={q}" target="_blank">أمازون الإمارات</a></li>
                                    <li><a href="https://www.noon.com/uae-en/search/?q={q}" target="_blank">نون</a></li>
                                    <li><a href="https://www.alibaba.com/trade/search?SearchText={q}" target="_blank">علي بابا</a></li>
                                </ul>
                            </div>
                        </div>
                        """
            except Exception as e:
                result_panel = f"""
                <div class="result-card">
                    <div class="result-header">
                        <h3>💰 بحث أسعار</h3>
                    </div>
                    <div class="card">
                        <p>حدث خطأ أثناء البحث عن الأسعار. جرب البحث مباشرة في المواقع التجارية.</p>
                    </div>
                </div>
                """
            
        elif mode == "images":
            result_panel = f"""
            <div class="result-card">
                <div class="result-header">
                    <h3>🖼️ بحث صور</h3>
                </div>
                <div class="card">
                    <p>للبحث عن الصور، يمكنك زيارة:</p>
                    <a href="https://duckduckgo.com/?q={q}&iax=images&ia=images" target="_blank" class="source-link">
                        🔗 فتح نتائج الصور في DuckDuckGo
                    </a>
                </div>
            </div>
            """
        
            return HTML_TEMPLATE.format(result_panel=result_panel)
        
        else:
            # وضع غير معروف
            result_panel = f"""
            <div class="result-card">
                <div class="result-header">
                    <h3>⚠️ وضع غير معروف</h3>
                </div>
                <div class="card">
                    <p>الوضع المطلوب '{mode}' غير مدعوم.</p>
                </div>
            </div>
            """
        
        return HTML_TEMPLATE.format(result_panel=result_panel)
        
    except Exception as e:
        error_panel = f"""
        <div class="result-card">
            <div class="result-header">
                <h3>⚠️ خطأ</h3>
            </div>
            <div class="card">
                <p>عذراً، حدث خطأ أثناء معالجة طلبك: {str(e)}</p>
            </div>
        </div>
        """
        return HTML_TEMPLATE.format(result_panel=error_panel)

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
    content = """
// بسام الذكي Service Worker
const CACHE_NAME = 'bassam-ai-v3';
const urlsToCache = [
    '/',
    '/manifest.json'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(urlsToCache))
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                return response || fetch(event.request);
            })
    );
});

console.log('🤖 بسام الذكي Service Worker نشط');
"""
    return Response(content=content, media_type="application/javascript")

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "app": "بسام الذكي", "version": "3.0"}