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
import core.math_engine as math_engine   # ✅ التعديل هنا
from core.ai_engine import ai_engine
from core.enhanced_ai_engine import enhanced_ai_engine
from core.advanced_intelligence import AdvancedIntelligence
from core.free_architecture import free_architecture
from core.scientific_libraries import scientific_libraries
from core.utils import is_arabic, normalize_text, truncate_text

# استيراد راوتر الصور (OCR)
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
    </head>
    <body>
        <h1>🤖 أهلاً بك في تطبيق بسام الذكي</h1>
        <p>مساعدك للبحث والرياضيات والذكاء الاصطناعي</p>
        <p><a href="/upload">📷 جرّب حل مسألة من صورة</a></p>
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

        return HTMLResponse(content=generate_result_html(result))

    except Exception as e:
        return JSONResponse({"error": f"حدث خطأ أثناء المعالجة: {str(e)}", "query": query, "mode": mode})

def generate_result_html(result: dict) -> str:
    """توليد HTML لعرض النتائج"""
    mode = result.get("mode", "")
    query = result.get("query", "")
    data = result.get("result", {})

    base_html = f"<h2>السؤال: {query}</h2>"

    if "error" in data:
        base_html += f"<p>❌ خطأ: {data['error']}</p>"
    elif mode in ("math", "smart_math"):
        base_html += f"<p>📊 النتيجة: {data}</p>"
    elif mode == "images":
        imgs = data.get("images", [])
        base_html += "<div>" + "".join(f"<img src='{i.get('thumbnail')}' width='150'>" for i in imgs) + "</div>"
    elif mode.startswith("smart_ai"):
        base_html += f"<div>🤖 {data.get('answer')}</div>"
    else:
        base_html += f"<div>🔍 {data.get('summary', 'لا توجد نتائج')}</div>"

    return base_html


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
