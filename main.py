"""
تطبيق بسام الذكي - BASSAM-AI-APP
تطبيق ذكي شامل للبحث والرياضيات والذكاء الاصطناعي باللغة العربية
"""

from fastapi import FastAPI, Form, Body, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Dict, Any
import os

# استيراد الوحدات المحلية
from core.search import search_engine
from core import math_engine  # <-- مهم: هكذا نتفادى ImportError
from core.ai_engine import ai_engine
from core.enhanced_ai_engine import enhanced_ai_engine
from core.advanced_intelligence import AdvancedIntelligence
from core.free_architecture import free_architecture
from core.scientific_libraries import scientific_libraries
from core.utils import is_arabic, normalize_text, truncate_text

# راوتر رفع/حل الصورة (OCR -> Math)
from routes_image import router as image_router

# إنشاء مثيل من الذكاء المتقدم
advanced_intelligence = AdvancedIntelligence()

# إعداد التطبيق
app = FastAPI(
    title="Bassam Smart App",
    description="تطبيق بسام الذكي - مساعد ذكي شامل باللغة العربية",
    version="1.0.0"
)

# تضمين راوتر الصور
app.include_router(image_router)

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

@app.get("/", response_class=HTMLResponse)
async def home():
    """الصفحة الرئيسية"""
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
            .form-group { margin-bottom: 25px; }
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
            .mode-selector {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin: 25px 0;
            }
            .mode-btn {
                padding: 15px;
                border: 2px solid #e1e5e9;
                background: white;
                border-radius: 10px;
                cursor: pointer;
                text-align: center;
                font-weight: bold;
                transition: all 0.3s;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
            }
            .mode-btn:hover { background: #f8f9fa; transform: translateY(-2px); }
            .mode-btn.active {
                background: #4facfe;
                color: white;
                border-color: #4facfe;
                transform: translateY(-2px);
            }
            .submit-btn {
                width: 100%;
                padding: 18px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 18px;
                font-weight: bold;
                cursor: pointer;
                transition: transform 0.3s;
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
                               placeholder="مثال: ما هو الذكاء الاصطناعي؟ | diff: x^2 + 3x | ارسم sin(x)" 
                               required>
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
                    
                    <button type="submit" class="submit-btn">🚀 ابدأ البحث</button>
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
            // تفعيل أزرار الوضع
            document.querySelectorAll('.mode-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    btn.querySelector('input').checked = true;
                });
            });
            
            // تركيز حقل الإدخال
            document.getElementById('query').focus();
        </script>
    </body>
    </html>
    """

# ------------------------------
# [إضافة آمنة] واجهة REST للرياضيات
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
    """POST /math"""
    query = (payload or {}).get("query", "")
    return _do_math_safely(query)

@app.get("/math", response_class=JSONResponse)
async def math_get(query: str = Query(..., description="نص المسألة")):
    """GET /math?query=..."""
    return _do_math_safely(query)

# ------------------------------
# نهاية إضافة /math
# ------------------------------

@app.post("/search")
async def search(query: str = Form(...), mode: str = Form("smart")):
    """معالجة طلبات البحث والحوسبة"""
    if not query.strip():
        return JSONResponse({"error": "يرجى إدخال سؤال أو مسألة", "query": query})

    try:
        result: Dict[str, Any] = {}

        if mode == "math":
            math_result = math_engine.solve_math_problem(query)
            result = {"mode": "math", "query": query, "result": math_result}

        elif mode == "search":
            search_result = search_engine.search_and_summarize(query)
            result = {"mode": "search", "query": query, "result": search_result}

        elif mode == "images":
            images = search_engine.search_images(query, max_results=10)
            result = {"mode": "images", "query": query, "result": {"images": images}}

        else:  # smart
            if any(k in query.lower() for k in ['مشتق', 'تكامل', 'حل', 'ارسم', 'plot', 'diff', 'integral', 'matrix']):
                math_result = math_engine.solve_math_problem(query)
                result = {"mode": "smart_math", "query": query, "result": math_result}
            else:
                ai_result = await enhanced_ai_engine.answer_question(query)
                if ai_result and ai_result.get('success'):
                    result = {"mode": "smart_ai", "query": query, "result": ai_result}
                else:
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

def generate_result_html(result: dict) -> str:
    """توليد HTML لعرض النتائج"""
    mode = result.get("mode", "")
    query = result.get("query", "")
    data = result.get("result", {})

    base_html = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head><meta charset="UTF-8"><title>نتائج البحث - بسام الذكي</title></head>
    <body><h2>السؤال: {query}</h2>
    """

    if "error" in data:
        base_html += f"<p>❌ خطأ: {data['error']}</p>"
    elif mode in ("math", "smart_math"):
        base_html += f"<p>📊 النتيجة: {data}</p>"
    elif mode == "images":
        imgs = data.get("images", [])
        base_html += "<div>" + "".join(f"<img src='{i.get('thumbnail', i.get('image',''))}' width='150' style='margin:6px'>" for i in imgs) + "</div>"
    elif mode.startswith("smart_ai"):
        base_html += f"<div>🤖 {data.get('answer')}</div>"
    else:
        base_html += f"<div>🔍 {data.get('ai_summary', data.get('summary', 'لا توجد نتائج'))}</div>"

    base_html += "</body></html>"
    return base_html


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
