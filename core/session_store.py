# core/session_store.py
from __future__ import annotations
import time
from typing import Dict, List, Any, Optional

# in-memory بسيط (Render/Replit: مؤقت، لكنه يكفي للمحادثة الخفيفة)
_STORE: Dict[str, Dict[str, Any]] = {}
TTL_SECONDS = 60 * 60  # ساعة

def now() -> float:
    return time.time()

def _expired(item: Dict[str, Any]) -> bool:
    return (now() - item.get("_ts", 0)) > TTL_SECONDS

def init(session_id: str) -> None:
    _STORE.setdefault(session_id, {"_ts": now(), "messages": [], "segments": []})
    _STORE[session_id]["_ts"] = now()

def add_message(session_id: str, role: str, content: str) -> None:
    init(session_id)
    _STORE[session_id]["messages"].append({"role": role, "content": content, "ts": now()})

def set_segments(session_id: str, segments: List[Dict[str, Any]]) -> None:
    init(session_id)
    _STORE[session_id]["segments"] = segments

def get_segments(session_id: str) -> List[Dict[str, Any]]:
    init(session_id)
    return _STORE[session_id].get("segments", [])

def get_message_history(session_id: str) -> List[Dict[str, Any]]:
    init(session_id)
    return _STORE[session_id]["messages"]

def cleanup() -> None:
    # نادِها كل فترة (اختياري)
    dead = [sid for sid, v in _STORE.items() if _expired(v)]
    for sid in dead:
        _STORE.pop(sid, None)
