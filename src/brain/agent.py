# brain/agent.py
from .guard import check_auth, sanitize
from .planner import simple_planner
from .registry import registry
from .memory import memory
from .autoheal import safe_run

SYSTEM_PROMPT = "أنت بسام الذكي. أجب باختصار ودقة."

def bassam_query(secret: str, user_text: str) -> str:
    """
    واجهة موحدة: تأخذ كلمة السر ونص المستخدم وترجع الإجابة.
    """
    if not check_auth(secret):
        return "رفض: كلمة السر غير صحيحة."

    user_text = sanitize(user_text)
    memory.add("user", user_text)

    plan = simple_planner(user_text)

    if plan["mode"] == "tool" and plan["tool"]:
        tool = plan["tool"]
        args = plan["args"] or {}
        if registry.has(tool):
            status, out = safe_run(registry.run, tool, **args)
            reply = out if status == "ok" else f"لم تنجح الأداة '{tool}'. {out}"
        else:
            reply = f"لا أعرف الأداة: {tool}"
    else:
        # رد نصي بسيط الآن (يمكن لاحقًا توصيل نموذج لغة/نواة)
        reply = f"{SYSTEM_PROMPT} | تلقيت سؤالك: «{user_text}»"

    memory.add("assistant", reply)
    return reply
