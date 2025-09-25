"""
تطبيق بسام الذكي - BASSAM-AI-APP
تطبيق ذكي شامل للبحث والرياضيات والذكاء الاصطناعي باللغة العربية
"""

from fastapi import FastAPI, Form, Body, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional, Dict, Any
import os

# استيراد الوحدات المحلية
from core.search import search_engine
from core.math_engine import math_engine
from core.ai_engine import ai_engine
from core.enhanced_ai_engine import enhanced_ai_engine
from core.advanced_intelligence import AdvancedIntelligence
from core.free_architecture import free_architecture
from core.scientific_libraries import scientific_libraries
from core.utils import is_arabic, normalize_text, truncate_text

# إنشاء مثيل من الذكاء المتقدم
advanced_intelligence = AdvancedIntelligence()

# إعداد التطبيق
app = FastAPI(
    title="Bassam Smart App",
    description="تطبيق بسام الذكي - مساعد ذكي شامل باللغة العربية",
    version="1.0.0"
)

@app.get("/health")
async def health():
    """Health check endpoint with comprehensive status"""
    system_status = enhanced_ai_engine.get_system_status()
    return {
        "status": "healthy",
        "app": "Bassam Smart AI - Enhanced Multi-LLM",
        "version": "2.0.0",
        "architecture": "Free-First",
        "ai_available": enhanced_ai_engine.is_available(),
        "services": {
            "search": True,
            "math": True,
            "ai": enhanced_ai_engine.is_available(),
            "multi_llm": True,
            "free_architecture": True
        },
        "models": system_status["models"],
        "session": system_status["session"],
        "architecture_health": system_status["architecture"],
        "system_healthy": system_status["system_healthy"]
    }

