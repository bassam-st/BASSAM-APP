# src/memory/memory.py
# نظام ذاكرة بسيط يعتمد ملف JSON (لاحقاً يمكن تبديله بـ Redis)

import json, os
from datetime import datetime
from typing import Dict, Any, Optional

MEMORY_FILE = "user_memory.json"

def _load() -> Dict[str, Any]:
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save(data: Dict[str, Any]) -> None:
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def remember(user_id: str, key: str, value: Any) -> None:
    """خزّن قيمة لمستخدم معيّن."""
    data = _load()
    u = data.get(user_id, {})
    u[key] = value
    u["last_update"] = datetime.now().isoformat(timespec="seconds")
    data[user_id] = u
    _save(data)

def recall(user_id: str, key: str, default: Optional[Any] = None) -> Any:
    """استرجع قيمة من ذاكرة المستخدم."""
    data = _load()
    return data.get(user_id, {}).get(key, default)

def forget_user(user_id: str) -> None:
    """احذف ذاكرة مستخدم بالكامل."""
    data = _load()
    if user_id in data:
        del data[user_id]
        _save(data)

def all_memory() -> Dict[str, Any]:
    """للاطلاع/التصحيح: أعد كل الذاكرة."""
    return _load()
