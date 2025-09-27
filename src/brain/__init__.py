# src/brain/__init__.py — نواة بسام الذكي

import random
from datetime import datetime

# قاعدة بيانات مؤقتة للذاكرة
memory_log = []


def safe_run(query: str) -> str:
    """
    نواة التفكير في بسام الذكي — النسخة 1.0
    تقوم بتحليل السؤال، البحث عن نمط، والرد بشكل ذكي مع حفظ الذاكرة.
    """

    # حفظ السؤال في الذاكرة
    memory_log.append({"time": datetime.now(), "query": query})

    # --------------------------
    # التحليل الأساسي
    # --------------------------
    q = query.strip().lower()

    # 1️⃣ رياضيات بسيطة
    if any(x in q for x in ["+", "-", "*", "/", "x**", "sqrt", "تكامل", "اشتقاق"]):
        return solve_math(q)

    # 2️⃣ أسئلة عامة
    elif "من هو" in q or "ما هي" in q or "اين" in q or "متى" in q:
        return smart_answer(q)

    # 3️⃣ رد افتراضي ذكي
    else:
        return think_creatively(q)


def solve_math(q: str) -> str:
    """معالجة الرياضيات"""
    try:
        from sympy import sympify
        result = sympify(q).evalf()
        return f"✅ الناتج: {result}"
    except Exception:
        return "⚠️ عذرًا، لم أتمكن من فهم المعادلة، أعد كتابتها بصيغة أوضح مثل: 2*x + 3."


def smart_answer(q: str) -> str:
    """ردود ذكية للأسئلة العامة"""
    responses = [
        "📘 سؤال جميل جدًا! اليمن تقع في جنوب شبه الجزيرة العربية وعاصمتها صنعاء 🇾🇪.",
        "💡 يبدو أنك تسأل عن معلومة عامة — جاري التفكير...",
        "🤖 حسب معلوماتي، الجواب يعتمد على السياق، هل يمكنك التوضيح أكثر؟"
    ]
    return random.choice(responses)


def think_creatively(q: str) -> str:
    """ردود إبداعية عند عدم تطابق النمط"""
    ideas = [
        f"✨ سؤال رائع يا بسام! سأسجله في الذاكرة لأتعلمه لاحقًا.",
        f"🤔 هذا سؤال يحتاج بحثًا أعمق، سأضيفه لقائمة التطوير القادمة.",
        f"💭 أفكر في هذا السؤال... يبدو أنك تفتح آفاقًا جديدة!"
    ]
    return random.choice(ideas)