# =========================
# صفحة البداية مع لوحة الرموز
# =========================
@app.get("/", response_class=HTMLResponse)
async def home():
    """الصفحة الرئيسية مع لوحة رموز رياضية"""
    return """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🤖 بسام الذكي - BASSAM AI APP</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
                direction: rtl;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                color: white;
                padding: 40px 30px;
                text-align: center;
            }
            .header h1 { font-size: 2.5em; margin-bottom: 10px; }
            .header p { font-size: 1.2em; opacity: 0.9; }
            .content { padding: 40px 30px; }
            .form-group { margin-bottom: 18px; }
            label { display: block; margin-bottom: 10px; font-weight: bold; color: #333; }
            input[type="text"] {
                width: 100%;
                padding: 15px;
                border: 2px solid #e1e5e9;
                border-radius: 10px;
                font-size: 16px;
                transition: border-color 0.3s;
            }
            input[type="text"]:focus { border-color: #4facfe; outline: none; }

            /* أزرار اختيار الوضع */
            .mode-selector {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 12px;
                margin: 18px 0;
            }
            .mode-btn {
                padding: 12px;
                border: 2px solid #e1e5e9;
                background: white;
                border-radius: 10px;
                cursor: pointer;
                text-align: center;
                font-weight: bold;
                transition: all 0.25s;
                display: flex; align-items: center; justify-content: center; gap: 8px;
            }
            .mode-btn:hover { background: #f8f9fa; transform: translateY(-2px); }
            .mode-btn.active {
                background: #4facfe; color: white; border-color: #4facfe; transform: translateY(-2px);
            }

            .submit-btn {
                width: 100%;
                padding: 16px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 18px;
                font-weight: bold;
                cursor: pointer;
                transition: transform 0.25s;
            }
            .submit-btn:hover { transform: translateY(-3px); }

            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }
            .feature {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }
            .feature-icon { font-size: 2em; margin-bottom: 10px; }
            .footer {
                background: #f8f9fa;
                padding: 20px;
                text-align: center;
                color: #666;
                border-top: 1px solid #eee;
            }

            /* لوحة الرموز الرياضية */
            .math-keyboard {
                display: none; /* تظهر فقط مع وضع الرياضيات */
                flex-wrap: wrap; gap: 8px; margin: 10px 0 16px 0;
            }
            .math-keyboard button {
                border: 1px solid #dbe1e7; background: #fff;
                border-radius: 8px; padding: 8px 10px;
                cursor: pointer; font-size: 14px;
                transition: background 0.2s, transform 0.1s;
            }
            .math-keyboard button:hover { background: #f3f6fa; }
            .math-keyboard button:active { transform: scale(0.98); }
            .kbd-note { color:#666; font-size:12px; margin-top:-6px; margin-bottom:8px; }
            .hint { color:#555; font-size: 12px; margin-top: 6px; }
            code.prompt { background:#f4f5f7; padding:2px 6px; border-radius:6px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 بسام الذكي</h1>
                <p>مساعدك الذكي للبحث والرياضيات والذكاء الاصطناعي</p>
            </div>
            
            <div class="content">
                <form method="post" action="/search">
                    <div class="form-group">
                        <label for="query">اطرح سؤالك أو مسألتك:</label>
                        <input type="text" id="query" name="query" 
                               placeholder="مثال: حل 2*x**2 + 3*x - 2 = 0 | تكامل sin(x) من 0 إلى pi | اشتق 3*x**2 + 5*x - 7"
                               required>
                        <div class="hint">تلميح: استخدم <code class="prompt">x**2</code> للأسس، <code class="prompt">sqrt(x)</code> للجذر، <code class="prompt">pi</code> للعدد π.</div>
                    </div>

                    <!-- لوحة الرموز الرياضية (تظهر فقط عندما يُختار وضع الرياضيات) -->
                    <div id="math-kbd" class="math-keyboard">
                        <div class="kbd-note">لوحة الرموز السريعة:</div>
                        <button type="button" onclick="insertSymbol('^2')">x²</button>
                        <button type="button" onclick="insertSymbol('**')">^ برمجي ( ** )</button>
                        <button type="button" onclick="insertSymbol('sqrt()')">√ الجذر</button>
                        <button type="button" onclick="insertSymbol('pi')">π</button>
                        <button type="button" onclick="insertSymbol('Abs()')">|x|</button>
                        <button type="button" onclick="insertSymbol('sin()')">sin</button>
                        <button type="button" onclick="insertSymbol('cos()')">cos</button>
                        <button type="button" onclick="insertSymbol('tan()')">tan</button>
                        <button type="button" onclick="insertSymbol('ln()')">ln</button>
                        <button type="button" onclick="insertSymbol('log(,10)')">log₁₀</button>
                        <button type="button" onclick="insertSymbol('exp()')">eˣ</button>
                        <button type="button" onclick="insertSymbol('∫ ')">∫ (رمز فقط)</button>
                        <button type="button" onclick="insertTemplate('integral')">∫ تكامل محدد</button>
                        <button type="button" onclick="insertTemplate('deriv')">مشتقة d/dx</button>
                        <button type="button" onclick="insertTemplate('solve')">حل معادلة = 0</button>
                    </div>
                    
                    <div class="mode-selector">
                        <label class="mode-btn active">
                            <input type="radio" name="mode" value="smart" checked style="display:none">
                            🤖 ذكي
                        </label>
                        <label class="mode-btn">
                            <input type="radio" name="mode" value="search" style="display:none">
                            🔍 بحث
                        </label>
                        <label class="mode-btn">
                            <input type="radio" name="mode" value="math" style="display:none">
                            📊 رياضيات
                        </label>
                        <label class="mode-btn">
                            <input type="radio" name="mode" value="images" style="display:none">
                            🖼️ صور
                        </label>
                    </div>
                    
                    <button type="submit" class="submit-btn">🚀 ابدأ</button>
                </form>
                
                <div class="features">
                    <div class="feature">
                        <div class="feature-icon">🤖</div>
                        <h3>ذكاء اصطناعي</h3>
                        <p>إجابات ذكية مجانية بالعربية</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">📊</div>
                        <h3>رياضيات متقدمة</h3>
                        <p>مشتقات، تكاملات، رسوم بيانية</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">🔍</div>
                        <h3>بحث ذكي</h3>
                        <p>بحث وتلخيص المحتوى العربي</p>
                    </div>
                    <div class="feature">
                        <div class="feature-icon">🌐</div>
                        <h3>دعم العربية</h3>
                        <p>مصمم خصيصاً للمستخدم العربي</p>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p>🤖 تطبيق بسام الذكي - BASSAM AI APP v1.0</p>
                <p>مساعدك الذكي المجاني باللغة العربية</p>
            </div>
        </div>
        
        <script>
            // تبديل الحالة المرئية للوحة الرياضيات حسب الوضع
            function refreshKeyboardVisibility() {
                const kbd = document.getElementById('math-kbd');
                const mode = document.querySelector('input[name="mode"]:checked').value;
                kbd.style.display = (mode === 'math') ? 'flex' : 'none';
            }

            // تفعيل أزرار الوضع + إظهار اللوحة عند اختيار "رياضيات"
            document.querySelectorAll('.mode-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    const radio = btn.querySelector('input');
                    radio.checked = true;
                    refreshKeyboardVisibility();
                    // تلميح لنماذج الرياضيات
                    if (radio.value === 'math') {
                        const q = document.getElementById('query');
                        if (!q.value) q.placeholder = "أمثلة: حل 2*x**2 + 3*x - 2 = 0 | اشتق 3*x**2 + 5*x - 7 | تكامل sin(x) من 0 إلى pi";
                    }
                });
            });

            // إدخال رمز مباشرة في خانة النص
            function insertSymbol(symbol) {
                const input = document.getElementById("query");
                const start = input.selectionStart, end = input.selectionEnd;
                const text = input.value;
                input.value = text.slice(0, start) + symbol + text.slice(end);
                input.focus();
                const pos = start + symbol.length;
                input.setSelectionRange(pos, pos);
            }

            // قوالب سريعة
            function insertTemplate(kind) {
                const input = document.getElementById("query");
                let t = "";
                if (kind === 'integral') {
                    t = "تكامل sin(x) من 0 إلى pi";
                } else if (kind === 'deriv') {
                    t = "اشتق 3*x**2 + 5*x - 7";
                } else if (kind === 'solve') {
                    t = "حل 2*x**2 + 3*x - 2 = 0";
                }
                input.value = t;
                input.focus();
                input.setSelectionRange(t.length, t.length);
            }

            // تركيز حقل الإدخال عند التحميل + تزامن حالة اللوحة
            window.addEventListener('DOMContentLoaded', () => {
                document.getElementById('query').focus();
                refreshKeyboardVisibility();
            });
        </script>
    </body>
    </html>
    """

