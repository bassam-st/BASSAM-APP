# src/brain/__init__.py

# نحاول استخدام الموجود داخل agent.py إن كان متاحًا
try:
    from . import agent as agent_mod
except Exception:
    agent_mod = None


def safe_run(query: str) -> str:
    """
    دالة آمنة لاستقبال سؤال المستخدم وتشغيل محرك الذكاء.
    تحاول تشغيل ما هو متاح داخل agent.py، ثم تسقط لرد تجريبي عند الحاجة.
    """
    try:
        if agent_mod is not None:
            # 1) إن كان هناك دالة safe_run في agent.py
            if hasattr(agent_mod, "safe_run") and callable(agent_mod.safe_run):
                return agent_mod.safe_run(query)

            # 2) أو دالة run
            if hasattr(agent_mod, "run") and callable(agent_mod.run):
                return agent_mod.run(query)

            # 3) أو كائن agent لديه __call__ أو run
            if hasattr(agent_mod, "agent"):
                ag = getattr(agent_mod, "agent")
                # callable(agent) => agent(query)
                if callable(ag):
                    return ag(query)
                # أو agent.run(query)
                if hasattr(ag, "run") and callable(ag.run):
                    return ag.run(query)

        # إن لم نجد أيًّا مما سبق، نرجع ردًا تجريبيًا
        return f"استلمت سؤالك: {query}"

    except Exception as e:
        # لا نسمح للخطأ أن يُسقط الخدمة؛ نرجع رسالة مفهومة
        return f"عذرًا، حدث خطأ داخلي أثناء المعالجة: {e}"
