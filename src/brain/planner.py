# brain/planner.py
from typing import Optional, Dict

def simple_planner(query: str) -> Dict[str, Optional[str]]:
    """
    يقرر بسرعة هل نستخدم مهارة معيّنة أم نرد نصيًا.
    صيغة بسيطة: user can hint like:  sum: a=2 b=3  أو  echo: text=...
    """
    q = (query or "").strip()
    # تنسيق سريع: "اسم_المهارة: مفتاح=قيمة ..."
    if ":" in q and "=" in q:
        tool, rest = q.split(":", 1)
        tool = tool.strip().lower()
        args: Dict[str, str] = {}
        for part in rest.split():
            if "=" in part:
                k, v = part.split("=", 1)
                args[k.strip()] = v.strip()
        return {"mode": "tool", "tool": tool, "args": args}

    # لا توجد إشارة لآلة -> رد نصي
    return {"mode": "chat", "tool": None, "args": None}