# ------------------------------
# واجهة REST للرياضيات (كما هي)
# ------------------------------
def _do_math_safely(query: str) -> Dict[str, Any]:
    """استدعاء محرك الرياضيات الحالي كما هو مع رسائل أخطاء واضحة."""
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="يرجى إرسال 'query' كنص للمسألة.")
    try:
        result = math_engine.solve_math_problem(query)
        if isinstance(result, dict) and "success" not in result:
            result["success"] = True
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ أثناء الحل: {e}")

@app.post("/math", response_class=JSONResponse)
async def math_post(payload: dict = Body(...)):
    """
    POST /math
    Body JSON: { "query": "مثال: حل 2*x+1=5" }
    """
    query = (payload or {}).get("query", "")
    return _do_math_safely(query)

@app.get("/math", response_class=JSONResponse)
async def math_get(query: str = Query(..., description="نص المسألة، مثل: تكامل 2*x من 0 إلى 1")):
    """
    مثال:
    GET /math?query=تكامل%202*x%20من%200%20إلى%201
    """
    return _do_math_safely(query)

# ------------------------------
# مسار البحث/الذكاء كما هو
# ------------------------------
@app.post("/search")
async def search(query: str = Form(...), mode: str = Form("smart")):
    """معالجة طلبات البحث والحوسبة"""
    if not query.strip():
        return JSONResponse({"error": "يرجى إدخال سؤال أو مسألة", "query": query})

    try:
        result: Dict[str, Any] = {}

        if mode == "math":
            # وضع الرياضيات
            math_result = math_engine.solve_math_problem(query)
            result = {"mode": "math", "query": query, "result": math_result}

        elif mode == "search":
            # وضع البحث
            search_result = search_engine.search_and_summarize(query)
            result = {"mode": "search", "query": query, "result": search_result}

        elif mode == "images":
            # وضع البحث عن الصور
            images = search_engine.search_images(query, max_results=10)
            result = {"mode": "images", "query": query, "result": {"images": images}}

        else:  # mode == "smart"
            # الوضع الذكي - يحدد تلقائياً نوع الطلب
            if any(k in query.lower() for k in ['مشتق', 'تكامل', 'حل', 'ارسم', 'plot', 'diff', 'integral', 'matrix']):
                math_result = math_engine.solve_math_problem(query)
                result = {"mode": "smart_math", "query": query, "result": math_result}
            else:
                # سؤال عام - استخدام النظام الذكي المحدث
                ai_result = await enhanced_ai_engine.answer_question(query)
                if ai_result and ai_result.get('success'):
                    result = {"mode": "smart_ai", "query": query, "result": ai_result}
                else:
                    # الاحتياط - البحث والتلخيص المحسن
                    search_result = search_engine.search_and_summarize(query)
                    enhanced = await enhanced_ai_engine.smart_search_enhancement(
                        query, search_result.get('results', [])
                    )
                    if enhanced:
                        search_result['ai_summary'] = enhanced
                    result = {"mode": "smart_search", "query": query, "result": search_result}

        html_response = generate_result_html(result)
        return HTMLResponse(content=html_response)

    except Exception as e:
        return JSONResponse({"error": f"حدث خطأ أثناء المعالجة: {str(e)}", "query": query, "mode": mode})

# ------------------------------
# مولّد صفحة النتائج (كما هو)
# ------------------------------
def generate_result_html(result: dict) -> str:
    """توليد HTML لعرض النتائج"""
    mode = result.get("mode", "")
    query = result.get("query", "")
    data = result.get("result", {})

    base_html = """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>نتائج البحث - بسام الذكي</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
                direction: rtl;
            }
            .container {
                max-width: 900px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .content { padding: 30px; }
            .result-card {
                background: #f8f9fa;
                border-radius: 15px;
                padding: 25px;
                margin: 20px 0;
                border-left: 5px solid #4facfe;
            }
            .back-btn {
                display: inline-block;
                padding: 12px 24px;
                background: #4facfe;
                color: white;
                text-decoration: none;
                border-radius: 25px;
                margin-bottom: 20px;
                transition: transform 0.3s;
            }
            .back-btn:hover { transform: translateY(-2px); }
            .math-result { background: #e8f5e8; border-left-color: #28a745; }
            .ai-result { background: #e3f2fd; border-left-color: #2196f3; }
            .search-result { background: #fff3e0; border-left-color: #ff9800; }
            .error-result { background: #ffebee; border-left-color: #f44336; }
            .image-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }
            .image-card {
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            .image-card img { width: 100%; height: 150px; object-fit: cover; }
            .image-card .title { padding: 10px; font-size: 0.9em; }
            pre { background: #f4f4f4; padding: 15px; border-radius: 8px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 بسام الذكي</h1>
                <p>نتائج البحث</p>
            </div>
            
            <div class="content">
                <a href="/" class="back-btn">← العودة للبحث</a>
                
                <h2>السؤال: """ + query + """</h2>"""

    if "error" in data:
        base_html += """
                <div class="result-card error-result">
                    <h3>❌ خطأ</h3>
                    <p>""" + str(data['error']) + """</p>
                </div>"""
    elif mode.startswith("smart_math") or mode == "math":
        if data.get('success'):
            base_html += """
                <div class="result-card math-result">
                    <h3>📊 """ + data.get('operation', 'نتيجة رياضية') + """</h3>"""
            if 'image' in data:
                base_html += '<img src="data:image/png;base64,' + data["image"] + '" style="max-width: 100%; border-radius: 10px; margin: 15px 0;">'
            if 'result' in data:
                base_html += "<p><strong>النتيجة:</strong> <code>" + str(data['result']) + "</code></p>"
            if 'solutions' in data:
                base_html += "<p><strong>الحلول:</strong> " + ', '.join(data['solutions']) + "</p>"
            base_html += "</div>"
        else:
            base_html += """
                <div class="result-card error-result">
                    <h3>❌ خطأ رياضي</h3>
                    <p>""" + data.get('error', 'خطأ غير محدد') + """</p>
                </div>"""
    elif mode.startswith("smart_ai"):
        ai_answer = data.get('answer', '').replace('\\n', '<br>')
        base_html += """
            <div class="result-card ai-result">
                <h3>🤖 إجابة ذكية</h3>
                <div style="line-height: 1.6; margin-top: 15px;">
                    """ + ai_answer + """
                </div>
            </div>"""
    elif mode == "images":
        images = data.get('images', [])
        if images:
            base_html += """
                <div class="result-card">
                    <h3>🖼️ نتائج الصور (""" + str(len(images)) + """ صورة)</h3>
                    <div class="image-grid">"""
            for img in images[:12]:
                img_thumbnail = img.get('thumbnail', img.get('image', ''))
                img_title = img.get('title', '')
                img_title_short = truncate_text(img_title, 50)
                base_html += """
                    <div class="image-card">
                        <img src=\\"""" + img_thumbnail + """\\" 
                             alt=\\"""" + img_title + """\\" loading="lazy">
                        <div class="title">""" + img_title_short + """</div>
                    </div>"""
            base_html += "</div></div>"
    else:
        search_summary = data.get('ai_summary', data.get('summary', 'لا توجد نتائج')).replace('\\n', '<br>')
        base_html += """
            <div class="result-card search-result">
                <h3>🔍 ملخص البحث</h3>
                <div style="line-height: 1.6; margin-top: 15px;">
                    """ + search_summary + """
                </div>
            </div>"""
        results = data.get('results', [])
        if results:
            base_html += "<h3>🌐 مصادر إضافية:</h3>"
            for result in results[:5]:
                base_html += """
                    <div class="result-card">
                        <h4><a href=\\"""" + result.get('url', '#') + """\\" target="_blank">""" + result.get('title', '') + """</a></h4>
                        <p>""" + result.get('snippet', '') + """</p>
                    </div>"""

    base_html += """
            </div>
        </div>
    </body>
    </html>"""
    return base_html


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
